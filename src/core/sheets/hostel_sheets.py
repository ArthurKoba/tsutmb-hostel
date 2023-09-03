from typing import Iterable, List, Text, Tuple

from configparser import ConfigParser

from extensions.google_sheets import GoogleSheetsApiClient
from core.loggers import hostel_sheets as logger
from json import dump, loads, dumps

from core.config import DEFAULT_RESOURCES_DIRECTORY_PATH
import os

from .models import Rows, User
from .parser import UserParser


class GoogleSheetHostel:
    def __init__(self, configs: ConfigParser):
        self._api = GoogleSheetsApiClient(
            service_account_path=configs.get("Sheets", "sheets_service_account_file_path"),
            spreadsheet_id=configs.get("Sheets", "spreadsheet_id")
        )
        self._database_sheet_name = configs.get("Sheets", "database_sheet_name")
        self._database_start_range = configs.getint("Sheets", "database_sheet_start_range")
        self._database_end_range = configs.getint("Sheets", "database_sheet_end_range")

        self.users: List[User] = []

    async def update_database(self) -> List[Text]:
        logger.debug("Обновление базы данных.")
        ranges = [
            f"{self._database_sheet_name}!A{i}:H{i}"
            for i in range(self._database_start_range, self._database_end_range + 1)
        ]
        rows = await self._api.batch_get_values(ranges)
        self.users, notes = UserParser.parse_database(rows=rows, start_index=self._database_start_range)
        # dump_directory = os.path.join(DEFAULT_RESOURCES_DIRECTORY_PATH, "database_dump.json")

        # with open(dump_directory, mode="w", encoding="utf-8") as file:
        #     file.write(dumps(rows, indent=4, ensure_ascii=False))

        # with open(dump_directory, "r", encoding="utf-8") as file:
        #     rows = loads(file.read())
        #     self.users, notes = UserParser.parse_database(rows=rows, start_index=self._database_start_range)
        return notes

    def get_all_vk_links(self) -> List[Text]:
        links = []
        for user in self.users:
            if not user.vk_link:
                continue
            links.append(user.vk_link)
        return links

    async def write_statuses_in_conversation(self, data: List[Tuple[User, bool]]):
        ranges = []
        values = []
        for user, status in data:
            print(user.fullname, user.is_in_conversation, status)
            ranges.append(f"{self._database_sheet_name}!H{user.row_index}")
            if status is True:
                values.append(["TRUE"])
            elif status is False:
                values.append(["FALSE"])
        await self._api.batch_update_values(ranges, values)

    async def start(self) -> None:
        await self._api.connect()
        await self.update_database()
