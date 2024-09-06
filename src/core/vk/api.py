from asyncio import sleep
from collections.abc import Iterable
from configparser import ConfigParser
from typing import Dict, Set, Tuple, List

from core.vk.base.bot import BotUserLongPool
from core.vk.utils import get_random_id
from core.vk.dialogs_conversation import Dialogs as dialog
from logging import Logger


class ConversationAPI:
    _cache_full_names: Dict[int, str] = {}
    _notification_join_offset = 20
    _notification_join_target_offset: int = 0
    group_id: int = 0

    conversation_admins: Set[int] = set()
    conversation_users: Set[int] = set()
    conversation_bots: Set[int] = set()

    _logger: Logger
    _bot: BotUserLongPool

    def __init__(self, configs: ConfigParser, bot: BotUserLongPool, logger: Logger):
        self._logger = logger
        self._bot = bot
        self.conversation_id = configs.getint("Conversation", "conversation_id")
        self._notification_join_offset = configs.getint("Conversation", "notification_join_offset")


    async def get_full_name_for_user(self, user_id: int) -> str | None:
        if user_id < 0:
            return self._logger.debug("Попытка получения полного имени для группы невозможно!")
        if user_id in self._cache_full_names:
            return self._cache_full_names.get(user_id)
        user = (await self._bot.api.users.get([user_id]))[0]
        full_name = f"{user.first_name} {user.last_name}"
        self._logger.debug(f"Полное имя для пользователя с id: {user_id} загружено и помещено в cache.")
        self._cache_full_names.update({user_id: full_name})
        return full_name

    async def send_message_to_conversation(self, text: str) -> int:
        data = dict(peer_id=self.conversation_id, message=text, random_id=get_random_id())
        self._logger.debug(f"Отправка сообщения в беседу. Сообщение: {text}")
        return await self._bot.api.messages.send(**data)

    async def send_reply_message(self, text: str, peer_id: int, reply_message_id: int) -> int:
        data = dict(peer_id=peer_id, message=text, reply_to=reply_message_id, random_id=get_random_id())
        self._logger.debug(f"Отправка ответа на сообщение id: {reply_message_id} в чате {peer_id}. Сообщение: {text}")
        return await self._bot.api.messages.send(**data)

    async def send_reply_message_conversation(self, text: str, reply_message_id: int) -> int:
        return await self.send_reply_message(text, self.conversation_id, reply_message_id)

    async def send_private_message(self, text: str, peer_id):
        data = dict(peer_id=peer_id, message=text, random_id=get_random_id())
        self._logger.debug(f"Отправка сообщения пользователю с id {peer_id}. Сообщение: {text}")
        return await self._bot.api.messages.send(**data)

    async def delete_message(self, message_id):
        # Добавить возможность удаления сообщения администраторов!
        request_data = dict(message_ids=message_id, delete_for_all=1)
        try:
            await self._bot.api.request("messages.delete", request_data)
            self._logger.debug(f"Сообщение с номером id: {message_id}, было успешно удаленно.")
            if self._notification_join_target_offset > 0:
                self._notification_join_target_offset -= 1
        except BaseException as error:
            return self._logger.error(f"Сообщение с id: {message_id} не может быть удаленно. Причина: {error}.")

    async def kick_user_conversation(self, user_id: int) -> bool:
        if self.is_admin(user_id):
            self._logger.warning(f"Пользователь с id: {user_id} не может быть исключен из беседы, так как он админ!")
            return False
        chat_id = self.conversation_id - 2000000000
        result = await self._bot.api.messages.remove_chat_user(member_id=user_id, chat_id=chat_id)
        if result == 1:
            self._logger.debug(f"Пользователь с id: {user_id} исключен. Результат: {result}")
            return True

    async def send_join_user_conversation_notification(self, user_id: int) -> None:
        full_name = await self.get_full_name_for_user(user_id)
        text = dialog.transit.join.format(user_id=user_id, full_name=full_name)
        if self._notification_join_target_offset > self._notification_join_offset:
            text += "\n\n" + dialog.transit.extended_join
            self._notification_join_target_offset = 0
        await self.send_message_to_conversation(text)

    async def send_left_user_conversation_notification(self, user_id: int) -> None:
        full_name = await self.get_full_name_for_user(user_id)
        text = dialog.transit.left.format(user_id=user_id, full_name=full_name)
        await self.send_message_to_conversation(text)

    async def read_all_messages_from_conversation(self):
        await self._bot.api.messages.mark_as_read(peer_id=self.conversation_id, mark_conversation_as_read=True)

    def increment_messages_counter(self):
        self._notification_join_target_offset += 1

    async def load_conversation(self) -> None:
        response = await self._bot.api.messages.get_conversation_members(
            peer_id=self.conversation_id, group_id=self.group_id
        )
        bots = set()
        admins = set()
        users = set()
        for member in response.items:
            if member.member_id < 0:
                bots.add(member.member_id)
            elif member.is_admin:
                admins.add(member.member_id)
            else:
                users.add(member.member_id)
        self.conversation_bots = bots
        self.conversation_users = users
        self.conversation_admins = admins

        for profile in response.profiles:
            full_name = f"{profile.first_name} {profile.last_name}"
            self._cache_full_names.update({profile.id: full_name})

    async def load_group(self) -> None:
        response_group = await self._bot.api.groups.get_by_id()
        self.group_id = response_group[0].id

        self._logger.info(f"Данные группы {response_group[0].name} ({response_group[0].id}) успешно загружены.")

        response_conversation = await self._bot.api.messages.get_conversations_by_id(peer_ids=[self.conversation_id])
        await self.load_conversation()
        self._logger.info("Беседа {} ({}) загружена! Количество админов: {}, ботов: {}, участников: {}.".format(
            response_conversation.items[0].chat_settings.title,
            self.conversation_id,
            len(self.conversation_admins),
            len(self.conversation_bots),
            len(self.conversation_users)
        ))

    async def send_message_and_sleep_and_delete(self, message_text: str, sleep_sec: int):
        message_id = await self.send_message_to_conversation(message_text)
        await sleep(sleep_sec)
        await self.delete_message(message_id)

    async def send_reply_message_conversation_and_sleep_and_delete(self, message_text: str, reply_message_id: int, sleep_sec: int):
        message_id = await self.send_reply_message_conversation(message_text, reply_message_id)
        await sleep(sleep_sec)
        await self.delete_message(message_id)

    def is_admin(self, user_id: int):
        return user_id in self.conversation_admins

    def get_user_ids(self) -> List[int]:
        return [*self.conversation_admins, *self.conversation_users]

    async def get_named_link(self, user_id: int) -> str:
        return f"@id{user_id} ({await self.get_full_name_for_user(user_id)})"

    async def send_named_links_from_user_ids(self, peer_id: int, list_ids: Iterable[int]):
        if not list_ids:
            return await self.send_private_message(peer_id=peer_id, text=dialog.commands.not_user_are_request)
        msg = ""
        for user_id in list_ids:
            link = await self.get_named_link(user_id)
            if len(msg) + len(link) < 4000:
                msg += "\n" + link
            else:
                await self.send_private_message(peer_id=peer_id, text=msg)
                msg = ""
        if msg:
            return await self.send_private_message(peer_id=peer_id, text=msg)