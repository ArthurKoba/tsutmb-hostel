from core.sheets.types import RowIndex, Rows, IndexedRow, User, UserRowSection, Institutes, TypeEducation, StatusInChat
from core.loggers import parser_sheets as logger


class UserParser:
    last_room: RowIndex | None = None

    @staticmethod
    def clean_fullname(fullname: str) -> str:
        while fullname and (fullname[0].isdigit() or fullname[0] in (".", " ")):
            fullname = fullname[1:]
        return fullname

    @staticmethod
    def check_vk_link(vk_link: str) -> bool:
        if not vk_link:
            return True
        elif "https://vk.com/id" in vk_link and vk_link.replace("https://vk.com/id", "").isdigit():
            return True

    def parse(self, row: IndexedRow) -> User | None:
        # print(row)
        named_arguments = dict(row_index=row.index)
        if row.data[UserRowSection.ROOM].isdigit():
            self.last_room = int(row.data[UserRowSection.ROOM])
        elif row.data[UserRowSection.ROOM]:
            return None
        named_arguments.update(dict(room=self.last_room))
        fullname = self.clean_fullname(row.data[UserRowSection.FULLNAME])
        if fullname:
            named_arguments.update(dict(fullname=fullname))
        else:
            return None
        if row.data[UserRowSection.INSTITUTE] in Institutes:
            named_arguments.update(dict(institute=row.data[UserRowSection.INSTITUTE]))
        elif row.data[UserRowSection.INSTITUTE]:
            logger.warning(f"Неверно указан институт в строке {row.index}: {row.data[UserRowSection.INSTITUTE]}")

        if row.data[UserRowSection.COURSE].isdigit():
            named_arguments.update(dict(course=int(row.data[UserRowSection.COURSE])))
        elif row.data[UserRowSection.COURSE]:
            logger.warning(f"Неверно указан курс в строке {row.index}: {row.data[UserRowSection.COURSE]}")

        if row.data[UserRowSection.EDUCATION] in TypeEducation:
            named_arguments.update(dict(type_of_education=row.data[UserRowSection.EDUCATION]))
        elif row.data[UserRowSection.EDUCATION]:
            logger.warning(f"Неверно указан тип обучения в строке {row.index}: {row.data[UserRowSection.EDUCATION]}")

        named_arguments.update(dict(other_information=row.data[UserRowSection.ADDITIONAL_INFORMATION]))

        if self.check_vk_link(row.data[UserRowSection.VK_LINK]):
            named_arguments.update(dict(vk_link=row.data[UserRowSection.VK_LINK]))
        else:
            logger.warning(f"Неверно указана VK ссылка в строке {row.index}: {row.data[UserRowSection.VK_LINK]}")

        if row.data[UserRowSection.IN_CONVERSATION] == StatusInChat.true.value:
            named_arguments.update(dict(is_in_conversation=True))
        elif row.data[UserRowSection.IN_CONVERSATION] == StatusInChat.false.value:
            named_arguments.update(dict(is_in_conversation=False))
        else:
            logger.warning(f"Неверно указано состояние беседы в строке {row.index}: {row.data[UserRowSection.IN_CONVERSATION]}")

        user = User(**named_arguments)
        return user

user_parser = UserParser()


def _parse_row(row: IndexedRow) -> User | None:
    match len(row.data):
        case 0:
            return None
        case 8:
            return user_parser.parse(row)
        case _:
            pass
            # logger.debug("{}, {}".format(row.index, row.data))


def _parse_database(rows: Rows, start_index: RowIndex = 0) -> None:
    users = []
    for row_index in range(0, len(rows)):
        row = IndexedRow(row_index + start_index, rows[row_index])
        result = _parse_row(row)
        if type(result) is User:
            users.append(result)
    logger.info(f"Инициализировано {len(users)} пользователей!")

