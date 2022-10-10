from asyncio import AbstractEventLoop, gather
from typing import Set

from vkbottle import User
from vkbottle_types.events.enums import UserEventType
from vkbottle_types.events.user_events import RawUserEvent

from core.loggers import old_conversation_logger as logger


class UserOldConversation:
    def __init__(self, access_token: str, conversation_id: int, loop: AbstractEventLoop):
        self._conversation_id_old = conversation_id
        self.user = User(access_token, loop=loop)
        self.api = self.user.api
        self.user.on.raw_event(UserEventType.MESSAGE_NEW)(self.process_message)
        self._conversation_admins: Set[int] = set()
        self._conversation_users: Set[int] = set()

    async def kick_user_from_old_conversation(self, user_id: int) -> bool:
        if user_id in self._conversation_admins:
            return logger.debug(f"Пользователь с id: {user_id} не исключен, так как он админ.")
        elif user_id not in self._conversation_users:
            return logger.debug(f"Пользователь с id: {user_id} не присутствует в беседе!")
        try:
            chat_id = self._conversation_id_old - 2000000000
            result = await self.api.messages.remove_chat_user(chat_id=chat_id, user_id=user_id)
        except BaseException as error:
            logger.error(f"Пользователь с id: {user_id} не исключен из беседы. Причина: {error}.")
            return False
        if result == 1:
            self._conversation_users.remove(user_id)
            logger.debug(f"Пользователь с id: {user_id} исключен из беседы id: {self._conversation_id_old}")
            return True

    async def process_message(self, event: RawUserEvent):
        chat_id = event.object[3]
        if chat_id != self._conversation_id_old:
            return
        user_id = int(event.object[7].get("from", 0))
        if user_id in self._conversation_admins:
            return
        message_id = event.object[1]
        await self.delete_message(message_id=message_id, chat_id=chat_id)

    async def delete_message(self, message_id, chat_id: int) -> bool:
        request_data = dict(message_id=message_id, peer_id=chat_id, delete_for_all=1)
        try:
            response = await self.user.api.request("messages.delete", request_data)
            result = response.get("response", None)
        except BaseException as error:
            logger.error(f"Сообщение с id: {message_id} не может быть удаленно из старой беседы. Причина: {error}.")
            return False
        if result == 1:
            logger.debug(f"Собщение с id: {message_id}, было удаленно из старой беседы.")
            return True

    async def _load_conversation(self) -> None:
        response_conversation, response_members = await gather(
            self.user.api.messages.get_conversations_by_id(peer_ids=[self._conversation_id_old]),
            self.user.api.messages.get_conversation_members(peer_id=self._conversation_id_old)
        )
        conversation = response_conversation.items[0]
        for member in response_members.items:
            if member.is_admin and member.member_id >= 0:
                self._conversation_admins.add(member.member_id)
            self._conversation_users.add(member.member_id)
        logger.debug("Данные старой беседы \"{}\" ({}) загружены. Количество админов: {}, участников: {}.".format(
            conversation.chat_settings.title,
            self._conversation_id_old,
            len(self._conversation_admins),
            len(self._conversation_users)
        ))

    async def start(self) -> None:
        logger.info("Запуск менеджера старой беседы.")
        await self._load_conversation()
        logger.debug("Запус прослушивания событий.")
        await self.user.run_polling()
