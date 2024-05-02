from asyncio import AbstractEventLoop, sleep, gather
from typing import Dict, List, Optional

from vkbottle_types.events.enums import UserEventType
from vkbottle_types.events.user_events import RawUserEvent
from vkbottle.tools.dev.mini_types.user.message import MessageMin

from configparser import ConfigParser

from core.sheets import GoogleSheetHostel
from core.vk.base.bot import BotUserLongPool
from core.vk.utils import get_random_id, get_vk_ids_from_list_links
from core.vk.dialogs_conversation import Dialogs as dialog
from core.loggers import conversation_logger as logger


class DefaultVKManager:
    def __init__(
            self, access_token: str,
            conversation_id: int,
            admins_conversation_id: int,
            loop: AbstractEventLoop,
            notification_join_offset: int = None,
            loop_checker_sleep_sec: int = None,
    ):
        self._loop = loop
        self._loop_checker_sleep_sec = loop_checker_sleep_sec or 30
        self.bot = BotUserLongPool(access_token, loop=loop, conversation_id=conversation_id)

        self._group_id: Optional[int] = None
        self.conversation_id = conversation_id
        self.admins_conversation_id = admins_conversation_id

        self._conversation_admins: List[int] = []
        self._conversation_users: List[int] = []
        self._conversation_bots: List[int] = []

        self._notification_join_offset = notification_join_offset or 20
        self._notification_join_target_offset = notification_join_offset + 1

        self._cache_full_names: Dict[int, str] = {}

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

    async def send_message_to_conversation(self, text: str) -> int:
        data = dict(peer_id=self.conversation_id, message=text, random_id=get_random_id())
        logger.debug(f"Отправка сообщения в беседу. Сообщение: {text}")
        return await self.bot.api.messages.send(**data)

    async def send_reply_message(self, text: str, peer_id, reply_message_id: int) -> int:
        data = dict(peer_id=peer_id, message=text, reply_to=reply_message_id, random_id=get_random_id())
        logger.debug(f"Отправка ответа на сообщение id: {reply_message_id} в чате {peer_id}. Сообщение: {text}")
        return await self.bot.api.messages.send(**data)

    async def send_private_message(self, text: str, peer_id):
        data = dict(peer_id=peer_id, message=text, random_id=get_random_id())
        logger.debug(f"Отправка сообщения пользователю с id {peer_id}. Сообщение: {text}")
        return await self.bot.api.messages.send(**data)

    async def delete_message(self, message_id) -> bool:
        # Добавить возможность удаления сообщения администраторов!
        request_data = dict(message_ids=message_id, delete_for_all=1)
        try:
            await self.bot.api.request("messages.delete", request_data)
            logger.debug(f"Сообщение с номером id: {message_id}, было успешно удаленно.")
            if self._notification_join_target_offset > 0:
                self._notification_join_target_offset -= 1
        except BaseException as error:
            return logger.error(f"Сообщение с id: {message_id} не может быть удаленно. Причина: {error}.")

    async def kick_user_conversation(self, user_id: int) -> bool:
        if user_id in self._conversation_admins:
            logger.debug(f"Пользователь с id: {user_id} не может быть исключен из беседы, так как он админ!")
            return False
        chat_id = self.conversation_id - 2000000000
        result = await self.bot.api.messages.remove_chat_user(member_id=user_id, chat_id=chat_id)
        if result == 1:
            logger.debug(f"Пользователь с id: {user_id} исключен. Результат: {result}")
            return True

    async def read_all_messages_from_conversation(self):
        await self.bot.api.messages.mark_as_read(peer_id=self.conversation_id, mark_conversation_as_read=True)
        await self.bot.api.messages.mark_as_read(peer_id=self.admins_conversation_id, mark_conversation_as_read=True)

    async def send_left_user_conversation_notification(self, user_id: int) -> None:
        full_name = await self.get_full_name_for_user(user_id)
        text = dialog.transit.left.format(user_id=user_id, full_name=full_name)
        await self.send_message_to_conversation(text)

    async def send_join_user_conversation_notification(self, user_id: int) -> None:
        full_name = await self.get_full_name_for_user(user_id)
        text = dialog.transit.join.format(user_id=user_id, full_name=full_name)
        if self._notification_join_target_offset > self._notification_join_offset:
            text += "\n\n" + dialog.transit.extended_join
            self._notification_join_target_offset = 0
        await self.send_message_to_conversation(text)

    async def _load_conversation(self) -> None:
        if not self._group_id:
            return logger.warning("Группа не была загружена предварительно!")
        response = await self.bot.api.messages.get_conversation_members(
            peer_id=self.conversation_id, group_id=self._group_id
        )
        bots = []
        admins = []
        users = []
        for member in response.items:
            if member.member_id < 0:
                bots.append(member.member_id)
            elif member.is_admin:
                admins.append(member.member_id)
            else:
                users.append(member.member_id)
        self._conversation_bots = bots
        self._conversation_users = users
        self._conversation_admins = admins

        for profile in response.profiles:
            full_name = f"{profile.first_name} {profile.last_name}"
            self._cache_full_names.update({profile.id: full_name})

    async def _load_group(self) -> None:
        response_group, response_conversation = await gather(
            self.bot.api.groups.get_by_id(),
            self.bot.api.messages.get_conversations_by_id(peer_ids=[self.conversation_id])
        )
        logger.info(f"Данные группы {response_group[0].name} ({response_group[0].id}) успешно загружены.")
        self._group_id = response_group[0].id
        await self._load_conversation()
        logger.info("Беседа {} ({}) загружена! Количество админов: {}, ботов: {}, участников: {}.".format(
            response_conversation.items[0].chat_settings.title,
            self.conversation_id,
            len(self._conversation_admins),
            len(self._conversation_bots),
            len(self._conversation_users),
        ))

    async def _loop_checker(self) -> None:
        logger.debug("Запуск цикла обновлений.")
        while True:
            await sleep(self._loop_checker_sleep_sec)
            await gather(
                self._load_conversation(),
                self.read_all_messages_from_conversation()
            )

    async def start(self) -> None:
        logger.debug("Запуск vk менеджера.")
        await self._load_group()
        self._loop.create_task(self._loop_checker())
        await self.bot.run_polling()


