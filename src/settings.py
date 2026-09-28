from __future__ import annotations

from json import JSONDecodeError, loads
from typing import TYPE_CHECKING

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from constants import BASE_PATH

if TYPE_CHECKING:
    from pathlib import Path


class ApplicationSettings(BaseSettings):
    GROUP_ACCESS_TOKEN: SecretStr
    CONVERSATION_ID: int
    NOTIFICATION_JOIN_OFFSET: int = 20
    ADMINS_CONVERSATION_ID: int

    SHEETS_SERVICE_ACCOUNT_JSON: SecretStr | None = None
    SHEETS_SERVICE_ACCOUNT_FILENAME: str = "service_account.json"
    SPREADSHEET_ID: str
    DATABASE_SHEET_NAME: str = "181Б"
    DATABASE_SHEET_START_RANGE: int = 1
    DATABASE_SHEET_END_RANGE: int = 500
    DATABASE_MOCK_FILENAME: str | None = None

    LOG_CONSOLE_ENABLED: bool = True
    LOG_FILE_ENABLED: bool = False

    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "tsutmb-hostel"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    OTEL_EXPORTER_OTLP_HEADERS: SecretStr | None = None
    OTEL_LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_observability(self) -> ApplicationSettings:
        if self.OTEL_ENABLED and not self.OTEL_EXPORTER_OTLP_ENDPOINT:
            msg = "OTEL_EXPORTER_OTLP_ENDPOINT is required when OTEL_ENABLED=true"
            raise ValueError(msg)
        if not (self.LOG_CONSOLE_ENABLED or self.LOG_FILE_ENABLED or self.OTEL_ENABLED):
            msg = "At least one logging sink must be enabled"
            raise ValueError(msg)
        return self

    def get_service_account_credentials(self) -> dict[str, str]:
        if self.SHEETS_SERVICE_ACCOUNT_JSON is not None:
            raw_credentials = self.SHEETS_SERVICE_ACCOUNT_JSON.get_secret_value().strip()
            if raw_credentials:
                return self._parse_json_object(raw_credentials, "SHEETS_SERVICE_ACCOUNT_JSON")

        path = BASE_PATH / self.SHEETS_SERVICE_ACCOUNT_FILENAME
        try:
            raw_credentials = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = (
                "Google service-account credentials are not configured. "
                "Set SHEETS_SERVICE_ACCOUNT_JSON or provide "
                f"{self.SHEETS_SERVICE_ACCOUNT_FILENAME} in {BASE_PATH}."
            )
            raise FileNotFoundError(msg) from exc
        return self._parse_json_object(raw_credentials, str(path))

    def get_mock_database_path(self) -> Path | None:
        return BASE_PATH / self.DATABASE_MOCK_FILENAME if self.DATABASE_MOCK_FILENAME else None

    def get_otel_logs_endpoint(self) -> str:
        if self.OTEL_EXPORTER_OTLP_ENDPOINT is None:
            msg = "OTEL_EXPORTER_OTLP_ENDPOINT is not configured"
            raise ValueError(msg)
        endpoint = self.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip("/")
        return endpoint if endpoint.endswith("/v1/logs") else f"{endpoint}/v1/logs"

    def get_otel_headers(self) -> dict[str, str] | None:
        if self.OTEL_EXPORTER_OTLP_HEADERS is None:
            return None
        raw_headers = self.OTEL_EXPORTER_OTLP_HEADERS.get_secret_value().strip()
        if not raw_headers:
            return None
        headers: dict[str, str] = {}
        for item in raw_headers.split(","):
            key, separator, value = item.partition("=")
            if not separator or not key.strip():
                msg = "OTEL_EXPORTER_OTLP_HEADERS must use comma-separated key=value pairs"
                raise ValueError(msg)
            headers[key.strip()] = value.strip()
        return headers

    @staticmethod
    def _parse_json_object(raw_value: str, source: str) -> dict[str, str]:
        try:
            value = loads(raw_value)
        except JSONDecodeError as exc:
            msg = f"Invalid JSON in {source}"
            raise ValueError(msg) from exc
        if not isinstance(value, dict):
            msg = f"{source} must contain a JSON object"
            raise TypeError(msg)
        return value

    @classmethod
    def load(cls) -> ApplicationSettings:
        return cls()
