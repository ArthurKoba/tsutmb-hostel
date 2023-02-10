class Permissions:
    command_denied = "Это не твой уровень, дорогой... :D"


class Transits:
    left = "@id{user_id} ({full_name}) покидает беседу!"
    join = "@id{user_id} ({full_name}) присоединяется к беседе!"

    extended_join = "Рекомендуется отключить уведомления в беседе, дабы вас не беспокоили неважные сообщения.\n\n"
    extended_join += "Только важные сообщения будут помечаться администраторами тегом @аll.\n\n"
    extended_join += "Всем, кто недавно заселился необходимо ознакомиться с требованиями к проживающим:\n"
    extended_join += "https://vk.com/@tsutmb_hostel_1b-requirements"


class Commands:
    global_mute = "Отправка сообщений в беседе {state}!"
    unknown = "Отправлена неизвестная команда!\n\nДля получения списка всех команд напишите /help"
    unlock = "разблокирована"
    lock = "заблокирована"
    help = "Команды бота:\n"
    help += "/help - получение списка доступных команд.\n"
    help += "/global_mute - переключение состояния блокировки сообщений в беседе.\n"
    help += "/send_join_extended_message - отправка расширенного сообщения при вступлении в беседу.\n"


class Dialogs:
    permission = Permissions
    transit = Transits
    commands = Commands
