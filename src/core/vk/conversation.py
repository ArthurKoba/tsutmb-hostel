from asyncio import AbstractEventLoop, sleep, gather
from typing import Dict, Set

from configparser import ConfigParser

from vkbottle_types.events.enums import UserEventType
from vkbottle_types.events.user_events import RawUserEvent

from core.vk.vkbottle_bot_user_longpool import BotUserLongPool
from core.vk.utils import get_random_id
from core.vk.dialogs_conversation import Dialogs as dialog
from core.loggers import conversation_logger as logger


class GroupConversation:
    notification_join_offset = 10

    def __init__(self, configs: ConfigParser, loop: AbstractEventLoop,
                 loop_checker_sleep_sec=30, notification_join_offset: int | None = None):
        self._loop = loop
        self._is_active_loop_checker = True
        self._loop_checker_sleep_sec = loop_checker_sleep_sec

        self._conversation_id = configs.getint("Conversation", "conversation_id")
        self._conversation_admins: Set[int] = set()
        self._conversation_users: Set[int] = set()
        self._conversation_bots: Set[int] = set()
        self._cache_full_names: Dict[int, str] = {}

        self._global_mute = False
        self._notification_join_offset = notification_join_offset
        self._notification_join_target_offset = notification_join_offset + 1

        self.bot = BotUserLongPool(configs.get("Tokens", "group_access_token"), loop=self._loop)
        self.bot.on.raw_event(UserEventType.CHAT_INFO_EDIT)(self._process_user_transit)
        self.bot.on.raw_event(UserEventType.MESSAGE_NEW)(self._process_message)

    async def get_full_name_for_user(self, user_id: int) -> str:
        if user_id < 0:
            return logger.warning("Попытка получения полного имени для группы невозможно!")
        if user_id in self._cache_full_names:
            return self._cache_full_names.get(user_id)
        user = (await self.bot.api.users.get([user_id]))[0]
        full_name = f"{user.first_name} {user.last_name}"
        logger.debug(f"Полное имя для пользователя с id: {user_id} загружено и помещено в cache.")
        self._cache_full_names.update({user_id: full_name})
        return full_name

    async def send_message(self, text: str) -> int:
        data = dict(peer_id=self._conversation_id, message=text, random_id=get_random_id())
        logger.debug(f"Отправка сообщения в беседу. Сообщение: {text}")
        return await self.bot.api.messages.send(**data)

    async def send_reply_message(self, text: str, peer_id, reply_message_id: int) -> int:
        data = dict(peer_id=peer_id, message=text, reply_to=reply_message_id, random_id=get_random_id())
        logger.debug(f"Отправка ответа на сообщение id: {reply_message_id} в чате {peer_id}. Сообщение: {text}")
        return await self.bot.api.messages.send(**data)

    async def send_left_user_conversation_notification(self, peer_id, user_id: int) -> None:
        full_name = await self.get_full_name_for_user(user_id)
        text = dialog.transit.left.format(user_id=user_id, full_name=full_name)
        await self.send_message(text)

    async def send_join_user_conversation_notification(self, peer_id, user_id: int) -> None:
        full_name = await self.get_full_name_for_user(user_id)
        text = dialog.transit.join.format(user_id=user_id, full_name=full_name)
        if self._notification_join_target_offset > self._notification_join_offset:
            text += "\n\n" + dialog.transit.extended_join
            self._notification_join_target_offset = 0
        await self.send_message(text)

    async def delete_message(self, message_id) -> None:
        # Добавить озможность удаления сообщения админов!
        request_data = dict(message_ids=message_id, delete_for_all=1)
        try:
            await self.bot.api.request("messages.delete", request_data)
            logger.debug(f"Собщение с номером id: {message_id}, было успешно удаленно.")
        except BaseException as error:
            return logger.error(f"Сообщение с id: {message_id} не может быть удаленно. Причина: {error}.")

    async def _process_chat_command(self, command: str, user_id, message_id: int) -> None:
        if user_id not in self._conversation_admins:
            full_name = await self.get_full_name_for_user(user_id=user_id)
            message_text = dialog.permission.command_denied.format(user_id=user_id, full_name=full_name)
            reply_message_id = await self.send_reply_message(
                text=message_text, peer_id=self._conversation_id, reply_message_id=message_id
            )
            await sleep(10)
            await gather(self.delete_message(message_id), self.delete_message(reply_message_id))

        elif command == "/global_mute":
            self._global_mute = not self._global_mute
            state = dialog.commands.lock if self._global_mute else dialog.commands.unlock
            message_text = dialog.commands.global_mute.format(state=state)
            await self.send_message(text=message_text)

        elif command == "/help":
            message_id = await self.send_message(text=dialog.commands.help)
            await sleep(15)
            await self.delete_message(message_id)
        elif command == "/send_join_extended_message":
            await self.send_message(text=dialog.transit.extended_join)
        else:
            message_id = await self.send_message(text=dialog.commands.unknown)
            await sleep(5)
            await self.delete_message(message_id)

    async def _process_message(self, event: RawUserEvent):
        logger.debug(f"New message: {event.object}")
        self._notification_join_target_offset += 1
        user_id = int(event.object[7].get('from', 0))
        peer_id = event.object[3]
        message_text = event.object[6]
        message_id = event.object[1]
        if self._global_mute and user_id not in self._conversation_admins:
            full_name = await self.get_full_name_for_user(user_id)
            logger.debug(f"MUTE | {full_name} ({user_id}) отправил сообщение: {message_text}")
            return await self.delete_message(message_id=message_id)

        if peer_id == self._conversation_id and len(message_text) > 1 and message_text[0] == "/":
            return await self._process_chat_command(command=message_text, user_id=user_id, message_id=message_id)

    async def _process_user_transit(self, event: RawUserEvent) -> None:
        if event.object[1] not in (6, 7):
            return
        user_id = event.object[3]
        peer_id = event.object[2]
        if event.object[1] == 6:
            logger.debug(f"Пользователь с id: {user_id} присоединился к беседе!")
            await self.send_join_user_conversation_notification(user_id=user_id, peer_id=peer_id)
        elif event.object[1] == 7:
            logger.debug(f"Пользователь с id: {user_id} вышел из беседы!")
            await self.send_left_user_conversation_notification(user_id=user_id, peer_id=peer_id)
            await self.kick_user_conversation(user_id=user_id)

    async def kick_user_conversation(self, user_id: int) -> None:
        if user_id in self._conversation_admins:
            logger.debug(f"Пользователь с id: {user_id} не может быть исключен из беседы, так как он админ!")
            return
        chat_id = self._conversation_id - 2000000000
        result = await self.bot.api.messages.remove_chat_user(member_id=user_id, chat_id=chat_id)
        if result == 1:
            logger.debug(f"Пользователь с id: {user_id} исключен. Результат: {result}")

    async def _read_all_messages(self):
        await self.bot.api.messages.mark_as_read(peer_id=self._conversation_id, mark_conversation_as_read=True)

    async def _load_conversation(self) -> None:
        response = await self.bot.api.messages.get_conversation_members(
            peer_id=self._conversation_id, group_id=self._group_id
        )
        for member in response.items:
            if member.member_id < 0:
                self._conversation_bots.add(member.member_id)
            self._conversation_users.add(member.member_id)
            if member.is_admin:
                self._conversation_admins.add(member.member_id)
        for profile in response.profiles:
            full_name = f"{profile.first_name} {profile.last_name}"
            self._cache_full_names.update({profile.id: full_name})

    async def _load_group(self) -> None:
        response_group, response_conversation = await gather(
            self.bot.api.groups.get_by_id(),
            self.bot.api.messages.get_conversations_by_id(peer_ids=[self._conversation_id])
        )
        logger.info(f"Данные группы {response_group[0].name} ({response_group[0].id}) успешно загружены.")
        self._group_id = response_group[0].id
        await self._load_conversation()
        logger.info("Беседа {} ({}) загружена! Количество админов: {}, ботов: {}, участников: {}.".format(
            response_conversation.items[0].chat_settings.title,
            self._conversation_id,
            len(self._conversation_admins),
            len(self._conversation_bots),
            len(self._conversation_users),
        ))

    async def _loop_checker(self) -> None:
        if not self._is_active_loop_checker:
            return
        logger.debug("Запуск цикла обновлений.")
        while self._is_active_loop_checker:
            await sleep(self._loop_checker_sleep_sec)
            await gather(
                self._load_conversation(),
                self._read_all_messages()
            )

    async def start(self) -> None:
        logger.debug("Запуск менеджера беседы.")
        await self._load_group()
        self._loop.create_task(self._loop_checker())
        await self.bot.run_polling()
