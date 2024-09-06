from asyncio import new_event_loop, AbstractEventLoop, Task
from os import mkdir, path

from core.config import DEFAULT_CONFIG_FILENAME, DEFAULT_RESOURCES_DIRECTORY_PATH, DEFAULT_LOGS_DIRECTORY_PATH

if __name__ == '__main__':
    if not path.exists(DEFAULT_RESOURCES_DIRECTORY_PATH):
        mkdir(DEFAULT_RESOURCES_DIRECTORY_PATH)
    if not path.exists(DEFAULT_LOGS_DIRECTORY_PATH):
        mkdir(DEFAULT_LOGS_DIRECTORY_PATH)

from core.loggers import main_logger
from core.sheets import GoogleSheetHostel
from core.vk.manager import VKManager
from core.config_utils import get_config


def exception_handler(_loop: AbstractEventLoop, context):
    exception = context.get("exception")
    if context.get('message') == "Task was destroyed but it is pending!" and type(context.get('task')) == Task:
        task: Task = context.get('task')
        main_logger.warning(f"Task destroyed: {task.get_name()} ({task.get_coro()})")
        return
    _loop.stop()
    _loop.close()
    raise exception


if __name__ == '__main__':
    main_logger.info("Запуск приложения.")
    loop = new_event_loop()
    loop.set_exception_handler(exception_handler)

    configs = get_config(directory_path=DEFAULT_RESOURCES_DIRECTORY_PATH, config_filename=DEFAULT_CONFIG_FILENAME)
    hostel_sheets = GoogleSheetHostel(configs=configs)
    vk_manager = VKManager(configs=configs, loop=loop, hostel_sheets=hostel_sheets)

    loop.create_task(vk_manager.start())
    # loop.create_task(hostel_sheets.start())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        main_logger.warning("Завершение работы программы!")
    except BaseException as e:
        main_logger.critical(f"Программа остановлена по ошибке: {e}", exc_info=True)
