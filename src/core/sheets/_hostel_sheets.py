from asyncio import sleep
from json import dumps, loads
from time import time
from typing import TYPE_CHECKING

from loguru import logger

from integration.google_sheets import GoogleSheetsApiClient

from ._models import User, UserRowSection
from ._parser import UserParser

if TYPE_CHECKING:
    from pathlib import Path

    from settings import ApplicationSettings


class GoogleSheetHostel:
    def __init__(self, settings: ApplicationSettings):
        self._api = GoogleSheetsApiClient(
            service_account_path=settings.get_service_account_file_path(),
            spreadsheet_id=settings.SPREADSHEET_ID,
        )
        self._last_update_db: float = 0

        self._database_sheet_name = settings.DATABASE_SHEET_NAME
        self._database_start_range = settings.DATABASE_SHEET_START_RANGE
        self._database_end_range = settings.DATABASE_SHEET_END_RANGE

        self._mock_database_file_path: Path | None = settings.get_mock_database_path()

        self.users: list[User] = []

    async def update_database(self):

        if self._mock_database_file_path and self._mock_database_file_path.exists():
            logger.warning("Загрузка базы из mock файла {}.", self._mock_database_file_path)
            with self._mock_database_file_path.open(encoding="utf-8") as file:
                rows = loads(file.read())

            self.users = UserParser.parse_database(
                rows=rows, start_index=self._database_start_range
            )
        else:
            logger.debug("Обновление базы данных.")
            ranges = [
                f"{self._database_sheet_name}!A{i}:N{i}"
                for i in range(self._database_start_range, self._database_end_range + 1)
            ]
            rows = await self._api.batch_get_values(ranges)
            if self._mock_database_file_path:
                logger.debug(
                    "Запись базы данных в mock файл {}", self._mock_database_file_path.name
                )
                with self._mock_database_file_path.open(mode="w", encoding="utf-8") as file:
                    file.write(dumps(rows, indent=4, ensure_ascii=False))
            self.users = UserParser.parse_database(
                rows=rows, start_index=self._database_start_range
            )
        self._last_update_db = time()

    def get_user_by_vk_id(self, user_id: int) -> User | None:
        for user in self.users:
            if user.vk_id == user_id:
                return user
        return None

    def get_all_vk_ids(self) -> list[str]:
        links = []
        for user in self.users:
            if not user.vk_id:
                continue
            links.append(user.vk_id)
        return links

    async def write_statuses_in_vk_conversation(self, data: list[tuple[User, bool]]):
        ranges = []
        values = []
        for user, status in data:
            ranges.append(
                f"{self._database_sheet_name}!{UserRowSection.IN_VK_CONVERSATION.letter}{user.row_index}"
            )
            values.append([str(status).upper()])
        await self._api.batch_update_values(ranges, values)

    async def update_vk_statuses(self, user_ids_in_vk_conversation: list[int]) -> int:
        data = []
        for user in self.users:
            actual_status = user.vk_id in user_ids_in_vk_conversation
            if actual_status != user.is_in_vk_conversation:
                data.append((user, actual_status))
        await self.write_statuses_in_vk_conversation(data)
        return len(data)

    async def start(self) -> None:
        logger.info("Запуск сервиса Google таблиц")
        await self._api.connect()
        await self.update_database()
        logger.info("База загружена: {} пользоватлеей", len(self.users))
        while True:
            await sleep(1)
            if time() - self._last_update_db < 60 * 5:
                continue
            await self.update_database()
