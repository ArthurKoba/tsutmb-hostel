from asyncio import create_task, run

from loguru import logger

from constants import LOGS_DIR
from core import VKManager
from core.sheets import GoogleSheetHostel
from settings import ApplicationSettings
from utils import setup_logging


async def main() -> None:
    setup_logging(level="DEBUG", logs_base_path=LOGS_DIR)
    logger.error("Запуск тестового файла.")
    settings = ApplicationSettings.load()
    hostel_sheets = GoogleSheetHostel(settings=settings)
    hostel_sheets_task = create_task(hostel_sheets.start())
    vk_manager = VKManager(settings=settings, hostel_sheets=hostel_sheets)
    await vk_manager.test()
    hostel_sheets_task.cancel()


if __name__ == "__main__":
    run(main)
