from pydantic_settings import BaseSettings, SettingsConfigDict

from constants import BASE_PATH


class ApplicationSettings(BaseSettings):
    GROUP_ACCESS_TOKEN: str

    CONVERSATION_ID: int
    NOTIFICATION_JOIN_OFFSET: int = 20
    ADMINS_CONVERSATION_ID: int

    SHEETS_SERVICE_ACCOUNT_FILENAME: str = "service_account.json"
    SPREADSHEET_ID: str
    DATABASE_SHEET_NAME: str = "181Б"
    DATABASE_SHEET_START_RANGE: int = 1
    DATABASE_SHEET_END_RANGE: int = 500
    DATABASE_MOCK_FILENAME: str | None = None

    model_config = SettingsConfigDict(extra="forbid")

    def get_service_account_file_path(self) -> str:
        return BASE_PATH / self.SHEETS_SERVICE_ACCOUNT_FILENAME

    def get_mock_database_path(self) -> str | None:
        return BASE_PATH / self.DATABASE_MOCK_FILENAME if self.DATABASE_MOCK_FILENAME else None

    @classmethod
    def load(cls) -> ApplicationSettings:
        return ApplicationSettings()
