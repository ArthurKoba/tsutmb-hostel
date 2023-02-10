import logging
from colorlog import ColoredFormatter

string_format = "%(log_color)s%(levelname)-8.8s|%(asctime)s| %(name)-18s| - %(message)s%(reset)s"
date_format = "%Y-%m-%d %H:%M:%S"


formatter = ColoredFormatter(fmt=string_format, datefmt=date_format)
handler = logging.StreamHandler()
handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.DEBUG,
    format=string_format,
    datefmt=date_format,
    handlers=[handler]
)

logging.getLogger("asyncio").setLevel(logging.INFO)
logging.getLogger("vkbottle").setLevel(logging.WARNING)


main_logger = logging.getLogger("tsutmb-hostel")
conversation_logger = logging.getLogger("conversation")
config_logger = logging.getLogger("config")

config_logger.setLevel(logging.INFO)

__all__ = [
    "main_logger",
    "config_logger",
    "conversation_logger",
]