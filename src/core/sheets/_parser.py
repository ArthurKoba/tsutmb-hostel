from loguru import logger

from ._models import IndexedRow, RowIndex, Rows, User, UserRowSection


class UserParser:
    def __init__(self):
        self.last_room: int | None = None

    @staticmethod
    def fmt(index: int, text: str, value: str | int = "") -> str:
        return "{} | {}{}".format(index, text, f" {value}" if value else "")

    @staticmethod
    def check_fullname(row: IndexedRow) -> str:
        fullname = row.data[UserRowSection.FULLNAME.index]
        while fullname and (fullname[0].isdigit() or fullname[0] in (".", " ")):
            fullname = fullname[1:]
        return fullname

    def parse_user_row(self, row: IndexedRow) -> User | None:
        named_arguments = {"row_index": row.index}
        named_arguments.update(vk_id=None)
        named_arguments.update(tg_id=None)

        if not row.data:
            return None
        data = row.data

        room: str = data[UserRowSection.ROOM.index]
        if "этаж" in room.lower() or "комната" in room.lower():
            return None
        if room.isdigit():
            self.last_room = int(room)
        elif room:
            return None
        named_arguments.update({"room": self.last_room})

        fullname = self.check_fullname(row)
        if not fullname:
            return None
        named_arguments.update({"fullname": fullname})

        vk_id: str = data[UserRowSection.VK_ID.index]
        logger.debug("vk id: {}", vk_id)
        if vk_id.isdigit():
            named_arguments.update({"vk_id": int(data[UserRowSection.VK_ID.index])})
        tg_id: str = data[UserRowSection.TG_ID.index]
        if tg_id.isdigit():
            named_arguments.update({"tg_id": int(data[UserRowSection.TG_ID.index])})
        is_in_vk_conversation_raw = data[UserRowSection.IN_VK_CONVERSATION.index]
        if is_in_vk_conversation_raw:
            named_arguments["is_in_vk_conversation"] = is_in_vk_conversation_raw == "TRUE"
        is_in_tg_conversation_raw = data[UserRowSection.IN_TG_CONVERSATION.index]
        if is_in_tg_conversation_raw:
            named_arguments["is_in_tg_conversation"] = is_in_tg_conversation_raw == "TRUE"
        return User(**named_arguments)

    @classmethod
    def parse_database(cls, rows: Rows, start_index: RowIndex = 0) -> list[User]:
        users = []
        parser = UserParser()
        for row_index in range(len(rows)):
            # for row_index in range(0, 20):
            row = IndexedRow(row_index + start_index, rows[row_index])
            user = parser.parse_user_row(row)
            logger.debug("parse row: {}. user: {}", rows[row_index], user)
            if user:
                users.append(user)
        logger.info("Инициализировано {} пользователей!", len(users))
        return users
