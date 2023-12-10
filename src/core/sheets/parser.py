from time import time
from typing import List, Text, Tuple, Optional
from core.sheets.models import \
    RowIndex, Rows, IndexedRow, \
    User, UserRowSection, \
    Institutes, TypeEducation, StatusInChat, \
    ParseRowResult
from core.loggers import parser_sheets as logger


class UserParser:

    @staticmethod
    def fmt(index: int, text: Text, value: Text | int = "") -> Text:
        return "{} | {}{}".format(index, text, f" {value}" if value else "")

    @staticmethod
    def check_fullname(row: IndexedRow, result: ParseRowResult) -> Optional[Text]:
        fullname = row.data[UserRowSection.FULLNAME]
        while fullname and (fullname[0].isdigit() or fullname[0] in (".", " ")):
            fullname = fullname[1:]
        return fullname

    @staticmethod
    def check_vk_link(vk_link: str) -> bool:
        if not vk_link:
            return True
        elif "https://vk.com/id" in vk_link and vk_link.replace("https://vk.com/id", "").isdigit():
            return True

    @classmethod
    def parse_row(cls, row: IndexedRow, last_room: int = None) -> ParseRowResult:
        result = ParseRowResult()
        named_arguments = dict(row_index=row.index)

        if not row.data:
            return result

        room = row.data[UserRowSection.ROOM]
        if "этаж" in room.lower() or "комната" in room.lower():
            return result
        elif room.isdigit():
            last_room = int(room)
        elif room:
            result.errors.append(cls.fmt(row.index, "Значение комнаты неверно!", room))
            return result
        named_arguments.update(dict(room=last_room))

        fullname = cls.check_fullname(row, result)
        if not fullname:
            return result
        named_arguments.update(dict(fullname=fullname))

        institute = row.data[UserRowSection.INSTITUTE]
        if institute in Institutes:
            named_arguments.update(dict(institute=institute))
        elif institute:
            result.warnings.append(cls.fmt(row.index, "Неверно указан институт! ({}) ".format(institute)))

        course = row.data[UserRowSection.COURSE]
        if course.isdigit():
            named_arguments.update(dict(course=int(course)))
        elif course:
            result.warnings.append(cls.fmt(row.index, "Неверно указан курс!", course))
        else:
            result.warnings.append(cls.fmt(row.index, "Курс не установлен!"))

        education = row.data[UserRowSection.EDUCATION]
        if education in TypeEducation:
            named_arguments.update(dict(type_of_education=row.data[UserRowSection.EDUCATION]))
        elif education:
            result.warnings.append(cls.fmt(row.index, "Неверно указан тип обучения!", education))
        else:
            result.warnings.append(cls.fmt(row.index, "Не установлен тип обучения!", education))

        named_arguments.update(dict(other_information=row.data[UserRowSection.ADDITIONAL_INFORMATION]))

        vk_link = row.data[UserRowSection.VK_LINK]
        if cls.check_vk_link(vk_link):
            named_arguments.update(dict(vk_link=vk_link))
        elif vk_link:
            result.warnings.append(cls.fmt(row.index, "Неверно указана ссылка на ВК!", vk_link))
        else:
            result.warnings.append(cls.fmt(row.index, "Не установлена ссылка ВК!"))

        is_in_conversation = row.data[UserRowSection.IN_CONVERSATION]
        if is_in_conversation == StatusInChat.true.value:
            named_arguments.update(dict(is_in_conversation=True))
        elif row.data[UserRowSection.IN_CONVERSATION] == StatusInChat.false.value:
            named_arguments.update(dict(is_in_conversation=False))
        else:
            result.warnings.append(cls.fmt(row.index, "Неверно указано нахождение в беседе!", is_in_conversation))

        if len(row.data) >= 9:
            mute_end_timestamp = row.data[UserRowSection.MUTE_END_TIMESTAMP]
            if mute_end_timestamp and mute_end_timestamp.isdigit():
                mute_end_timestamp = int(mute_end_timestamp)
                named_arguments.update(dict(mute_end_timestamp=mute_end_timestamp))
            else:
                mute_end_timestamp = 0
            if mute_end_timestamp and time() > mute_end_timestamp:
                result.warnings.append(cls.fmt(row.index, "Время мута не актуально!", mute_end_timestamp))
            else:
                result.warnings.append(cls.fmt(row.index, "Неверно указано время окончания мута!", mute_end_timestamp))

        result.user = User(**named_arguments)
        return result

    @classmethod
    def parse_database(cls, rows: Rows, start_index: RowIndex = 0) -> Tuple[List[User], List[Text]]:
        last_room = None
        users = []
        notes = []
        for row_index in range(0, len(rows)):
        # for row_index in range(0, 20):
            row = IndexedRow(row_index + start_index, rows[row_index])
            result = UserParser.parse_row(row, last_room)
            notes.extend(result.warnings)
            notes.extend(result.errors)
            if result.user:
                users.append(result.user)
                last_room = result.user.room
        logger.debug(f"Инициализировано {len(users)} пользователей!")
        return users, notes


