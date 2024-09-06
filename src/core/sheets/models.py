from typing import NamedTuple, Sequence, Text, Optional, List
from enum import Enum
from dataclasses import dataclass, field

RowIndex = int
Row = Sequence[Text]
Rows = Sequence[Row]


class IndexedRow(NamedTuple):
    index: RowIndex
    data: Row


class UserRowSection:
    ROOM = 0
    FULLNAME = 1
    INSTITUTE = 2
    COURSE = 3
    EDUCATION = 4
    ADDITIONAL_INFORMATION = 5
    VK_LINK = 6
    IN_CONVERSATION = 7
    MUTE_END_TIMESTAMP = 8


Institutes = ("ИМФИТ", "ФКИ", "ФФКС", "ФФЖ", "ФИМПС", "ИЭУС", "ИПНБ", "Мед.", "ИЕ", "Пед.")
TypeEducation = ("бюджет", "договор", "целевое")


class StatusInChat(Enum):
    true = "TRUE"
    false = "FALSE"


@dataclass(frozen=False, kw_only=True)
class User:
    row_index: int
    room: int
    fullname: str
    institute: str = None
    course: int = None
    type_of_education: str = None
    other_information: str = None
    vk_link: str = None
    is_in_conversation: bool = None
    mute_end_timestamp: int = None
    is_normalize: bool = False

    def __repr__(self):
        formatter_string = "User"
        formatter_string += f"[{self.room}] (" if self.room else "("
        formatter_string += f"{self.fullname}" if self.fullname else "Null"
        formatter_string += f", {self.institute}" if self.institute else ""
        formatter_string += f", {self.course}" if self.course else ""
        formatter_string += f", {self.type_of_education}" if self.type_of_education else ""
        # formatter_string += f", {self.other_information}" if self.other_information else ""
        formatter_string += f", {self.vk_link}" if self.vk_link else ""
        formatter_string += f", {self.is_in_conversation}" if self.is_in_conversation else ""
        return formatter_string + ")"

    def get_vk_id(self) -> Optional[int]:
        if not self.vk_link or not self.vk_link.startswith("https://vk.com/id"):
            return None
        try:
            string_id = self.vk_link.replace("https://vk.com/id", "")
            return int(string_id)
        except ValueError:
            return None


@dataclass(kw_only=True, frozen=False)
class ParseRowResult:
    user: Optional[User] = None
    warnings: List[Text] = field(default_factory=list)
    errors: List[Text] = field(default_factory=list)

