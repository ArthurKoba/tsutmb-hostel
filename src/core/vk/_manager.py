from asyncio import create_task, sleep
from typing import TYPE_CHECKING

from loguru import logger
from vkbottle_types.events.enums import UserEventType

from ._api import ConversationAPI
from ._dialogs_conversation import Dialogs
from .base import BotUserLongPool

if TYPE_CHECKING:
    from vkbottle.tools.mini_types.user.message import MessageMin
    from vkbottle_types.events.user_events import RawUserEvent

    from core.sheets import GoogleSheetHostel
    from settings import ApplicationSettings


dialog = Dialogs()


class VKManager:
    _api: ConversationAPI

    def __init__(
        self,
        settings: ApplicationSettings,
        hostel_sheets: GoogleSheetHostel,
    ):

        self.conversation_id = settings.CONVERSATION_ID

        self.bot = BotUserLongPool(
            token=settings.GROUP_ACCESS_TOKEN, conversation_id=self.conversation_id
        )
        self._api = ConversationAPI(settings=settings, bot=self.bot)

        self._loop_checker_sleep_sec = 30
        self._global_mute = False
        self._sheets = hostel_sheets

        self.bot.on.raw_event(UserEventType.CHAT_INFO_EDIT)(self._process_user_transit)
        self.bot.on.conversation_message()(self._process_conversation_message)
        self.bot.on.private_message()(self._process_private_command)
        self.kicked_list = set()

    async def _process_conversation_message(self, message: MessageMin):
        author_id = message.from_id
        if message.peer_id != self.conversation_id or (
            author_id < 0 and author_id == -self._api.group_id
        ):
            return None
        fullname = await self._api.get_full_name_for_user(message.from_id)
        logger.debug("New message: {} -> {}", fullname, message.text)
        self._api.increment_messages_counter()
        await self.bot.api.messages.mark_as_read(
            peer_id=self.conversation_id, mark_conversation_as_read=True
        )

        full_name = await self._api.get_full_name_for_user(message.from_id)

        if self._global_mute and not self._api.is_admin(author_id):
            logger.debug("{} ({}) отправил сообщение: {}", full_name, message.from_id, message.text)
            await self._api.delete_message(message_id=message.id)
            return None
        if message.text.startswith("/"):
            return await self._process_conversation_command(author_id, message)
        if ("@all " in message.text or message.text == "@all") and not self._api.is_admin(
            author_id
        ):
            await self._api.send_reply_message_conversation_and_sleep_and_delete(
                dialog.permission.tag_all_denied, message.id, 15
            )
            await self._api.delete_message(message.id)
        return None

    async def _process_conversation_command(self, author_id: int, message: MessageMin):
        cmd = message.text
        if not self._api.is_admin(author_id):
            full_name = await self._api.get_full_name_for_user(user_id=message.from_id)
            message_text = dialog.permission.command_denied.format(
                user_id=message.from_id, full_name=full_name
            )
            await self._api.send_reply_message_conversation_and_sleep_and_delete(
                message_text, message.id, 10
            )
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
            if not message.reply_message:
                return await self._api.send_reply_message_conversation_and_sleep_and_delete(
                    dialog.commands.not_reply_message, message.id, 10
                )
            await self._api.delete_message(message.reply_message.id)
        else:
            await self._api.send_reply_message_conversation_and_sleep_and_delete(
                dialog.commands.unknown, message.id, 5
            )
        return None

    async def _process_user_transit(self, event: RawUserEvent) -> None:
        edit_id = event.object[1]
        user_id = event.object[3]
        peer_id = event.object[2]
        if peer_id != self.conversation_id:
            return
        if edit_id == 6:
            logger.debug("Пользователь с id: {} присоединился к беседе!", user_id)
            await self._api.send_join_user_conversation_notification(user_id=user_id)
        elif edit_id == 7:
            logger.debug("Пользователь с id: {} вышел из беседы!", user_id)
            await self._api.send_left_user_conversation_notification(user_id=user_id)
            if user_id in self.kicked_list:
                self.kicked_list.remove(user_id)
            else:
                await self._api.kick_user_conversation(user_id=user_id)
                self.kicked_list.add(user_id)

    async def _process_private_command(self, message: MessageMin):
        await self.bot.api.messages.mark_as_read(
            peer_id=message.peer_id, mark_conversation_as_read=True
        )
        author_id = message.peer_id
        if not message.text.startswith("/"):
            return await self._api.send_private_message(
                peer_id=message.peer_id, text=dialog.commands.start
            )

        cmd = message.text

        if cmd == "/start":
            return await self._api.send_private_message(
                peer_id=message.peer_id, text=dialog.commands.start
            )
        if not self._api.is_admin(author_id):
            return await self._api.send_private_message(
                peer_id=message.peer_id, text=dialog.permission.private_cmd_denied
            )

        if cmd == "/help":
            await self._api.send_private_message(
                peer_id=message.peer_id, text=dialog.commands.private_help
            )
        elif cmd == "/show_need_kick":
            await self._show_users_which_are_need_kick(message)
        elif cmd == "/show_need_invite":
            await self._show_users_which_are_need_invite(message)
        elif cmd == "/kick_users_from_conversation":
            await self._kick_users_which_are_not_in_db()
        elif cmd == "/update_statuses":
            await self._update_statuses_db_in_conversation(message)

        return None

    async def _send_notes(self, message: MessageMin):
        await self._sheets.update_database()
        msg = ""
        if msg:
            await self._api.send_private_message(peer_id=message.peer_id, text=msg)

    @staticmethod
    def _get_users_which_are_need_kick(db_ids, conversation_ids: list[int]) -> list[int]:
        need_kick = []
        for user_id in conversation_ids:
            if user_id not in db_ids:
                need_kick.append(user_id)
        return need_kick

    async def _get_db_and_conversation_vk_ids(self):
        await self._sheets.update_database()
        db_vk_ids = self._sheets.get_all_vk_ids()
        conversation_ids = self._api.get_user_ids()
        return db_vk_ids, conversation_ids

    async def _show_users_which_are_need_kick(self, message: MessageMin):
        db_ids, conversation_ids = await self._get_db_and_conversation_vk_ids()
        need_kick = self._get_users_which_are_need_kick(db_ids, conversation_ids)
        await self._api.send_named_links_from_user_ids(message.peer_id, need_kick)

    async def _show_users_which_are_need_invite(self, message: MessageMin):
        db_ids, conversation_ids = await self._get_db_and_conversation_vk_ids()
        need_invite = []
        for user_id in db_ids:
            if user_id not in conversation_ids:
                need_invite.append(user_id)
        await self._api.send_named_links_from_user_ids(message.peer_id, need_invite)

    async def _kick_users_which_are_not_in_db(self):
        db_ids, conversation_ids = await self._get_db_and_conversation_vk_ids()
        for user_id in conversation_ids:
            if user_id in db_ids:
                continue
            await self._api.kick_user_conversation(user_id=user_id)

    async def _update_statuses_db_in_conversation(self, message: MessageMin):
        conversation_ids = self._api.get_user_ids()
        result = await self._sheets.update_vk_statuses(conversation_ids)
        await self._api.send_private_message(
            peer_id=message.peer_id,
            text=dialog.commands.count_updated_statuses.format(count=result),
        )

    async def _loop_checker(self) -> None:
        logger.debug("Запуск цикла обновлений.")
        while True:
            await sleep(self._loop_checker_sleep_sec)
            await self._api.load_conversation()

    async def test(self):
        await self._api.load_group()
        await self._api.load_conversation()
        await self._sheets.update_database()
        db_ids = self._sheets.get_all_vk_ids()
        conversation_ids = self._api.get_user_ids()
        users = self._get_users_which_are_need_kick(db_ids, conversation_ids)
        msg = await self._api.format_named_links_from_user_ids(users)
        logger.warning(msg)

    async def run(self) -> None:
        logger.info("Запуск vk менеджера.")
        await self._api.load_group()
        await self._api.read_all_messages_from_conversation()
        checker_task = create_task(self._loop_checker())
        await self.bot.run_polling()
        await checker_task
