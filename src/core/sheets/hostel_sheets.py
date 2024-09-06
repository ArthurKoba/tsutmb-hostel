from typing import Optional, List, Text, Tuple, Dict
from asyncio import sleep
from time import time

from configparser import ConfigParser

from extensions.google_sheets import GoogleSheetsApiClient
from core.loggers import hostel_sheets as logger


from .models import Rows, User
from .parser import UserParser


class GoogleSheetHostel:
    def __init__(self, configs: ConfigParser):
        self._api = GoogleSheetsApiClient(
            service_account_path=configs.get("Sheets", "sheets_service_account_file_path"),
            spreadsheet_id=configs.get("Sheets", "spreadsheet_id")
        )
        self._last_update_db: float = 0
        self._database_sheet_name = configs.get("Sheets", "database_sheet_name")
        self._database_start_range = configs.getint("Sheets", "database_sheet_start_range")
        self._database_end_range = configs.getint("Sheets", "database_sheet_end_range")

        self.users: List[User] = []
        self.muted: dict[int: Optional[int]] = {}

    def is_muted(self, user_id: int) -> bool:
        return user_id in self.muted and (self.muted[user_id] == 0 or self.muted[user_id] < time())

    async def update_database(self) -> List[Text]:
        logger.debug("Обновление базы данных.")
        ranges = [
            f"{self._database_sheet_name}!A{i}:I{i}"
            for i in range(self._database_start_range, self._database_end_range + 1)
        ]
        rows = await self._api.batch_get_values(ranges)
        try:
            self.users, notes = UserParser.parse_database(rows=rows, start_index=self._database_start_range)
            muted = dict()
            for user in self.users:
                if user.mute_end_timestamp is None:
                    continue
                if user.is_muted() and user.get_vk_id():
                    muted.update({user.get_vk_id(): user.mute_end_timestamp})
                elif user.need_clear_timestamp():
                    await self.remove_mute_user(user)
            self.muted = muted
        except Exception as e:
            logger.error(e)
            raise e
        # dump_directory = os.path.join(DEFAULT_RESOURCES_DIRECTORY_PATH, "database_dump.json")

        # with open(dump_directory, mode="w", encoding="utf-8") as file:
        #     file.write(dumps(rows, indent=4, ensure_ascii=False))

        # with open(dump_directory, "r", encoding="utf-8") as file:
        #     rows = loads(file.read())
        #     self.users, notes = UserParser.parse_database(rows=rows, start_index=self._database_start_range)
        self._last_update_db = time()
        return notes

    async def add_mute_time(self, user_id: int, timestamp: int) -> bool:
        user = self.get_user_by_vk_id(user_id)
        if not user:
            logger.debug(f"Пользователь с ID: {user_id} не обнаружен!")
            return False
        self.muted.update({user_id: timestamp})
        ranges = [f"{self._database_sheet_name}!I{user.row_index}"]
        values = [[str(timestamp)]]
        await self._api.batch_update_values(ranges, values)
        return True

    async def remove_mute_user(self, user: User):
        ranges = [f"{self._database_sheet_name}!I{user.row_index}"]
        values = [[""]]
        await self._api.batch_update_values(ranges, values)

    async def remove_mute(self, user_id: int) -> bool:
        user = self.get_user_by_vk_id(user_id)
        if not user:
            logger.debug(f"Пользователь с ID: {user_id} не обнаружен!")
            return False
        if user_id in self.muted:
            self.muted.pop(user_id)
            await self.remove_mute_user(user)
        return True

    def get_user_by_vk_id(self, user_id: int) -> Optional[User]:
        for user in self.users:
            if user.get_vk_id() == user_id:
                return user

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
            ranges.append(f"{self._database_sheet_name}!H{user.row_index}")
            if status is True:
                values.append(["TRUE"])
            elif status is False:
                values.append(["FALSE"])
        await self._api.batch_update_values(ranges, values)

    async def update_statuses(self, user_ids_in_conversation: List[int]) -> int:
        data = []
        for user in self.users:
            actual_status = user.get_vk_id() in user_ids_in_conversation
            if actual_status != user.is_in_conversation:
                data.append((user, actual_status))
        await self.write_statuses_in_conversation(data)
        return len(data)

    async def start(self) -> None:
        await self._api.connect()
        await self.update_database()
        while True:
            await sleep(1)
        #     await self.add_mute_time(198534303, 3600)
        #     await self.remove_mute(188464671)
            if time() - self._last_update_db < 60 * 5:
                continue
            await self.update_database()

    async def update_links(self, map_links: Dict[str, str]) -> int:
        ranges = []
        values = []
        for user in self.users:
            for link in map_links.keys():
                if link not in user.vk_link:
                    continue
                ranges.append(f"{self._database_sheet_name}!G{user.row_index}")
                values.append([map_links.get(link)])
        await self._api.batch_update_values(ranges, values)
        return len(ranges)

