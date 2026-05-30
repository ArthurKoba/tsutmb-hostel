from asyncio import create_task, run

from loguru import logger

from constants import LOGS_DIR
from core import GoogleSheetHostel, VKManager
from settings import ApplicationSettings
from utils import setup_logging


async def main():
    setup_logging(level="DEBUG", logs_base_path=LOGS_DIR)
    logger.disable("core.sheets._parser")

    logger.info("Запуск приложения.")
    settings = ApplicationSettings.load()
    hostel_sheets = GoogleSheetHostel(settings=settings)
    vk_manager = VKManager(settings=settings, hostel_sheets=hostel_sheets)
    hostel_task = create_task(hostel_sheets.start())
    await vk_manager.run()
    hostel_task.cancel()

if __name__ == "__main__":
    try:
        run(main())
    except KeyboardInterrupt:
        logger.warning("Завершение работы программы!")
