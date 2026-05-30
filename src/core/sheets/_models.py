from dataclasses import dataclass
from typing import NamedTuple

RowIndex = int
Row = list[str]
Rows = list[Row]


class IndexedRow(NamedTuple):
    index: RowIndex
    data: Row


class DatabaseRowSection(NamedTuple):
    index: int
    letter: str


class UserRowSection:
    ROOM = DatabaseRowSection(0, "A")
    FULLNAME = DatabaseRowSection(1, "B")
    BIRTHDATE = DatabaseRowSection(2, "C")

    INSTITUTE = DatabaseRowSection(3, "D")
    STAGE_OF_STUDY = DatabaseRowSection(4, "E")
    COURSE = DatabaseRowSection(5, "F")
    EDUCATION = DatabaseRowSection(6, "G")
    NOTE = DatabaseRowSection(7, "H")
    VK_ID = DatabaseRowSection(8, "I")
    TG_ID = DatabaseRowSection(9, "J")
    VK_LINK = DatabaseRowSection(10, "K")
    TG_LINK = DatabaseRowSection(11, "L")
    IN_VK_CONVERSATION = DatabaseRowSection(12, "M")
    IN_TG_CONVERSATION = DatabaseRowSection(13, "N")


@dataclass(frozen=False, kw_only=True)
class User:
    row_index: int
    room: int
    fullname: str
    vk_id: int | None
    tg_id: str | None
    is_in_vk_conversation: bool
    is_in_tg_conversation: bool
    is_normalize: bool = False

    def __repr__(self):
        formatter_string = "User"
        formatter_string += f"[{self.room}] (" if self.room else "("
        formatter_string += f"{self.fullname}" if self.fullname else "Null"
        return formatter_string + ")"
