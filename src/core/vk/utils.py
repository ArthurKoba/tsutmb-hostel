from time import time
from typing import Optional, Text, List
from datetime import timedelta, datetime


def get_random_id() -> int:
    return int(time() * 1000)


def get_vk_id_from_link(link: Text) -> Optional[int]:
    if not "https://vk.com/id" in link:
        return None
    try:
        return int(link.replace("https://vk.com/id", ""))
    except ValueError:
        return None


def get_vk_ids_from_list_links(links: List[Text]) -> List[int]:
    ids = []
    for link in links:
        _id = get_vk_id_from_link(link)
        if _id:
           ids.append(_id)
    return ids

def get_timestamp_from_minutes_offset(cmd: str) -> int | None:
    try:
        minutes = int(cmd)
        if minutes < 0 or 0:
            return None
        datetime_unmute = datetime.now() + timedelta(minutes=minutes)
        return int(datetime_unmute.timestamp())
    except ValueError:
        return None

def timestamp_to_string(timestamp: int) -> str:
    unmute_date = datetime.fromtimestamp(timestamp)
    return unmute_date.strftime("%H:%M %d-%m-%Y")