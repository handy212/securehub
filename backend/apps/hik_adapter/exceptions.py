class HikPartnerError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        payload: dict | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = str(error_code) if error_code is not None else None
        self.payload = payload or {}
        self.status_code = status_code
