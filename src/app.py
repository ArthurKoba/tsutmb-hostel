from asyncio import CancelledError, create_task, run
from contextlib import suppress

from loguru import logger

from constants import LOGS_DIR
from core import GoogleSheetHostel, VKManager
from settings import ApplicationSettings
from telemetry import setup_telemetry
from utils import setup_logging


async def main() -> None:
    settings = ApplicationSettings.load()
    setup_logging(
        level="DEBUG",
        logs_base_path=LOGS_DIR,
        console_enabled=settings.LOG_CONSOLE_ENABLED,
        log_to_file=settings.LOG_FILE_ENABLED,
    )
    shutdown_telemetry = setup_telemetry(settings)
    logger.disable("core.sheets._parser")

    hostel_task = None
    try:
        logger.info("Запуск приложения.")
        hostel_sheets = GoogleSheetHostel(settings=settings)
        vk_manager = VKManager(settings=settings, hostel_sheets=hostel_sheets)
        hostel_task = create_task(hostel_sheets.start())
        await vk_manager.run()
    except Exception:
        logger.exception("Приложение остановлено из-за необработанной ошибки")
        raise
    finally:
        if hostel_task is not None:
            hostel_task.cancel()
            with suppress(CancelledError):
                await hostel_task
        shutdown_telemetry()


if __name__ == "__main__":
    try:
        run(main())
    except KeyboardInterrupt:
        logger.warning("Завершение работы программы!")
