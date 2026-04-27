import logging
import time
import uuid
from dataclasses import dataclass
from threading import Lock
from urllib.parse import urljoin

import requests
from django.conf import settings

from .exceptions import HikPartnerError

logger = logging.getLogger(__name__)

# Human-readable messages for LAP gateway error codes that the API returns with
# no 'msg' field (or an empty one), so "unknown error" would show instead.
_LAP_ERROR_MESSAGES: dict[str, str] = {
    "LAP020011": "device offline or unreachable",
    "LAP006009": "device does not exist or no permission",
    "LAP068001": "event subscription not active",
    "LAP008128": "permission denied",
}


@dataclass
class HikPartnerClient:
    base_url: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    dry_run: bool | None = None

    def __post_init__(self) -> None:
        hik_settings = settings.HIK_PARTNER
        if self.base_url is None:
            self.base_url = hik_settings.get("BASE_URL", "")
        if self.api_key is None:
            self.api_key = hik_settings.get("API_KEY", "")
        if self.api_secret is None:
            self.api_secret = hik_settings.get("API_SECRET", "")
        if self.dry_run is None:
            self.dry_run = hik_settings.get("DRY_RUN", True)

        self._access_token = None
        self._token_expires_at = 0
        self._token_lock = Lock()

    def build_url(self, path: str) -> str:
        if not self.base_url:
            return path
        return urljoin(f"{self.base_url.rstrip('/')}/", path.lstrip("/"))

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.api_secret)

    def get_access_token(self) -> str:
        with self._token_lock:
            if self._access_token and time.time() < self._token_expires_at:
                return self._access_token

            if self.dry_run:
                return "dry-run-token"

            url = self.build_url("/api/hpcgw/v1/token/get")
            # Per API guide §3.1: token request uses plain appKey + secretKey (no HMAC)
            payload = {
                "appKey": self.api_key,
                "secretKey": self.api_secret,
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError:
                logger.error("Invalid JSON in token response: %s", response.text)
                raise

            if data.get("errorCode") != "0":
                error_code = data.get("errorCode")
                message = data.get("msg") or data.get("errorMsg") or "token request failed"
                raise HikPartnerError(
                    f"HPC Token Error: {message} ({error_code})",
                    error_code=str(error_code),
                    payload=data,
                    status_code=response.status_code,
                )

            self._access_token = data["data"]["accessToken"]
            # expireTime is an absolute epoch timestamp in milliseconds (valid 7 days)
            expire_time_ms = int(data["data"]["expireTime"])
            self._token_expires_at = expire_time_ms / 1000 - 60  # 1 min buffer
            # areaDomain is the correct regional base URL for all subsequent API calls
            area_domain = data["data"].get("areaDomain")
            if area_domain:
                self.base_url = area_domain
            return self._access_token

    def _request_with_retry(
        self, method: str, url: str, retries: int = 3, **kwargs
    ) -> requests.Response:
        """
        Wrap requests.request with simple linear backoff retry.
        Only retries on connect-level errors (ConnectTimeout, ConnectionError).
        ReadTimeout is NOT retried: the server may have already processed a
        state-changing request and retrying would send the command twice.
        """
        _retryable = (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        )
        for attempt in range(retries):
            try:
                return requests.request(method=method, url=url, **kwargs)
            except _retryable as exc:
                if attempt == retries - 1:
                    raise
                delay = attempt + 1  # 1s, 2s, 3s …
                logger.warning(
                    "Retry %s/%s for %s %s after error: %s",
                    attempt + 1, retries, method, url, exc,
                )
                time.sleep(delay)
            except requests.exceptions.RequestException:
                raise

    def request(
        self,
        method: str,
        path: str,
        json: dict = None,
        headers: dict = None,
        content_type: str = "application/json",
        timeout: int = 15,
    ) -> dict:
        if self.dry_run:
            logger.debug("DRY RUN: %s %s", method, path)
            return {"status": "dry_run", "method": method, "path": path}

        request_id = str(uuid.uuid4())[:8]
        url = self.build_url(path)
        token = self.get_access_token()

        combined_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
            "Accept": "application/json",
        }
        if headers:
            combined_headers.update(headers)

        logger.debug("REQ[%s] %s %s", request_id, method, path)

        try:
            response = self._request_with_retry(
                method=method,
                url=url,
                json=json,
                headers=combined_headers,
                timeout=timeout,
            )

            if not response.ok:
                logger.error(
                    "REQ[%s] Hik-Partner API Error [%s]: %s\n"
                    "Request: %s %s\n"
                    "Headers: %s\n"
                    "Gateway Error: %s, Device Error: %s\n"
                    "Response Body: %s",
                    request_id,
                    response.status_code,
                    response.reason,
                    method, url,
                    {k: v for k, v in combined_headers.items() if k != "Authorization"},
                    response.headers.get("X-ErrorCode", "N/A"),
                    response.headers.get("X-DeviceCode", "N/A"),
                    response.text,
                )

            response.raise_for_status()

            try:
                data = response.json()
            except ValueError:
                # Fallback: if not JSON, return the raw text (e.g. XML)
                # This is common in transparent ISAPI channels.
                logger.debug(
                    "REQ[%s] Non-JSON response from %s %s, returning raw text.",
                    request_id, method, path
                )
                return response.text

            # Special case for transparent ISAPI: §A.5.8 JSON_ResponseStatus
            # If statusCode is 1, it is a success regardless of errorCode.
            if data.get("statusCode") == 1:
                return data

            error_code = data.get("errorCode")
            if error_code is not None and str(error_code) != "0":
                message = (
                    data.get("msg")
                    or data.get("errorMsg")
                    or _LAP_ERROR_MESSAGES.get(str(error_code))
                    or "unknown error"
                )
                raise HikPartnerError(
                    f"Hik-Partner API error {error_code}: {message} "
                    f"(path={path}, req={request_id})",
                    error_code=str(error_code),
                    payload=data,
                    status_code=response.status_code,
                )
            return data
        except requests.exceptions.RequestException as exc:
            logger.error("REQ[%s] Hik-Partner Connection Error: %s", request_id, exc)
            raise HikPartnerError(
                f"Hik-Partner Connection Error: {exc}",
                status_code=getattr(getattr(exc, "response", None), "status_code", None),
            ) from exc


    def transparent(
        self,
        device_serial: str,
        method: str,
        isapi_uri: str,
        body: dict = None,
        headers: dict = None,
        timeout: int = 15,
    ) -> dict:
        """
        Transparent ISAPI channel — per API guide §3.23.
        Path format: GET/PUT/POST/DELETE /api/hpcgw/v1/device/transparent/{isapi_uri}
        device_serial: hardware serial number — sent as X-Devserial header (required).
        headers: optional extra headers, e.g. X-Username / X-Password / X-Userlevel
                 for AX Pro operator auth. Must NOT re-set X-Devserial.
        """
        path = f"/api/hpcgw/v1/device/transparent/{isapi_uri.lstrip('/')}"
        http_headers = {"X-Devserial": device_serial}
        if headers:
            http_headers.update(headers)
        return self.request(
            method=method,
            path=path,
            json=body,
            headers=http_headers,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # MQ (event polling) — §3.33 – §3.35
    # ------------------------------------------------------------------

    def subscribe_events(self, device_serials: list[str] | None = None) -> dict:
        """
        Subscribe to alarm events.
        Pass device_serials to subscribe to specific devices, or None for all.
        Per §3.33: subType=1 (subscribe), subMode='all'|'list'.
        """
        if self.dry_run:
            return {"status": "dry_run"}

        if device_serials:
            body = {"subType": 1, "subMode": "list", "deviceSerialList": device_serials}
        else:
            body = {"subType": 1, "subMode": "all"}

        return self.request("POST", "/api/hpcgw/v1/mq/subscribe", json=body)

    def unsubscribe_events(self, device_serials: list[str] | None = None) -> dict:
        """Per §3.33: subType=0 (unsubscribe)."""
        if self.dry_run:
            return {"status": "dry_run"}

        if device_serials:
            body = {"subType": 0, "subMode": "list", "deviceSerialList": device_serials}
        else:
            body = {"subType": 0, "subMode": "all"}

        return self.request("POST", "/api/hpcgw/v1/mq/subscribe", json=body)

    def poll_messages(self) -> dict:
        """
        Long-poll for alarm messages (blocks up to 20 s if no events).
        Per §3.34 — returns batchId + list of alarm messages.
        Timeout is (5, 30): 5 s connect, 30 s read to safely outlast the 20 s server hold.
        Auto-resubscribes on LAP068001 (subscription expired / not subscribed).
        """
        if self.dry_run:
            return {"status": "dry_run", "data": {"list": [], "batchId": ""}}

        try:
            return self.request(
                "POST", "/api/hpcgw/v1/mq/messages", json={}, timeout=(5, 30)
            )
        except HikPartnerError as exc:
            if exc.error_code != "LAP068001":
                raise
            logger.warning(
                "poll_messages: MQ not subscribed (LAP068001) — attempting re-subscribe..."
            )
            try:
                self.subscribe_events()
                logger.info("poll_messages: re-subscribe successful, retrying poll")
                return self.request(
                    "POST", "/api/hpcgw/v1/mq/messages", json={}, timeout=(5, 30)
                )
            except Exception as sub_exc:
                logger.error("poll_messages: re-subscribe or retry failed: %s", sub_exc)
                return {"data": {"list": [], "batchId": ""}}

    def confirm_messages(self, batch_id: str) -> dict:
        """
        Confirm receipt of a message batch so it is not re-delivered.
        Per §3.35: call immediately after processing poll_messages() result.
        """
        if self.dry_run:
            return {"status": "dry_run"}

        return self.request("POST", "/api/hpcgw/v1/mq/offset", json={"batchId": batch_id})

    # ------------------------------------------------------------------
    # Webhook configuration — §3.67 – §3.69
    # ------------------------------------------------------------------

    def get_webhook_config(self) -> dict:
        """Per §3.67 — returns current callbackUrl, retryTimes, retryDelay."""
        if self.dry_run:
            return {"status": "dry_run"}
        return self.request("POST", "/api/hpcgw/webhook/v1/config/query", json={})

    def save_webhook_config(
        self,
        callback_url: str,
        retry_times: int = 3,
        retry_delay_ms: int = 1000,
        sign_secret: str = None,
    ) -> dict:
        """
        Per §3.68 — callback_url MUST use HTTPS.
        Only one webhook config is allowed per account.
        sign_secret: optional 8–32 alphanumeric chars for HMAC signing.
        Defaults to the account SecretKey if omitted.
        """
        if self.dry_run:
            return {"status": "dry_run"}

        if not callback_url.startswith("https://"):
            raise ValueError("Hikvision requires the webhook callbackUrl to use HTTPS.")
        if retry_times < -1 or retry_times > 5:
            raise ValueError("retryTimes must be between -1 and 5.")

        body = {
            "callbackUrl": callback_url,
            "retryTimes": retry_times,
            "retryDelay": retry_delay_ms,
        }
        if sign_secret:
            if not sign_secret.isalnum() or not (8 <= len(sign_secret) <= 32):
                raise ValueError("signSecret must be 8-32 alphanumeric characters.")
            body["signSecret"] = sign_secret

        return self.request("POST", "/api/hpcgw/webhook/v1/config/save", json=body)

    def delete_webhook_config(self) -> dict:
        """Per §3.69."""
        if self.dry_run:
            return {"status": "dry_run"}
        return self.request("POST", "/api/hpcgw/webhook/v1/config/delete", json={})

    # ------------------------------------------------------------------
    # Alarm picture URL — §3.36
    # ------------------------------------------------------------------

    def get_alarm_picture_url(self, file_path: str) -> dict:
        """
        Retrieve a time-limited download URL for an alarm image attachment.
        Per §3.36: filePath comes from the alarmData in an MQ message or webhook payload.
        The returned URL is valid for 2 hours. encrypt=True means the image is encrypted.
        """
        if self.dry_run:
            return {"pictureUrl": "https://example.com/dry-run-alarm-image.jpg", "encrypt": False}
        resp = self.request("POST", "/api/hpcgw/v1/alarm/pictureurl", json={"filePath": file_path})
        return resp.get("data", {})

    # ------------------------------------------------------------------
    # Site management — §3.3, §3.6
    # ------------------------------------------------------------------

    def create_site(
        self,
        name: str,
        time_zone: int = 222,
        time_sync: bool = False,
        site_state: str = None,
        site_city: str = None,
        site_street: str = None,
        location: str = None,
    ) -> dict:
        """
        Create a site on the Hik-Partner Pro platform.
        Per §3.3: returns only {"errorCode": "0"} — no site ID is returned.
        Call search_sites() afterwards to retrieve the assigned ID.
        timeZone 222 = UTC; see API appendix A.2 for full timezone list.
        """
        if self.dry_run:
            return {"status": "dry_run"}
        body = {"name": name, "timeZone": time_zone, "timeSync": time_sync}
        if site_state:
            body["siteState"] = site_state
        if site_city:
            body["siteCity"] = site_city
        if site_street:
            body["siteStreet"] = site_street
        if location:
            body["location"] = location
        return self.request("POST", "/api/hpcgw/v1/site/add", json=body)

    def search_sites(self, search: str = "", page: int = 1, page_size: int = 20) -> dict:
        """
        Search sites on the Hik-Partner Pro platform.
        Per §3.6: fuzzy search across site name, address, installer.
        Returns rows with: id, siteName, timeZone, siteState, siteCity, siteStreet, location.
        """
        if self.dry_run:
            return {"data": {"rows": [{"id": "dry-run-site-id", "siteName": search}], "total": 1}}
        return self.request(
            "POST",
            "/api/hpcgw/v1/site/search",
            json={"search": search, "page": page, "pageSize": page_size},
        )

    # ------------------------------------------------------------------
    # Device management — §3.18, §3.19
    # ------------------------------------------------------------------

    def add_devices(self, site_id: str, device_list: list) -> dict:
        """
        Add devices to a site on the Hik-Partner Pro platform.
        Per §3.18: each device needs deviceSerial + validateCode (verification code on the label).
        Returns addSuccessList and addFailedList.
        """
        if self.dry_run:
            serials = [d.get("deviceSerial", "unknown") for d in device_list]
            return {
                "data": {
                    "addSuccessList": [{"deviceSerial": s, "deviceName": s} for s in serials],
                    "addFailedList": [],
                }
            }
        return self.request(
            "POST",
            "/api/hpcgw/v2/device/add",
            json={"siteId": site_id, "deviceList": device_list},
        )

    def list_devices(self, site_id: str, page: int = 1, page_size: int = 100) -> dict:
        """
        List devices under a Hik site.
        Per §3.21: device/list is paginated. Passing page/pageSize avoids only
        receiving the platform default first page on larger production sites.
        """
        if self.dry_run:
            return {"data": {"rows": [], "total": 0, "page": page, "pageSize": page_size}}
        return self.request(
            "POST",
            "/api/hpcgw/v1/device/list",
            json={"siteId": site_id, "page": page, "pageSize": page_size},
        )


    def delete_device(self, device_id: str) -> dict:
        """
        Remove a device from the Hik-Partner Pro platform.
        Per §3.19: device_id is the Hik-side device ID (hik_device_id in local models).
        """
        if self.dry_run:
            return {"status": "dry_run"}
        return self.request("POST", "/api/hpcgw/v1/device/delete", json={"id": device_id})

    # ------------------------------------------------------------------
    # Installer (employee) search — §3.2
    # ------------------------------------------------------------------

    def search_installers(
        self, search: str = "", page: int = 1, page_size: int = 20
    ) -> dict:
        """
        Search for employees/installers on the Hik-Partner Pro platform.
        Per §3.2: fuzzy search across name, email, and phone number.
        Returns rows with: id, firstName, lastName, email, phone, isAdmin, enableStatus.
        """
        if self.dry_run:
            return {
                "data": {
                    "rows": [
                        {
                            "id": "dry-run-installer-id",
                            "firstName": "Demo",
                            "lastName": "Installer",
                            "email": "demo@example.com",
                            "phone": "+1234567890",
                            "isAdmin": False,
                            "enableStatus": True,
                            "invitedStatus": True,
                        }
                    ],
                    "total": 1,
                    "totalPage": 1,
                    "page": page,
                    "pageSize": page_size,
                }
            }
        body = {"page": page, "pageSize": page_size}
        if search:
            body["search"] = search
        return self.request("POST", "/api/hpcgw/v1/installers/search", json=body)

    # ------------------------------------------------------------------
    # ARC (Alarm Receiving Centre) service — §3.37–3.39
    # ------------------------------------------------------------------

    def list_arc_devices(
        self,
        page: int = 1,
        page_size: int = 20,
        site_id: str = None,
        device_serials: list[str] = None,
    ) -> dict:
        """
        Get devices with ARC service enabled.
        Per §3.37: available to ARC users only.
        """
        if self.dry_run:
            return {"data": {"rows": [], "total": 0, "totalPage": 0}}
        body = {"page": page, "pageSize": page_size}
        if site_id:
            body["siteId"] = site_id
        if device_serials:
            body["deviceSerialList"] = device_serials
        return self.request("POST", "/api/hpcgw/v1/arcservice/device/list", json=body)

    def enable_arc(self, device_serial: str, arc_id: str) -> dict:
        """
        Enable ARC service for a device.
        Per §3.38: all event types subscribed by default.
        permission: 0=pending end-user approval, 1=approved and applied.
        """
        if self.dry_run:
            return {"data": {"permission": 1}}
        return self.request(
            "POST",
            "/api/hpcgw/v1/arcservice/device/enable",
            json={"deviceSerial": device_serial, "arcId": arc_id},
        )

    def disable_arc(self, device_serial: str) -> dict:
        """
        Disable ARC service for a device.
        Per §3.39.
        """
        if self.dry_run:
            return {"status": "dry_run"}
        return self.request(
            "POST",
            "/api/hpcgw/v1/arcservice/device/disable",
            json={"deviceSerial": device_serial},
        )

    def get_site_health_report(self, site_id: str) -> dict:
        """
        Get the site health monitoring report — per §3.17.
        Returns device online status, battery, work status, and per-zone health.
        Response: data.reportDetail[].{deviceSerial, onlineStatus, alarmDeviceStatus}
        alarmDeviceStatus: {batteryStatus, workStatus, cloudStatus, zones[{zoneId, name,
                            batteryStatus, tamperStatus, networkStatus, byPassStatus}]}
        """
        if self.dry_run:
            return {
                "data": {
                    "reportDetail": []
                }
            }
        return self.request(
            "POST",
            "/api/hpcgw/v1/site/health/report",
            json={"siteId": site_id},
        )
