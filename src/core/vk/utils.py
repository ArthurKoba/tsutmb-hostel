from time import time
from typing import Optional, Text, List


def get_random_id() -> int:
    return int(time() * 1000)


def get_vk_id_from_link(link: Text) -> Optional[int]:
    try:
        return int(link.replace("https://vk.com/id", ""))
    except ValueError:
        return


def get_vk_ids_from_list_links(links: List[Text]) -> List[int]:
    ids = []
    for link in links:
        _id = get_vk_id_from_link(link)
        if _id:
           ids.append(_id)
    return ids