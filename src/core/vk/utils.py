from time import time


def get_random_id() -> int:
    return int(time() * 1000)