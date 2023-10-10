import logging
from logging.handlers import RotatingFileHandler
from colorlog import ColoredFormatter
from os import path

from core.config import DEFAULT_LOGS_DIRECTORY_PATH

string_format = "%(log_color)s%(levelname)-8.8s|%(asctime)s| %(name)-18s| - %(message)s%(reset)s"
date_format = "%Y-%m-%d %H:%M:%S"


formatter = ColoredFormatter(fmt=string_format, datefmt=date_format)
handler = logging.StreamHandler()
handler.setFormatter(formatter)

file_handler_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | - %(message)s")
path_log_debug = path.join(DEFAULT_LOGS_DIRECTORY_PATH, "tsutmb-hostel_debug.log")
path_log_error = path.join(DEFAULT_LOGS_DIRECTORY_PATH, "tsutmb-hostel_errors.log")
file_handler_debug = RotatingFileHandler(filename=path_log_debug, maxBytes=1024 * 10, backupCount=3)
file_handler_errors = RotatingFileHandler(path_log_error, maxBytes=1024 * 10, backupCount=3)
file_handler_debug.setFormatter(file_handler_formatter)
file_handler_errors.setFormatter(file_handler_formatter)
file_handler_debug.setLevel(logging.DEBUG)
file_handler_errors.setLevel(logging.ERROR)


logging.basicConfig(
    level=logging.DEBUG,
    format=string_format,
    datefmt=date_format,
    handlers=[handler, file_handler_debug, file_handler_errors]
)

logging.getLogger("asyncio").setLevel(logging.INFO)
logging.getLogger("vkbottle").setLevel(logging.WARNING)


main_logger = logging.getLogger("tsutmb-hostel")
conversation_logger = logging.getLogger("conversation")
config_logger = logging.getLogger("config")
hostel_sheets = logging.getLogger("hostel-sheets")
parser_sheets = logging.getLogger("parser-sheets")

config_logger.setLevel(logging.INFO)

__all__ = [
    "main_logger",
    "config_logger",
    "conversation_logger",
    "hostel_sheets",
    "parser_sheets"
]