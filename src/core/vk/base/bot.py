import asyncio
from typing import TYPE_CHECKING, Optional

from vkbottle import Bot
from vkbottle.framework.labeler import UserLabeler
from vkbottle.modules import logger
from vkbottle.polling.user_polling import UserPolling
from vkbottle.tools import LoopWrapper

if TYPE_CHECKING:
    from vkbottle.callback import ABCCallback
    from vkbottle.polling import ABCPolling
    from vkbottle.api import ABCAPI, Token
    from vkbottle.exception_factory import ABCErrorHandler
    from vkbottle.dispatch import ABCRouter, ABCStateDispenser
    from vkbottle.framework.labeler import ABCLabeler


class BotMessagesPooling(UserPolling):
    """The bot uses the User Long Poll to get its events.
    For example, such events can be exiting or entering a conversation.
    """

    def __init__(
        self,
        api: Optional["ABCAPI"] = None,
        group_id: Optional[int] = None,
        wait: Optional[int] = None,
        mode: Optional[int] = None,
        rps_delay: Optional[int] = None,
        error_handler: Optional["ABCErrorHandler"] = None,
    ):
        super().__init__(api, wait, mode, rps_delay, error_handler)
        self.group_id = group_id

    async def get_server(self) -> dict:
        logger.debug("Getting polling server...")
        if self.group_id is None:
            self.group_id = (await self.api.request("groups.getById", {}))["response"][0]["id"]
        return (await self.api.request("messages.getLongPollServer", {}))["response"]


class BotUserLongPool(Bot):
    def __init__(self, token: Optional["Token"] = None, api: Optional["ABCAPI"] = None,
                 polling: Optional["ABCPolling"] = None, callback: Optional["ABCCallback"] = None,
                 loop: Optional[asyncio.AbstractEventLoop] = None, loop_wrapper: Optional[LoopWrapper] = None,
                 router: Optional["ABCRouter"] = None, labeler: Optional["ABCLabeler"] = None,
                 state_dispenser: Optional["ABCStateDispenser"] = None,
                 error_handler: Optional["ABCErrorHandler"] = None, task_each_event: bool = True):

        polling = polling or BotMessagesPooling()
        labeler = labeler or UserLabeler()

        super().__init__(token, api, polling, callback, loop, loop_wrapper, router, labeler, state_dispenser,
                         error_handler, task_each_event)
