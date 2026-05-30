from asyncio import sleep
from typing import TYPE_CHECKING

from loguru import logger

from ._dialogs_conversation import Dialogs
from ._utils import get_random_id

if TYPE_CHECKING:
    from settings import ApplicationSettings

    from .base import BotUserLongPool


dialog = Dialogs()


class ConversationAPI:
    def __init__(self, settings: ApplicationSettings, bot: BotUserLongPool):
        self._bot: BotUserLongPool = bot
        self.conversation_id = settings.CONVERSATION_ID
        self._notification_join_offset = settings.NOTIFICATION_JOIN_OFFSET
        self._cache_full_names: dict[int, str] = {}

        self.conversation_admins: set[int] = set()
        self.conversation_users: set[int] = set()
        self.conversation_bots: set[int] = set()

        self._notification_join_offset = 20
        self._notification_join_target_offset: int = 0
        self.group_id: int = 0

    async def get_full_name_for_user(self, user_id: int) -> str | None:
        if user_id < 0:
            logger.debug("Попытка получения полного имени для группы невозможно!")
            return None
        if user_id in self._cache_full_names:
            return self._cache_full_names.get(user_id)
        user = (await self._bot.api.users.get([user_id]))[0]
        full_name = f"{user.first_name} {user.last_name}"
        logger.debug("Полное имя для пользователя с id: {} загружено и помещено в cache.", user_id)
        self._cache_full_names.update({user_id: full_name})
        return full_name

    async def send_message_to_conversation(self, text: str) -> int:
        data = {"peer_id": self.conversation_id, "message": text, "random_id": get_random_id()}
        logger.debug("Отправка сообщения в беседу. Сообщение: {}", text)
        return await self._bot.api.messages.send(**data)

    async def send_reply_message(self, text: str, peer_id: int, reply_message_id: int) -> int:
        data = {
            "peer_id": peer_id,
            "message": text,
            "reply_to": reply_message_id,
            "random_id": get_random_id(),
        }
        logger.debug(
            "Отправка ответа на сообщение id: {} в чате {}. Сообщение: {}",
            reply_message_id,
            peer_id,
            text,
        )
        return await self._bot.api.messages.send(**data)

    async def send_reply_message_conversation(self, text: str, reply_message_id: int) -> int:
        return await self.send_reply_message(text, self.conversation_id, reply_message_id)

    async def send_private_message(self, text: str, peer_id):
        data = {"peer_id": peer_id, "message": text, "random_id": get_random_id()}
        logger.debug("Отправка сообщения пользователю с id {}. Сообщение: {}", peer_id, text)
        return await self._bot.api.messages.send(**data)

    async def delete_message(self, message_id):
        # todo Добавить возможность удаления сообщения администраторов!
        request_data = {"message_ids": message_id, "delete_for_all": 1}
        try:
            await self._bot.api.request("messages.delete", request_data)
            logger.debug("Сообщение с номером id: {}, было успешно удаленно.", message_id)
            if self._notification_join_target_offset > 0:
                self._notification_join_target_offset -= 1
        except BaseException as error:
            logger.error(
                "Сообщение с id: {} не может быть удаленно. Причина: {}.", message_id, error
            )
            return

    async def kick_user_conversation(self, user_id: int) -> bool:
        if self.is_admin(user_id):
            logger.warning(
                "Пользователь с id: {} не может быть исключен из беседы, так как он админ!", user_id
            )
            return False
        chat_id = self.conversation_id - 2000000000
        result = await self._bot.api.messages.remove_chat_user(member_id=user_id, chat_id=chat_id)
        if result == 1:
            logger.debug("Пользователь с id: {} исключен. Результат: {}", user_id, result)
            return True
        return None

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
        await self._bot.api.messages.mark_as_read(
            peer_id=self.conversation_id, mark_conversation_as_read=True
        )

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
        if not response_group.groups or len(response_group.groups) > 1:
            msg = "Ошибка загрузки группы"
            raise ValueError(msg)
        response_group = response_group.groups[0]
        self.group_id = response_group.id
        logger.info(
            "Данные группы {} ({}) успешно загружены.", response_group.name, response_group.id
        )
        response_conversation = await self._bot.api.messages.get_conversations_by_id(
            peer_ids=[self.conversation_id]
        )
        await self.load_conversation()

        chat_title = ""
        settings = response_conversation.items[0].chat_settings
        if settings and settings.title:
            chat_title = settings.title
        logger.info(
            "Беседа {} ({}) загружена! Количество админов: {}, ботов: {}, участников: {}.",
            chat_title,
            self.conversation_id,
            len(self.conversation_admins),
            len(self.conversation_bots),
            len(self.conversation_users),
        )

    async def send_message_and_sleep_and_delete(self, message_text: str, sleep_sec: int):
        message_id = await self.send_message_to_conversation(message_text)
        await sleep(sleep_sec)
        await self.delete_message(message_id)

    async def send_reply_message_conversation_and_sleep_and_delete(
        self, message_text: str, reply_message_id: int, sleep_sec: int
    ):
        message_id = await self.send_reply_message_conversation(message_text, reply_message_id)
        await sleep(sleep_sec)
        await self.delete_message(message_id)

    def is_admin(self, user_id: int):
        return user_id in self.conversation_admins

    def get_user_ids(self) -> list[int]:
        return [*self.conversation_admins, *self.conversation_users]

    async def get_named_link(
        self,
        user_id: int,
    ) -> str:
        return f"@id{user_id} ({await self.get_full_name_for_user(user_id)})"

    async def format_named_links_from_user_ids(self, list_ids: list[int]) -> str:
        msg = ""
        for user_id in list_ids:
            link = await self.get_named_link(user_id)
            msg += "\n" + link
        return msg

    async def send_named_links_from_user_ids(self, peer_id: int, list_ids: list[int]):
        if not list_ids:
            return await self.send_private_message(
                peer_id=peer_id, text=dialog.commands.not_user_are_request
            )
        msg = await self.format_named_links_from_user_ids(list_ids)
        if msg:
            return await self.send_private_message(peer_id=peer_id, text=msg)
        return None
