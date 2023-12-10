class Permissions:
    command_denied = "Это не твой уровень, дорогой... :D"
    tag_all_denied = "Тег \"all\" доступен только администраторам. Не надо беспокоить людей ненужными уведомлениями."
    private_cmd_denied = "Команда не обнаружена или у вас нет доступа к ней!"


class Transits:
    left = "@id{user_id} ({full_name}) покидает беседу!"
    join = "@id{user_id} ({full_name}) присоединяется к беседе!"

    extended_join = "Рекомендуется отключить уведомления в беседе, дабы вас не беспокоили неважные сообщения.\n\n"
    extended_join += "Только важные сообщения будут помечаться администраторами тегом @аll.\n\n"
    extended_join += "Всем, кто недавно заселился необходимо ознакомиться с требованиями в дорожной карте:\n"
    extended_join += "https://vk.com/@tsutmb_hostel_1b-map-for-new-people\n"


class Commands:
    global_mute = "Отправка сообщений в беседе {state}!"
    unknown = "Отправлена неизвестная команда!\n\nДля получения списка всех команд напишите /help"
    unlock = "разблокирована"
    lock = "заблокирована"
    unknown_del_msg_id = "Ошибка! Команда сработает только если её использовать отвечая на сообщение!"

    count_updated_statuses = "Обновлено {count} статусов пользователей."

    help = "Команды бота:\n"
    help += "/help - получение списка доступных команд.\n"
    help += "/global_mute - переключение состояния блокировки сообщений в беседе.\n"
    help += "/send_join_extended_message - отправка расширенного сообщения при вступлении в беседу.\n"

    start = "Бот находится в рабочем состоянии, но на данный момент у него нет функционала для пользователей. \n\n"
    start += "Если у вас есть какие-либо вопросы, можете написать Артуру, старосте общежития: @arthur_koba"

    private_help = "Команды бота: \n"
    private_help += "/update_statuses - обновить статусы в базе о нахождении пользователей в беседе.\n"
    private_help += "/show_notes - показать заметки по базе.\n"
    private_help += "/show_need_kick - показать пользователей которых нужно исключить.\n"
    private_help += "/show_need_invite - показать пользователей которых нужно пригласить.\n"
    private_help += "/kick_users_from_conversation - исключить пользователей из беседы, которых нет в базе.\n"


class Dialogs:
    permission = Permissions
    transit = Transits
    commands = Commands
