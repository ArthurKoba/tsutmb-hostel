from asyncio import new_event_loop, AbstractEventLoop, Task

from core.config import get_config
from core.loggers import main_logger
from core.vk.conversation import GroupConversation


def exception_handler(_loop: AbstractEventLoop, context):
    exception = context.get("exception")
    if context.get('message') == "Task was destroyed but it is pending!" and type(context.get('task')) == Task:
        task: Task = context.get('task')
        main_logger.warning(f"Task destroyed: {task.get_name()} ({task.get_coro()})")
        return
    main_logger.critical(f"Exception: {context.get('message', 'NO MSG')}")
    raise exception


if __name__ == '__main__':
    main_logger.info("Запуск приложения.")
    loop = new_event_loop()
    loop.set_exception_handler(exception_handler)

    configs = get_config()

    group_access_token = configs.get("Tokens", "group_access_token")
    conversation_id = configs.getint("Conversation", "conversation_id")
    notification_join_offset = configs.getint("Conversation", "notification_join_offset")

    group_conversation = GroupConversation(
        configs=configs,
        loop=loop,
        notification_join_offset=notification_join_offset
    )

    group_conversation_task: Task = loop.create_task(group_conversation.start())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        main_logger.warning("Завершение работы программы!")
    except BaseException as e:
        main_logger.critical(f"Программа остановлена по ошибке: {e}")
