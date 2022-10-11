from asyncio import get_event_loop, AbstractEventLoop

from core.config import get_config
from core.loggers import main_logger
from core.vk.conversation import GroupConversation


async def main(loop: AbstractEventLoop) -> None:
    main_logger.info("Запуск приложения.")

    configs = get_config()
    group_access_token = configs.get("Tokens", "group_access_token")
    conversation_id = configs.getint("Conversation", "conversation_id")
    notification_join_offset = configs.getint("Conversation", "notification_join_offset")

    group_conversation = GroupConversation(
        access_token=group_access_token, conversation_id=conversation_id, loop=loop,
        notification_join_offset=notification_join_offset
    )

    loop.create_task(group_conversation.start())


def exception_handler(loop: AbstractEventLoop, context):
    exception = context.get("exception")
    loop.stop()
    raise exception


def start() -> None:
    loop = get_event_loop()
    loop.set_exception_handler(exception_handler)
    try:
        loop.create_task(main(loop))
        loop.run_forever()
    except KeyboardInterrupt:
        main_logger.warning("Завершение работы программы!")


if __name__ == '__main__':
    start()
