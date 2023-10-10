from asyncio import new_event_loop, AbstractEventLoop
from sys import version_info

from core.loggers import main_logger
from core.config import DEFAULT_RESOURCES_DIRECTORY_PATH, DEFAULT_CONFIG_FILENAME
from core.config_utils import get_config
from core.sheets import GoogleSheetHostel

if version_info < (3, 10):
    print("Need Python version >= 3.10")
    exit(1)


async def main(loop: AbstractEventLoop) -> None:
    main_logger.error("Запуск тестового файла.")
    configs = get_config(directory_path=DEFAULT_RESOURCES_DIRECTORY_PATH, config_filename=DEFAULT_CONFIG_FILENAME)
    hostel_sheets = GoogleSheetHostel(configs=configs)
    loop.create_task(hostel_sheets.start())


def exception_handler(loop: AbstractEventLoop, context):
    exception = context.get("exception")
    loop.stop()
    exception_type = type(exception)
    if exception_type == KeyboardInterrupt:
        main_logger.warning("Завершение приложения.")
    else:
        raise exception


def start() -> None:
    loop = new_event_loop()
    loop.set_exception_handler(exception_handler)
    loop.create_task(main(loop))
    try:
        loop.run_forever()
    except BaseException:
        pass


if __name__ == '__main__':
    start()