class VKManager(DefaultVKManager):
    def __init__(self, configs: ConfigParser, loop: AbstractEventLoop, hostel_sheets: GoogleSheetHostel,
                 loop_checker_sleep_sec: int = None, notification_join_offset: int = None):

        super().__init__(
            access_token=configs.get("Tokens", "group_access_token"),
            conversation_id=configs.getint("Conversation", "conversation_id"),
            admins_conversation_id=configs.getint("Conversation", "admins_conversation_id"),
            loop=loop,
            notification_join_offset=notification_join_offset,
            loop_checker_sleep_sec=loop_checker_sleep_sec
        )

        self._global_mute = False
        self._sheets = hostel_sheets

        self.bot.on.raw_event(UserEventType.CHAT_INFO_EDIT)(self._process_user_transit)
        self.bot.on.conversation_message()(self._process_conversation_message)
        self.bot.on.private_message()(self._process_private_command)
    #     self.bot.on.private_message(FromPeerRule([198534303]))(self.test)
        self.kicked_list = set()

    async def _process_conversation_command(self, message: MessageMin):
        if message.peer_id != self.conversation_id:
            return
        cmd = message.text
        if message.from_id not in self._conversation_admins:
            full_name = await self.get_full_name_for_user(user_id=message.from_id)
            message_text = dialog.permission.command_denied.format(user_id=message.from_id, full_name=full_name)
            reply_message_id = await self.send_reply_message(
                text=message_text, peer_id=self.conversation_id, reply_message_id=message.id
            )
            await sleep(10)
            await gather(self.delete_message(message.id), self.delete_message(reply_message_id))
        elif cmd == "/help":
            message_id = await self.send_message_to_conversation(text=dialog.commands.help)
            await sleep(15)
            await self.delete_message(message_id)
        elif cmd == "/global_mute":
            self._global_mute = not self._global_mute
            state = dialog.commands.lock if self._global_mute else dialog.commands.unlock
            message_text = dialog.commands.global_mute.format(state=state)
            await self.send_message_to_conversation(text=message_text)
        elif cmd == "/send_join_extended_message":
            await self.send_message_to_conversation(text=dialog.transit.extended_join)
        elif cmd == "/del":
            if message.reply_message:
                await self.delete_message(message.reply_message.id)
            else:
                message_id = await self.send_message_to_conversation(dialog.commands.unknown_del_msg_id)
                await sleep(10)
                await self.delete_message(message_id)
        else:
            message_id = await self.send_message_to_conversation(text=dialog.commands.unknown)
            await sleep(5)
            return await self.delete_message(message_id)

    async def _process_conversation_message(self, message: MessageMin):
        if message.peer_id != self.conversation_id:
            return
        logger.debug(f"New message: {message.text}")
        self._notification_join_target_offset += 1
        full_name = await self.get_full_name_for_user(message.from_id)
        if self._global_mute and message.from_id not in self._conversation_admins:
            logger.debug(f"MUTE | {full_name} ({message.from_id}) отправил сообщение: {message.text}")
            return await self.delete_message(message_id=message.id)
        if message.from_id in self._sheets.muted:
            logger.debug(f"MUTED {full_name} ({message.from_id}) отправил сообщение: {message.text}")
            return await self.delete_message(message_id=message.id)
        if message.text.startswith("/"):
            return await self._process_conversation_command(message)
        if "@all" in message.text and message.from_id not in self._conversation_admins:
            message_id = await self.send_reply_message(
                text=dialog.permission.tag_all_denied, peer_id=self.conversation_id, reply_message_id=message.id
            )
            await sleep(10)
            await self.delete_message(message_id)

    async def _process_user_transit(self, event: RawUserEvent) -> None:
        edit_id = event.object[1]
        user_id = event.object[3]
        peer_id = event.object[2]
        if peer_id != self.conversation_id:
            return
        if edit_id == 6:
            logger.debug(f"Пользователь с id: {user_id} присоединился к беседе!")
            await self.send_join_user_conversation_notification(user_id=user_id)
        elif edit_id == 7:
            logger.debug(f"Пользователь с id: {user_id} вышел из беседы!")
            await self.send_left_user_conversation_notification(user_id=user_id)
            print(self.kicked_list)
            if user_id in self.kicked_list:
                self.kicked_list.remove(user_id)
            elif await self.kick_user_conversation(user_id=user_id):
                self.kicked_list.add(user_id)

    async def _process_private_command(self, message: MessageMin):

        if not message.text.startswith("/"):
            return await self.send_private_message(peer_id=message.peer_id, text=dialog.commands.start)
        cmd = message.text

        if cmd == "/start":
            return await self.send_private_message(peer_id=message.peer_id, text=dialog.commands.start)
        elif message.peer_id not in self._conversation_admins:
            return await self.send_private_message(peer_id=message.peer_id, text=dialog.permission.private_cmd_denied)

        if cmd == "/help":
            return await self.send_private_message(peer_id=message.peer_id, text=dialog.commands.private_help)

        elif cmd == "/show_notes":
            await self._send_notes(message)
        elif cmd == "/show_need_kick":
            await self._show_users_which_are_need_kick(message)
        elif cmd == "/show_need_invite":
            await self._show_users_which_are_need_invite(message)
        elif cmd == "/kick_users_from_conversation":
            await self._kick_users_which_are_not_in_db(message)
        elif cmd == "/update_statuses":
            await self._update_statuses_db_in_conversation(message)

    async def _send_notes(self, message: MessageMin):
        notes = await self._sheets.update_database()
        msg = ""
        for note in notes:
            if len(msg) + len(note) < 4000:
                msg += "\n" + note
            else:
                await self.send_private_message(peer_id=message.peer_id, text=msg)
                msg = ""
        if msg:
            await self.send_private_message(peer_id=message.peer_id, text=msg)

    async def _show_users_which_are_need_kick(self, message: MessageMin):
        await self._sheets.update_database()
        vk_links = self._sheets.get_all_vk_links()
        db_ids = get_vk_ids_from_list_links(vk_links)
        conversation_ids = [*self._conversation_admins, *self._conversation_users]
        need_kick = []
        for user_id in conversation_ids:
            if user_id not in db_ids:
                need_kick.append(user_id)
        msg = ""
        for user_id in need_kick:
            fullname = await self.get_full_name_for_user(user_id)
            named_link = f"@id{user_id} ({fullname})"
            if len(msg) + len(named_link) < 4000:
                msg += "\n" + named_link
            else:
                await self.send_private_message(peer_id=message.peer_id, text=msg)
                msg = ""
        if msg:
            return await self.send_private_message(peer_id=message.peer_id, text=msg)
        await self.send_private_message(peer_id=message.peer_id, text="Нет пользователей которых необходимо исключить.")

    async def _show_users_which_are_need_invite(self, message: MessageMin):
        await self._sheets.update_database()
        vk_links = self._sheets.get_all_vk_links()
        db_ids = get_vk_ids_from_list_links(vk_links)
        conversation_ids = [*self._conversation_admins, *self._conversation_users]
        need_invite = []
        for user_id in db_ids:
            if user_id not in conversation_ids:
                need_invite.append(user_id)
        msg = ""
        for user_id in need_invite:
            fullname = await self.get_full_name_for_user(user_id)
            named_link = f"@id{user_id} ({fullname})"
            if len(msg) + len(named_link) < 4000:
                msg += "\n" + named_link
            else:
                await self.send_private_message(peer_id=message.peer_id, text=msg)
                msg = ""
        if msg:
            await self.send_private_message(peer_id=message.peer_id, text=msg)

    async def _kick_users_which_are_not_in_db(self, message: MessageMin):
        await self._sheets.update_database()
        vk_links = self._sheets.get_all_vk_links()
        db_ids = get_vk_ids_from_list_links(vk_links)
        conversation_ids = [*self._conversation_admins, *self._conversation_users]
        for user_id in conversation_ids:
            if user_id in db_ids:
                continue
            await self.kick_user_conversation(user_id=user_id)

    async def _update_statuses_db_in_conversation(self, message: MessageMin):
        await self._sheets.update_database()
        conversation_ids = [*self._conversation_admins, *self._conversation_users]
        data = []
        for user in self._sheets.users:
            actual_status = user.get_vk_id() in conversation_ids
            if actual_status != user.is_in_conversation:
                data.append((user, actual_status))
        await self._sheets.write_statuses_in_conversation(data)
        await self.send_private_message(
            peer_id=message.peer_id, text=dialog.commands.count_updated_statuses.format(count=len(data))
        )
