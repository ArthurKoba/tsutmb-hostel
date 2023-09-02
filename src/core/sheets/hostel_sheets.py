from typing import Iterable

from configparser import ConfigParser

from extensions.google_sheets import GoogleSheetsApiClient
from core.loggers import hostel_sheets as logger
from json import dump, loads

from core.config import DEFAULT_RESOURCES_DIRECTORY_PATH
import os

from .types import Rows
from .parser import _parse_database





class GoogleSheetHostel:
    def __init__(self, configs: ConfigParser):
        self._api = GoogleSheetsApiClient(
            service_account_path=configs.get("Sheets", "sheets_service_account_file_path"),
            spreadsheet_id=configs.get("Sheets", "spreadsheet_id")
        )
        self._database_sheet_name = configs.get("Sheets", "database_sheet_name")
        self._database_start_range = configs.getint("Sheets", "database_sheet_start_range")
        self._database_end_range = configs.getint("Sheets", "database_sheet_end_range")


    async def _load_database(self) -> None:
        # ranges = [f"{self._database_sheet_name}!A{self._database_start_range}:H{self._database_end_range}"]
        # values = await self._api.batch_get_values(ranges)

        dump_directory = os.path.join(DEFAULT_RESOURCES_DIRECTORY_PATH, "database_dump.json")
        # with open(dump_directory, mode="w", encoding="utf-8") as file:
        #     dump(values, file, indent=4, ensure_ascii=False)
        with open(dump_directory, "r", encoding="utf-8") as file:
            rows = loads(file.read())
            _parse_database(rows=rows)


        # for i in range(len(values)):
        #     line = values[i]
        #     if not line:
        #         continue
        #     if not line[0]:
        #         line[0] = values[i - 1][0]
        #
        #     database_row_number = i + self._database_ranges[0]
        #     for column in line:
        #         if "https://vk.com/id" not in column:
        #             continue
        #         string_vk_id = column.replace("https://vk.com/id", "")
        #         if "https://vk.com/id" not in column or not string_vk_id.isdigit():
        #             logger.warning(f"Ошибка в оформлении ссылки в строке {database_row_number} {column}")
        #             continue
        #         vk_id = int(string_vk_id)
        #         self._database.update({vk_id: database_row_number})
        #     # logger.debug(f"[{database_row_number}] {line}")
        # self._is_databases_loaded = True
        # logger.info(f"База данных загруженна! Количество пользователей: {len(self._database)}")
        # range = 'Tests!A1:B1'
        # values1 = await api.GetValues(range)
        # print(values1)
        #
        # ranges = ['Tests!A1:B1', 'Tests!A2:B2']
        # values2 = await api.BatchGetValues(ranges)
        # print(values2)

        # range = 'Tests!C2'
        # values1 = ['FALSE']
        # await api.UpdateValues(range, values1, "COLUMNS")

        # ranges = ['Tests!A4:B4', 'Tests!A6:B6']
        # values2 = [['A4', 'B4'], ['A6','B6']]
        # await api.BatchUpdateValues(ranges, values2)

    async def write_status_in_conversation(self, status_list: list[dict[int, bool]]):
        ranges = []
        values = []
        for target_status in status_list:
            user_id = target_status.get("user_id")
            status = target_status.get("status")
            row_number = self._database.get(user_id, None)
            print(row_number, user_id, status)
            ranges.append(f"{self._database_sheet_name}!H{row_number}")
            if status is True:
                values.append(["TRUE"])
            elif status is False:
                values.append(["FALSE"])
        # for i in range(len(ranges)):

            # print(ranges[i], values[i])
        await self._api.batch_update_values(ranges, values)
        # await self._api.update_values(target_range, values, "COLUMNS")

    async def start(self) -> None:
        # await self._api.connect()
        # result = await self._api.get_values(sheet_range=f"{self._database_sheet_name}!A1:H1")
        await self._load_database()
