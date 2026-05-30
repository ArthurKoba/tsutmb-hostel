from asyncio import get_running_loop
from typing import TYPE_CHECKING, Any

from vkbottle import API, Bot, LoopWrapper, SingleAiohttpClient
from vkbottle.modules import logger
from vkbottle.polling.user_polling import UserPolling

from ._labeler import Labeler

if TYPE_CHECKING:
    from vkbottle.api import ABCAPI, Token
    from vkbottle.callback import ABCCallback
    from vkbottle.dispatch import ABCRouter, ABCStateDispenser
    from vkbottle.exception_factory import ABCErrorHandler
    from vkbottle.framework.labeler import ABCLabeler
    from vkbottle.polling import ABCPolling


class BotMessagesPooling(UserPolling):
    """The bot uses the User Long Poll to get its events.
    For example, such events can be exiting or entering a conversation.
    """

    def __init__(
        self,
        api: ABCAPI | None = None,
        group_id: int | None = None,
        wait: int | None = None,
        mode: int | None = None,
        rps_delay: int | None = None,
        error_handler: ABCErrorHandler | None = None,
    ):
        super().__init__(api, wait, mode, rps_delay, error_handler)
        self.group_id = group_id

    async def get_server(self) -> dict:
        logger.debug("Getting polling server...")
        if self.group_id is None:
            result = await self.api.request("groups.getById", {})
            groups = result.get("response", {}).get("groups", [{"id": None}])
            self.group_id = groups[0]["id"]
            logger.debug("Load group_id: {}", self.group_id)
        return (await self.api.request("messages.getLongPollServer", {}))["response"]


class CustomLoopWrapper(LoopWrapper):

    def set_running(self, value: bool):
        self._running = value

class BotUserLongPool(Bot):
    def __init__(
        self,
        conversation_id: int,
        token: Token | None = None,
        polling: ABCPolling | None = None,
        callback: ABCCallback | None = None,
        router: ABCRouter | None = None,
        labeler: ABCLabeler | None = None,
        state_dispenser: ABCStateDispenser | None = None,
        error_handler: ABCErrorHandler | None = None,
        task_each_event: Any = None,
    ) -> None:

        polling = polling or BotMessagesPooling()
        labeler = labeler or Labeler(conversation_id=conversation_id)

        loop_wrapper = CustomLoopWrapper(loop=get_running_loop())
        loop_wrapper.set_running(True)

        api = API(token=token, http_client=SingleAiohttpClient())

        super().__init__(
            api=api,
            polling=polling,
            callback=callback,
            loop_wrapper=loop_wrapper,
            router=router,
            labeler=labeler,
            state_dispenser=state_dispenser,
            error_handler=error_handler,
            task_each_event=task_each_event,
        )

    @property
    def on(self) -> Labeler:
        return self.labeler
