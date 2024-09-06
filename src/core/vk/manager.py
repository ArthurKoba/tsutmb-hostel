from asyncio import AbstractEventLoop, sleep, gather
from typing import Dict, List, Optional
from functools import wraps

from vkbottle_types.events.enums import UserEventType
from vkbottle_types.events.user_events import RawUserEvent
from vkbottle.tools.dev.mini_types.user.message import MessageMin

from configparser import ConfigParser

from core.sheets import GoogleSheetHostel

from core.vk.utils import get_vk_ids_from_list_links
from .api import ConversationAPI

from core.vk.dialogs_conversation import Dialogs as dialog
from core.loggers import conversation_logger as logger
from core.vk.base.bot import BotUserLongPool


def with_update_db(method):
    @wraps(method)
    async def wrapper(self, message: MessageMin):
        await self._sheets.update_database()
        return await method(message)

    return wrapper


def mix_db_ids_and_conversation_ids(method):
    @wraps(method)
    async def wrapped(self, message: MessageMin):
        db_ids = get_vk_ids_from_list_links(self._sheets.get_all_vk_links())
        conversation_ids = self._api.get_user_ids()
        return await method(message, db_ids, conversation_ids)

    return wrapped

class VKManager:
    _api: ConversationAPI
    _loop: AbstractEventLoop

    def __init__(self, configs: ConfigParser, loop: AbstractEventLoop, hostel_sheets: GoogleSheetHostel):
        self._loop = loop

        self.conversation_id = configs.getint("Conversation", "conversation_id")

        self.bot = BotUserLongPool(
            token=configs.get("Tokens", "group_access_token"),
            loop=loop,
            conversation_id=self.conversation_id
        )
        self._api = ConversationAPI(configs=configs, bot=self.bot, logger=logger)

        self._loop_checker_sleep_sec = 30
        self._global_mute = False
        self._sheets = hostel_sheets

        self.bot.on.raw_event(UserEventType.CHAT_INFO_EDIT)(self._process_user_transit)
        self.bot.on.conversation_message()(self._process_conversation_message)
        self.bot.on.private_message()(self._process_private_command)
    #     self.bot.on.private_message(FromPeerRule([198534303]))(self.test)
        self.kicked_list = set()


    async def _process_conversation_message(self, message: MessageMin):
        author_id = message.from_id
        if message.peer_id != self.conversation_id or (author_id < 0 and author_id == -self._api.group_id):
            return
        logger.debug(f"New message: {message.text}")
        self._api.increment_messages_counter()
        await self.bot.api.messages.mark_as_read(peer_id=self.conversation_id, mark_conversation_as_read=True)

        full_name = await self._api.get_full_name_for_user(message.from_id)

        if (self._global_mute or self._sheets.is_muted(author_id)) and not self._api.is_admin(author_id):
            logger.debug(f"{full_name} ({message.from_id}) отправил сообщение: {message.text}")
            return await self._api.delete_message(message_id=message.id)
        if message.text.startswith("/"):
            return await self._process_conversation_command(author_id, message)
        if ("@all " in message.text or message.text == "@all") and not self._api.is_admin(author_id):
            await self._api.send_reply_message_conversation_and_sleep_and_delete(
                dialog.permission.tag_all_denied, message.id, 15
            )
            await self._api.delete_message(message.id)


    async def _process_conversation_command(self, author_id: int, message: MessageMin):
        cmd = message.text
        if not self._api.is_admin(author_id):
            full_name = await self._api.get_full_name_for_user(user_id=message.from_id)
            message_text = dialog.permission.command_denied.format(user_id=message.from_id, full_name=full_name)
            await self._api.send_reply_message_conversation_and_sleep_and_delete(message_text, message.id, 10)
            await self._api.delete_message(message.id)
        elif cmd == "/help":
            await self._api.send_message_and_sleep_and_delete(dialog.commands.help, 10)
        elif cmd == "/global_mute":
            self._global_mute = not self._global_mute
            state = dialog.commands.lock if self._global_mute else dialog.commands.unlock
            message_text = dialog.commands.global_mute.format(state=state)
            await self._api.send_message_to_conversation(text=message_text)
        elif cmd == "/send_join_extended_message":
            await self._api.send_message_to_conversation(text=dialog.transit.extended_join)
        elif cmd == "/del":
            if message.reply_message:
                await self._api.delete_message(message.reply_message.id)
            else:
                await self._api.send_message_and_sleep_and_delete(dialog.commands.unknown_del_msg_id, 10)
        elif cmd == "/unmute":
            user_id = message.reply_message.from_id
            result = await self._sheets.remove_mute(user_id)
            await self._api.send_reply_message_conversation_and_sleep_and_delete(
                dialog.commands.delete_mute_success if result else dialog.commands.delete_mute_fail, message.id, 10
            )
        elif cmd.startswith("/mute"):
            pass
        else:
            await self._api.send_reply_message_conversation_and_sleep_and_delete(
                dialog.commands.unknown, message.id, 5
            )

    async def _process_user_transit(self, event: RawUserEvent) -> None:
        edit_id = event.object[1]
        user_id = event.object[3]
        peer_id = event.object[2]
        if peer_id != self.conversation_id:
            return
        if edit_id == 6:
            logger.debug(f"Пользователь с id: {user_id} присоединился к беседе!")
            await self._api.send_join_user_conversation_notification(user_id=user_id)
        elif edit_id == 7:
            logger.debug(f"Пользователь с id: {user_id} вышел из беседы!")
            await self._api.send_left_user_conversation_notification(user_id=user_id)
            if user_id in self.kicked_list:
                self.kicked_list.remove(user_id)
            else:
                await self._api.kick_user_conversation(user_id=user_id)
                self.kicked_list.add(user_id)

    async def _process_private_command(self, message: MessageMin):
        await self.bot.api.messages.mark_as_read(peer_id=message.peer_id, mark_conversation_as_read=True)
        author_id = message.peer_id
        if not message.text.startswith("/"):
            return await self._api.send_private_message(peer_id=message.peer_id, text=dialog.commands.start)

        cmd = message.text

        if cmd == "/start":
            return await self._api.send_private_message(peer_id=message.peer_id, text=dialog.commands.start)
        elif not self._api.is_admin(author_id):
            return await self._api.send_private_message(peer_id=message.peer_id, text=dialog.permission.private_cmd_denied)

        if cmd == "/help":
            return await self._api.send_private_message(peer_id=message.peer_id, text=dialog.commands.private_help)
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
                await self._api.send_private_message(peer_id=message.peer_id, text=msg)
                msg = ""
        if msg:
            await self._api.send_private_message(peer_id=message.peer_id, text=msg)



    @with_update_db
    @mix_db_ids_and_conversation_ids
    async def _show_users_which_are_need_kick(self, message: MessageMin, db_ids, conversation_ids):
        need_kick = []
        for user_id in conversation_ids:
            if user_id not in db_ids:
                need_kick.append(user_id)
        await self._api.send_named_links_from_user_ids(message.peer_id, need_kick)

    @with_update_db
    @mix_db_ids_and_conversation_ids
    async def _show_users_which_are_need_invite(self, message: MessageMin, db_ids, conversation_ids):
        need_invite = []
        for user_id in db_ids:
            if user_id not in conversation_ids:
                need_invite.append(user_id)
        await self._api.send_named_links_from_user_ids(message.peer_id, need_invite)

    @with_update_db
    @mix_db_ids_and_conversation_ids
    async def _kick_users_which_are_not_in_db(self, message: MessageMin, db_ids, conversation_ids):
        for user_id in conversation_ids:
            if user_id in db_ids:
                continue
            await self._api.kick_user_conversation(user_id=user_id)

    @with_update_db
    async def _update_statuses_db_in_conversation(self, message: MessageMin, db_ids, conversation_ids):
        result = await self._sheets.update_statuses(conversation_ids)
        await self._api.send_private_message(
            peer_id=message.peer_id, text=dialog.commands.count_updated_statuses.format(count=result)
        )

    async def _loop_checker(self) -> None:
        logger.debug("Запуск цикла обновлений.")
        while True:
            await sleep(self._loop_checker_sleep_sec)
            await self._api.load_conversation()

    async def start(self) -> None:
        logger.debug("Запуск vk менеджера.")
        await self._api.load_group()
        await self._api.read_all_messages_from_conversation()
        self._loop.create_task(self._loop_checker())
        await self.bot.run_polling()