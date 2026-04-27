import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.alarms.models import AlarmEvent
from apps.sites.models import AlarmOutput, AlarmPanelDevice, AlarmPeripheral, Site, Subsystem, Zone

from .client import HikPartnerClient
from .services import HikPartnerService, HikPartnerError


class HikAdapterTests(TestCase):
    def setUp(self):
        self.site = Site.objects.create(name="Test Site", hik_site_id="site-1")
        self.device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="Test Device",
            serial_number="SN123",
            hik_device_id="dev-1",
        )
        self.subsystem = Subsystem.objects.create(
            site=self.site,
            device=self.device,
            name="Test Subsystem",
            hik_subsystem_id="sub-1",
            subsystem_number=1,
        )

    # ... (previous tests) ...

    def test_sync_site_devices_dry_run(self):
        service = HikPartnerService()
        service.client.dry_run = True
        
        result = service.sync_site_devices(self.site)
        
        self.assertEqual(result["synced_panels"], 1)
        
        # Verify database
        self.assertTrue(AlarmPanelDevice.objects.filter(site=self.site, hik_device_id="demo-panel-001").exists())

    @patch("apps.hik_adapter.client.HikPartnerClient.subscribe_events")
    @patch("apps.hik_adapter.services.HikPartnerService.sync_site_metadata")
    @patch("apps.hik_adapter.client.HikPartnerClient.list_devices")
    def test_sync_site_devices_fetches_all_device_pages(
        self,
        mock_list_devices,
        mock_sync_metadata,
        mock_subscribe_events,
    ):
        mock_list_devices.side_effect = [
            {
                "data": {
                    "rows": [
                        {
                            "id": "dev-page-1",
                            "deviceSerial": "SN-PAGE-1",
                            "deviceName": "Panel Page 1",
                            "deviceModel": "AX",
                            "deviceCategory": 3,
                            "deviceSubCategory": 3,
                            "deviceOnlineStatus": 1,
                        }
                    ],
                    "total": 2,
                }
            },
            {
                "data": {
                    "rows": [
                        {
                            "id": "dev-page-2",
                            "deviceSerial": "SN-PAGE-2",
                            "deviceName": "Panel Page 2",
                            "deviceModel": "AX",
                            "deviceCategory": 3,
                            "deviceSubCategory": 4,
                            "deviceOnlineStatus": 0,
                        }
                    ],
                    "total": 2,
                }
            },
        ]

        service = HikPartnerService()
        service.client.dry_run = False

        result = service.sync_site_devices(self.site)

        self.assertEqual(result["devices_seen"], 2)
        self.assertTrue(AlarmPanelDevice.objects.filter(serial_number="SN-PAGE-1").exists())
        self.assertTrue(AlarmPanelDevice.objects.filter(serial_number="SN-PAGE-2").exists())
        self.assertEqual(mock_list_devices.call_count, 2)
        mock_subscribe_events.assert_called_once_with(["SN-PAGE-1", "SN-PAGE-2"])

    @patch("apps.hik_adapter.client.requests.post")
    def test_get_access_token_success(self, mock_post):
        # Per API guide §3.1: token request uses plain appKey + secretKey
        # expireTime is absolute epoch in milliseconds
        import time
        expire_ms = int((time.time() + 7 * 86400) * 1000)  # 7 days from now
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errorCode": "0",
            "data": {
                "accessToken": "test-token-123",
                "expireTime": expire_ms,
                "areaDomain": "https://ieuapi.hik-partner.com",
            },
        }
        mock_post.return_value = mock_response

        client = HikPartnerClient(
            base_url="https://api.example.com",
            api_key="key",
            api_secret="secret",
            dry_run=False,
        )
        token = client.get_access_token()

        self.assertEqual(token, "test-token-123")
        self.assertTrue(mock_post.called)

        # Verify correct payload: plain secretKey, no HMAC signature
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["appKey"], "key")
        self.assertEqual(payload["secretKey"], "secret")
        self.assertNotIn("signature", payload)
        self.assertNotIn("time", payload)

        # Verify expiry is set correctly from expireTime (ms)
        self.assertAlmostEqual(client._token_expires_at, expire_ms / 1000 - 60, delta=5)

    @patch("apps.hik_adapter.client.requests.request")
    @patch("apps.hik_adapter.client.HikPartnerClient.get_access_token")
    def test_request_includes_auth_header_only(self, mock_get_token, mock_request):
        # Per API guide: only Authorization + Content-Type needed for business calls
        mock_get_token.return_value = "token-abc"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errorCode": "0", "data": "ok"}
        mock_request.return_value = mock_response

        client = HikPartnerClient(
            base_url="https://api.example.com",
            api_key="key",
            api_secret="secret",
            dry_run=False,
        )

        response = client.request("PUT", "/api/test", json={"foo": "bar"})

        self.assertEqual(response, {"errorCode": "0", "data": "ok"})

        # Verify only documented headers are sent
        args, kwargs = mock_request.call_args
        headers = kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer token-abc")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertNotIn("X-Hpc-AppKey", headers)
        self.assertNotIn("X-Hpc-Signature", headers)
        self.assertNotIn("X-Hpc-Timestamp", headers)
        self.assertNotIn("X-Hpc-Nonce", headers)

    @patch("apps.hik_adapter.client.requests.request")
    @patch("apps.hik_adapter.client.HikPartnerClient.get_access_token")
    def test_request_raises_typed_error_for_business_error(self, mock_get_token, mock_request):
        mock_get_token.return_value = "token-abc"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"errorCode": "LAP006009", "msg": "missing"}
        mock_request.return_value = mock_response

        client = HikPartnerClient(
            base_url="https://api.example.com",
            api_key="key",
            api_secret="secret",
            dry_run=False,
        )

        with self.assertRaises(HikPartnerError) as cm:
            client.request("POST", "/api/test", json={})

        self.assertEqual(cm.exception.error_code, "LAP006009")

    @patch("apps.hik_adapter.client.HikPartnerClient.request")
    def test_service_executes_command_and_logs_event(self, mock_client_request):
        mock_client_request.return_value = {"code": "0", "msg": "success", "data": {}}
        
        service = HikPartnerService()
        service.client.dry_run = False  # Enable real calls
        
        result = service.execute_subsystem_command(
            site=self.site,
            subsystem=self.subsystem,
            action="arm",
            payload={"moduleOperateCode": "1234"},
        )
        
        self.assertTrue(result["queued"])
        self.assertEqual(result["api_response"], {"code": "0", "msg": "success", "data": {}})
        
        # Verify subsystem status updated
        self.subsystem.refresh_from_db()
        self.assertEqual(self.subsystem.status, Subsystem.STATUS_ARMED)
        
        # Verify AlarmEvent created
        event = AlarmEvent.objects.get(site=self.site, subsystem=self.subsystem, event_type="arm_success")
        self.assertEqual(event.payload["action"], "arm")
        self.assertEqual(event.payload["api_response"]["code"], "0")
        self.assertNotIn("hpc_path", event.payload)

        # Verify client.request call
        mock_client_request.assert_called_once()
        args, kwargs = mock_client_request.call_args
        self.assertEqual(kwargs["method"], "PUT")
        self.assertIn("/api/hpcgw/v1/device/transparent/", kwargs["path"])
        self.assertEqual(kwargs["json"]["Operate"]["moduleOperateCode"], "1234")

    @patch("apps.hik_adapter.client.HikPartnerClient.request")
    def test_service_handles_api_failure(self, mock_client_request):
        mock_client_request.side_effect = Exception("Connection Timeout")
        
        service = HikPartnerService()
        service.client.dry_run = False
        self.subsystem.status = Subsystem.STATUS_ARMED
        self.subsystem.save(update_fields=["status"])
        
        with self.assertRaises(HikPartnerError) as cm:
            service.execute_subsystem_command(
                site=self.site,
                subsystem=self.subsystem,
                action="disarm",
                payload={},
            )
        
        self.assertIn("Failed to execute command on Hik-Partner Pro", str(cm.exception))
        
        # Local state must not change until Hik confirms the command succeeded.
        self.subsystem.refresh_from_db()
        self.assertEqual(self.subsystem.status, Subsystem.STATUS_ARMED)

    @patch("apps.hik_adapter.client.HikPartnerClient.request")
    def test_service_marks_panel_offline_when_hik_reports_unreachable(self, mock_client_request):
        mock_client_request.side_effect = HikPartnerError(
            "device offline or unreachable",
            error_code="LAP020011",
        )
        self.device.is_online = True
        self.device.save(update_fields=["is_online"])
        self.subsystem.status = Subsystem.STATUS_DISARMED
        self.subsystem.save(update_fields=["status"])

        service = HikPartnerService()
        service.client.dry_run = False

        with self.assertRaises(HikPartnerError) as cm:
            service.execute_subsystem_command(
                site=self.site,
                subsystem=self.subsystem,
                action="arm",
                payload={},
            )

        self.assertEqual(cm.exception.error_code, "LAP020011")
        self.device.refresh_from_db()
        self.subsystem.refresh_from_db()
        self.assertFalse(self.device.is_online)
        self.assertEqual(self.subsystem.status, Subsystem.STATUS_DISARMED)

    @patch("apps.hik_adapter.client.HikPartnerClient.request")
    def test_service_sends_operate_body_even_without_module_code(self, mock_client_request):
        mock_client_request.return_value = {"statusCode": 1, "statusString": "OK"}

        service = HikPartnerService()
        service.client.dry_run = False

        service.execute_subsystem_command(
            site=self.site,
            subsystem=self.subsystem,
            action="disarm",
            payload={},
        )

        args, kwargs = mock_client_request.call_args
        self.assertEqual(kwargs["json"], {"Operate": {}})
        self.assertEqual(kwargs["timeout"], 30)

    @patch("apps.hik_adapter.client.HikPartnerClient.request")
    def test_clear_alarm_command_logs_low_severity_system_event(self, mock_client_request):
        mock_client_request.return_value = {"statusCode": 1, "statusString": "OK"}

        service = HikPartnerService()
        service.client.dry_run = False

        service.execute_subsystem_command(
            site=self.site,
            subsystem=self.subsystem,
            action="clear-alarm",
            payload={},
        )

        event = AlarmEvent.objects.get(site=self.site, subsystem=self.subsystem, event_type="alarm_cleared")
        self.assertEqual(event.event_category, AlarmEvent.CATEGORY_SYSTEM)
        self.assertEqual(event.severity, AlarmEvent.SEVERITY_LOW)

    @patch("apps.hik_adapter.client.HikPartnerClient.request")
    def test_trigger_global_panic_uses_one_key_alarm_when_supported(self, mock_client_request):
        self.device.is_online = True
        self.device.save(update_fields=["is_online"])
        self.site.latitude = Decimal("5.565529300")
        self.site.longitude = Decimal("-0.186268300")
        self.site.save(update_fields=["latitude", "longitude", "updated_at"])
        second_subsystem = Subsystem.objects.create(
            site=self.site,
            device=self.device,
            name="Second Subsystem",
            hik_subsystem_id="sub-2",
            subsystem_number=2,
        )

        def fake_request(*args, **kwargs):
            path = kwargs["path"]
            if "control/capabilities" in path:
                return {"HostControlCap": {"isSptOneKeyAlarmCtrl": True}}
            if "control/oneKeyAlarm" in path:
                return {"statusCode": 1, "statusString": "OK"}
            self.fail(f"Unexpected request path: {path}")

        mock_client_request.side_effect = fake_request

        service = HikPartnerService()
        service.client.dry_run = False

        result = service.trigger_global_panic(self.site, panic_type="audible")

        self.subsystem.refresh_from_db()
        second_subsystem.refresh_from_db()
        self.assertEqual(self.subsystem.status, Subsystem.STATUS_ALARM)
        self.assertEqual(second_subsystem.status, Subsystem.STATUS_ALARM)
        self.assertEqual(result["dispatched"], 1)
        self.assertEqual(result["dispatched_partitions"], 2)
        self.assertEqual(result["failed_partitions"], 0)

        event = AlarmEvent.objects.get(site=self.site, event_code="panic")
        self.assertEqual(event.payload["partitions_triggered"], 2)
        self.assertEqual(event.payload["partitions_failed"], 0)
        self.assertEqual(event.payload["control_mode"], "one_key_alarm")

        put_calls = [
            kwargs for _, kwargs in mock_client_request.call_args_list
            if kwargs["path"].endswith("/ISAPI/SecurityCP/control/oneKeyAlarm?format=json")
        ]
        self.assertEqual(len(put_calls), 1)
        self.assertEqual(
            put_calls[0]["json"],
            {"OneKeyAlarm": {"longitude": -0.186268, "latitude": 5.565529}},
        )

    @patch("apps.hik_adapter.client.HikPartnerClient.request")
    def test_trigger_global_panic_falls_back_to_partition_endpoint_when_needed(self, mock_client_request):
        self.device.is_online = True
        self.device.save(update_fields=["is_online"])
        second_subsystem = Subsystem.objects.create(
            site=self.site,
            device=self.device,
            name="Second Subsystem",
            hik_subsystem_id="sub-2",
            subsystem_number=2,
        )

        def fake_request(*args, **kwargs):
            path = kwargs["path"]
            if "control/capabilities" in path:
                return {"HostControlCap": {"isSptOneKeyAlarmCtrl": False}}
            if "panicAlarm/2" in path:
                raise HikPartnerError("device rejected panic", error_code="LAP020011")
            if "panicAlarm/1" in path:
                return {"statusCode": 1, "statusString": "OK"}
            self.fail(f"Unexpected request path: {path}")

        mock_client_request.side_effect = fake_request

        service = HikPartnerService()
        service.client.dry_run = False

        result = service.trigger_global_panic(self.site, panic_type="audible")

        self.subsystem.refresh_from_db()
        second_subsystem.refresh_from_db()
        self.assertEqual(self.subsystem.status, Subsystem.STATUS_ALARM)
        self.assertNotEqual(second_subsystem.status, Subsystem.STATUS_ALARM)
        self.assertEqual(result["dispatched"], 1)
        self.assertEqual(result["dispatched_partitions"], 1)
        self.assertEqual(result["failed_partitions"], 1)

        event = AlarmEvent.objects.get(site=self.site, event_code="panic")
        self.assertEqual(event.payload["partitions_triggered"], 1)
        self.assertEqual(event.payload["partitions_failed"], 1)

    @patch("apps.hik_adapter.services.requests.get")
    @patch("apps.hik_adapter.client.HikPartnerClient.search_sites")
    def test_sync_site_metadata_updates_address_and_coordinates(self, mock_search_sites, mock_get):
        mock_search_sites.return_value = {
            "data": {
                "rows": [
                    {
                        "id": "site-1",
                        "siteName": "Synced Site",
                        "siteState": "Greater Accra",
                        "siteCity": "Accra",
                        "siteStreet": "15 Industrial Estate",
                        "location": "15 Industrial Estate, Accra",
                        "timeZone": "222",
                        "primaryIndustry": "Residential",
                    }
                ],
                "total": 1,
            }
        }
        mock_response = MagicMock()
        mock_response.json.return_value = [{"lat": "5.603700000", "lon": "-0.187000000"}]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        service = HikPartnerService()
        service.client.dry_run = False

        service.sync_site_metadata(self.site)

        self.site.refresh_from_db()
        self.assertEqual(self.site.name, "Synced Site")
        self.assertEqual(self.site.city, "Accra")
        self.assertEqual(self.site.state, "Greater Accra")
        self.assertEqual(self.site.address, "15 Industrial Estate, Accra")
        self.assertEqual(self.site.primary_industry, "House")
        self.assertEqual(self.site.latitude, Decimal("5.603700000"))
        self.assertEqual(self.site.longitude, Decimal("-0.187000000"))

    @patch("apps.hik_adapter.services.requests.get")
    @patch("apps.hik_adapter.client.HikPartnerClient.search_sites")
    def test_sync_site_metadata_uses_device_site_name_fallback(self, mock_search_sites, mock_get):
        mock_search_sites.side_effect = [
            {"data": {"rows": [], "total": 0}},
            {
                "data": {
                    "rows": [
                        {
                            "id": "site-1",
                            "siteName": "site74",
                            "siteState": "",
                            "siteCity": "Accra",
                            "siteStreet": "oseble street",
                            "location": "",
                            "timeZone": "48",
                        }
                    ],
                    "total": 1,
                }
            },
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        service = HikPartnerService()
        service.client.dry_run = False

        service.sync_site_metadata(
            self.site,
            device_list=[
                {
                    "siteID": "site-1",
                    "siteName": "site74",
                }
            ],
        )

        self.site.refresh_from_db()
        self.assertEqual(self.site.name, "site74")
        self.assertEqual(self.site.city, "Accra")
        self.assertEqual(self.site.address, "oseble street")

    def test_sync_alarm_status_persists_extended_zone_metadata_and_outputs(self):
        self.device.is_online = True
        self.device.save(update_fields=["is_online"])
        Zone.objects.create(
            subsystem=self.subsystem,
            name="Front Door",
            zone_number=1,
            device_type=Zone.DEVICE_TYPE_ZONE,
        )

        service = HikPartnerService()
        service.client.dry_run = False

        def transparent(*, isapi_uri, **kwargs):
            if isapi_uri == "/ISAPI/SecurityCP/status/subSystems?format=json":
                return {"SubSysList": [{"SubSys": {"id": 1, "name": "Area 1", "arming": "away", "alarm": False}}]}
            if isapi_uri == "/ISAPI/SecurityCP/status/hostHealth?format=json":
                return {"HostHealth": {"powerStatus": "AC"}}
            if isapi_uri == "/ISAPI/SecurityCP/status/zones?format=json":
                return {
                    "ZoneList": [
                        {
                            "Zone": {
                                "id": 1,
                                "name": "Front Door",
                                "subSystemNo": 1,
                                "status": "online",
                                "alarm": False,
                                "bypassed": False,
                                "magnetOpenStatus": True,
                                "charge": "lowPower",
                                "chargeValue": 22,
                                "signal": 88,
                                "tamperEvident": True,
                                "shielded": True,
                                "detectorType": "magneticContact",
                                "zoneType": "Perimeter",
                                "healthStatus": "fault",
                                "reason": "short",
                                "model": "DS-PDMCX-E-WE",
                                "accessModuleType": "transmitter",
                                "relatedAccessModuleID": 3,
                                "address": 4,
                                "zoneAttrib": "wireless",
                                "mainCharge": "normal",
                                "preheatStatus": "processing",
                                "userfulLifeStatus": "expire",
                                "mazeStatus": "abnormal",
                                "sensorStatus": "abnormal",
                                "temperature": 18,
                                "humidity": 40,
                                "deviceNo": 7,
                            }
                        }
                    ]
                }
            if isapi_uri == "/ISAPI/SecurityCP/status/outputStatus?format=json":
                return {
                    "OutputSearch": {
                        "OutputList": [
                            {
                                "Output": {
                                    "id": 2,
                                    "name": "Relay 2",
                                    "status": "on",
                                    "tamperEvident": True,
                                    "charge": "normal",
                                    "linkage": "alarm",
                                    "signal": 101,
                                    "durationConstOutputEnable": True,
                                    "isAvailable": True,
                                    "accessModuleType": "localRelay",
                                    "relatedAccessModuleID": 9,
                                    "address": 6,
                                    "subSystemList": [1],
                                    "scenarioType": ["alarm", "manualCtrl"],
                                    "relayAttrib": "wireless",
                                    "deviceNo": 11,
                                    "devIndex": "relay-dev-1",
                                    "devName": "Relay Module",
                                    "diagnosticsResult": "PASS",
                                }
                            }
                        ]
                    }
                }
            if isapi_uri == "/ISAPI/System/deviceInfo?format=json":
                return {"DeviceInfo": {"model": "DS-PWA96-M-WE", "firmwareVersion": "1.0.0", "hardwareVersion": "A1"}}
            raise AssertionError(f"Unexpected ISAPI URI {isapi_uri}")

        service.client.transparent = MagicMock(side_effect=transparent)

        service.sync_alarm_status(self.site)

        zone = Zone.objects.get(subsystem=self.subsystem, zone_number=1, device_type=Zone.DEVICE_TYPE_ZONE)
        self.assertEqual(zone.zone_type, "Perimeter")
        self.assertEqual(zone.access_module_type, "transmitter")
        self.assertEqual(zone.zone_attribute, "wireless")
        self.assertEqual(zone.health_status, "fault")
        self.assertTrue(zone.low_battery)
        self.assertTrue(zone.tamper)
        self.assertTrue(zone.shielded)
        self.assertTrue(zone.magnet_open)
        self.assertEqual(zone.device_number, 7)

        output = AlarmOutput.objects.get(device=self.device, output_number=2)
        self.assertEqual(output.linkage, "alarm")
        self.assertEqual(output.access_module_type, "localRelay")
        self.assertEqual(output.scenario_types, ["alarm", "manualCtrl"])
        self.assertTrue(output.duration_const_output_enable)

    @patch.object(HikPartnerService, "_sync_outputs_via_isapi", return_value=0)
    def test_apply_health_report_syncs_alarm_peripherals(self, mock_sync_outputs):
        service = HikPartnerService()
        report_detail = [
            {
                "deviceSerial": self.device.serial_number,
                "onlineStatus": 1,
                "alarmDeviceStatus": {
                    "batteryStatus": "ok",
                    "workStatus": "armed",
                    "cloudStatus": "online",
                    "zones": [],
                    "keyPadList": [
                        {"id": 1, "name": "Keypad A", "seq": "KP-1", "networkStatus": "ok", "batteryStatus": "ok", "signalStrength": "strong", "tamperStatus": "false", "diagnosticsResult": "PASS", "lastOperationTime": "5,Sep,2023 18:14:59"}
                    ],
                    "remoteList": [
                        {"id": 2, "name": "Keyfob A", "seq": "KF-1", "diagnosticsResult": "PASS", "lastOperationTime": "5,Sep,2023 18:14:59"}
                    ],
                    "cardReaderList": [
                        {"id": 3, "name": "Reader A", "seq": "CR-1", "networkStatus": "ok", "batteryStatus": "ok", "signalStrength": "middle", "tamperStatus": "true", "diagnosticsResult": "PASS"}
                    ],
                    "sirenList": [
                        {"id": 4, "name": "Siren A", "seq": "SR-1", "networkStatus": "ok", "batteryStatus": "low", "signalStrength": "weak", "tamperStatus": "false", "diagnosticsResult": "PASS"}
                    ],
                    "repeaterList": [
                        {"id": 5, "name": "Repeater A", "seq": "RP-1", "networkStatus": "ok", "batteryStatus": "ok", "signalStrength": "strong", "tamperStatus": "false", "diagnosticsResult": "PASS"}
                    ],
                    "TransmitterList": [
                        {"id": 6, "name": "Transmitter A", "seq": "TX-1", "networkStatus": "ok", "batteryStatus": "ok", "signalStrength": "strong", "tamperStatus": "false", "diagnosticsResult": "PASS", "lastTriggerTime": "5,Sep,2023 18:14:59"}
                    ],
                    "outPutList": [
                        {"id": 7, "name": "Output Module A", "seq": "OM-1", "networkStatus": "ok", "batteryStatus": "ok", "signalStrength": "strong", "tamperStatus": "false", "diagnosticsResult": "PASS"}
                    ],
                },
            }
        ]

        result = service._apply_health_report(self.site, report_detail)

        self.assertEqual(result["peripherals_updated"], 7)
        self.assertTrue(AlarmPeripheral.objects.filter(site=self.site, peripheral_type=AlarmPeripheral.TYPE_SIREN, peripheral_number=4).exists())
        self.assertTrue(AlarmPeripheral.objects.filter(site=self.site, peripheral_type=AlarmPeripheral.TYPE_OUTPUT_MODULE, peripheral_number=7).exists())
        self.assertTrue(Zone.objects.filter(subsystem=self.subsystem, device_type=Zone.DEVICE_TYPE_KEYPAD, zone_number=1).exists())
        self.assertTrue(Zone.objects.filter(subsystem=self.subsystem, device_type=Zone.DEVICE_TYPE_KEYFOB, zone_number=2).exists())
        self.assertTrue(Zone.objects.filter(subsystem=self.subsystem, device_type=Zone.DEVICE_TYPE_CARD_READER, zone_number=3).exists())

    @patch.object(HikPartnerService, "_sync_outputs_via_isapi", return_value=0)
    def test_apply_health_report_preserves_panel_power_when_report_omits_battery(self, mock_sync_outputs):
        self.device.is_online = True
        self.device.battery_status = AlarmPanelDevice.BATTERY_OK
        self.device.save(update_fields=["is_online", "battery_status", "updated_at"])

        service = HikPartnerService()
        service.client.transparent = MagicMock(return_value={"HostHealth": {"powerStatus": "AC"}})
        report_detail = [
            {
                "deviceSerial": self.device.serial_number,
                "onlineStatus": 1,
                "alarmDeviceStatus": {
                    "workStatus": "armed",
                    "cloudStatus": "online",
                    "zones": [],
                },
            }
        ]

        service._apply_health_report(self.site, report_detail)

        self.device.refresh_from_db()
        self.assertEqual(self.device.battery_status, AlarmPanelDevice.BATTERY_OK)

    def test_detector_mapping_covers_extended_alarm_detectors(self):
        self.assertEqual(HikPartnerService.get_detector_label("glassBreakDetector"), "Glass Break")
        self.assertEqual(HikPartnerService.get_detector_label("curtainDetector"), "Curtain Motion")
        self.assertEqual(HikPartnerService.get_detector_label("coDetector"), "CO Detector")
        self.assertEqual(HikPartnerService.get_detector_icon("curtainDetector"), "motion")
        self.assertEqual(HikPartnerService.get_detector_icon("heatDetector"), "fire")
        self.assertEqual(HikPartnerService.get_detector_label("unknownCustomDetector"), "Zone Sensor")

    def test_process_mq_message_normalizes_raw_hik_event_types(self):
        service = HikPartnerService()
        msg = {
            "deviceSerial": self.device.serial_number,
            "formatType": "JSON",
            "sendTime": "2026-04-11T19:00:00+00:00",
            "alarmData": json.dumps(
                {
                    "eventType": "VMD",
                    "eventDescription": "",
                    "triggerTime": "2026-04-11T19:00:00+00:00",
                }
            ),
        }

        event = service.process_mq_message(msg)

        self.assertIsNotNone(event)
        self.assertEqual(event.event_code, "VMD")
        self.assertEqual(event.event_category, AlarmEvent.CATEGORY_ALARM)
        self.assertEqual(event.severity, AlarmEvent.SEVERITY_HIGH)
        self.assertEqual(event.payload["event_name"], "Motion Detection")
        self.assertEqual(event.payload["normalized_event_type"], "motion_detection")

    def test_process_mq_message_normalizes_manual_capture_as_info_event(self):
        service = HikPartnerService()
        msg = {
            "deviceSerial": self.device.serial_number,
            "formatType": "JSON",
            "sendTime": "2026-04-11T19:05:00+00:00",
            "alarmData": json.dumps(
                {
                    "eventType": "manualRep",
                    "eventDescription": "",
                    "triggerTime": "2026-04-11T19:05:00+00:00",
                }
            ),
        }

        event = service.process_mq_message(msg)

        self.assertIsNotNone(event)
        self.assertEqual(event.event_code, "manualRep")
        self.assertEqual(event.event_category, AlarmEvent.CATEGORY_INFO)
        self.assertEqual(event.severity, AlarmEvent.SEVERITY_LOW)
        self.assertEqual(event.payload["event_name"], "Manual Capture")
        self.assertEqual(event.payload["normalized_event_type"], "manual_capture")

    def test_process_mq_message_normalizes_health_description_with_punctuation(self):
        service = HikPartnerService()
        msg = {
            "deviceSerial": self.device.serial_number,
            "formatType": "JSON",
            "sendTime": "2026-04-11T19:06:00+00:00",
            "alarmData": json.dumps(
                {
                    "eventType": "cidEvent",
                    "eventDescription": "PanelStatus(Power&Battery)",
                    "triggerTime": "2026-04-11T19:06:00+00:00",
                }
            ),
        }

        event = service.process_mq_message(msg)

        self.assertIsNotNone(event)
        self.assertEqual(event.event_category, AlarmEvent.CATEGORY_HEALTH)
        self.assertEqual(event.severity, AlarmEvent.SEVERITY_MEDIUM)
        self.assertEqual(event.payload["event_name"], "Panel Power Status")
        self.assertEqual(event.payload["normalized_event_type"], "panel_power_status")

    def test_process_mq_message_normalizes_ac_power_events(self):
        service = HikPartnerService()
        msg = {
            "deviceSerial": self.device.serial_number,
            "formatType": "JSON",
            "sendTime": "2026-04-11T19:07:00+00:00",
            "alarmData": json.dumps(
                {
                    "eventType": "cidEvent",
                    "eventDescription": "CID event",
                    "triggerTime": "2026-04-11T19:07:00+00:00",
                    "CIDEvent": {"description": "ACDown"},
                }
            ),
        }

        event = service.process_mq_message(msg)

        self.assertIsNotNone(event)
        self.assertEqual(event.event_category, AlarmEvent.CATEGORY_HEALTH)
        self.assertEqual(event.severity, AlarmEvent.SEVERITY_HIGH)
        self.assertEqual(event.payload["event_name"], "AC Power Lost")
        self.assertEqual(event.payload["normalized_event_type"], "ac_power_lost")
        self.device.refresh_from_db()
        self.assertEqual(self.device.battery_status, AlarmPanelDevice.BATTERY_LOW)

    def test_process_mq_message_restores_panel_power_from_ac_recovery_event(self):
        self.device.battery_status = AlarmPanelDevice.BATTERY_LOW
        self.device.save(update_fields=["battery_status", "updated_at"])
        service = HikPartnerService()
        msg = {
            "deviceSerial": self.device.serial_number,
            "formatType": "JSON",
            "sendTime": "2026-04-11T19:09:00+00:00",
            "alarmData": json.dumps(
                {
                    "eventType": "cidEvent",
                    "eventDescription": "CID event",
                    "triggerTime": "2026-04-11T19:09:00+00:00",
                    "CIDEvent": {"description": "ACRecov"},
                }
            ),
        }

        event = service.process_mq_message(msg)

        self.assertIsNotNone(event)
        self.assertEqual(event.payload["event_name"], "AC Power Restored")
        self.assertEqual(event.payload["normalized_event_type"], "ac_power_restored")
        self.device.refresh_from_db()
        self.assertEqual(self.device.battery_status, AlarmPanelDevice.BATTERY_OK)

    def test_process_mq_message_normalizes_alarm_trigger_label(self):
        service = HikPartnerService()
        msg = {
            "deviceSerial": self.device.serial_number,
            "formatType": "JSON",
            "sendTime": "2026-04-11T19:08:00+00:00",
            "alarmData": json.dumps(
                {
                    "eventType": "alarmTrig",
                    "eventDescription": "",
                    "triggerTime": "2026-04-11T19:08:00+00:00",
                }
            ),
        }

        event = service.process_mq_message(msg)

        self.assertIsNotNone(event)
        self.assertEqual(event.event_category, AlarmEvent.CATEGORY_ALARM)
        self.assertEqual(event.severity, AlarmEvent.SEVERITY_CRITICAL)
        self.assertEqual(event.payload["event_name"], "Alarm Triggered")
        self.assertEqual(event.payload["normalized_event_type"], "alarm_triggered")

    def test_process_mq_message_normalizes_internal_cid_system_names(self):
        service = HikPartnerService()
        cases = [
            ("MobileZoneInstantAlarm", "Instant Zone Alarm", "instant_zone_alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_CRITICAL),
            ("SoftZonePanicAlarm", "Panic Alarm", "panic_alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_CRITICAL),
            ("ClearAlarm", "Alarm Cleared", "alarm_cleared", AlarmEvent.CATEGORY_SYSTEM, AlarmEvent.SEVERITY_LOW),
            ("WiredNetworkFault", "Wired Network Fault", "wired_network_fault", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_HIGH),
            ("WiredNetworkFaultRecover", "Wired Network Fault Restored", "wired_network_fault_restored", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_LOW),
            ("Snapshot", "Snapshot Captured", "snapshot_captured", AlarmEvent.CATEGORY_INFO, AlarmEvent.SEVERITY_LOW),
        ]

        for index, (event_desc, event_name, normalized_type, category, severity) in enumerate(cases):
            msg = {
                "deviceSerial": self.device.serial_number,
                "formatType": "JSON",
                "sendTime": f"2026-04-11T19:{10 + index:02d}:00+00:00",
                "alarmData": json.dumps(
                    {
                        "eventType": "cidEvent" if event_desc != "Snapshot" else "Snapshot",
                        "eventDescription": event_desc,
                        "triggerTime": f"2026-04-11T19:{10 + index:02d}:00+00:00",
                        "CIDEvent": {"description": event_desc},
                    }
                ),
            }

            event = service.process_mq_message(msg)

            self.assertIsNotNone(event)
            self.assertEqual(event.payload["event_name"], event_name)
            self.assertEqual(event.payload["normalized_event_type"], normalized_type)
            self.assertEqual(event.event_category, category)
            self.assertEqual(event.severity, severity)
