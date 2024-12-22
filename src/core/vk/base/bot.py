from typing import TYPE_CHECKING, Optional

from aiohttp import ClientSession, ClientResponse
from vkbottle import Bot, API, SingleAiohttpClient
from vkbottle.modules import logger
from vkbottle.polling.user_polling import UserPolling
from vkbottle.tools import LoopWrapper

from .labeler import Labeler

if TYPE_CHECKING:
    from vkbottle.callback import ABCCallback
    from vkbottle.polling import ABCPolling
    from vkbottle.api import ABCAPI, Token
    from vkbottle.exception_factory import ABCErrorHandler
    from vkbottle.dispatch import ABCRouter, ABCStateDispenser
    from vkbottle.framework.labeler import ABCLabeler


class NoSSLAiohttp(SingleAiohttpClient):
    async def request_raw(
        self,
        url: str,
        method: str = "GET",
        data: Optional[dict] = None,
        **kwargs,
    ) -> "ClientResponse":
        if not self.session:
            self.session = ClientSession(
                json_serialize=self.json_processing_module.dumps,
                **self._session_params,
            )
        kwargs.setdefault("ssl", False)
        async with self.session.request(url=url, method=method, data=data, **kwargs) as response:
            await response.read()
            return response

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
            result = await self.api.request("groups.getById", {})
            self.group_id = result["response"][0]["id"]
        return (await self.api.request("messages.getLongPollServer", {}))["response"]


class BotUserLongPool(Bot):
    def __init__(self, token: Optional["Token"] = None, api: Optional["ABCAPI"] = None,
                 polling: Optional["ABCPolling"] = None, callback: Optional["ABCCallback"] = None,
                 loop_wrapper: Optional[LoopWrapper] = None, router: Optional["ABCRouter"] = None,
                 labeler: Optional["ABCLabeler"] = None, state_dispenser: Optional["ABCStateDispenser"] = None,
                 conversation_id: int = None, error_handler: Optional["ABCErrorHandler"] = None):

        polling = polling or BotMessagesPooling()
        labeler = labeler or Labeler(conversation_id=conversation_id)

        http_client = NoSSLAiohttp()
        api = API(token=token, http_client=http_client)

        super().__init__(
            api=api, polling=polling, callback=callback, loop_wrapper=loop_wrapper,
            router=router, labeler=labeler, state_dispenser=state_dispenser,
            error_handler=error_handler)

    @property
    def on(self) -> Labeler:
        return self.labeler
