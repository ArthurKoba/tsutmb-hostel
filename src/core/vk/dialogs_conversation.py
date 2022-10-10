class Permissions:
    command_denied = "Это не твой уровень, дорогой... :D"


class Transits:
    left = "@id{user_id} ({full_name}) покидает беседу!"
    join = "@id{user_id} ({full_name}) присоединяется к беседе!"

    extended_join = """\n\n
    Рекомендуется отключить уведомления в беседе, дабы вас не беспокоили неважные сообщения. 
    
    Важные сообщения будут помечаться администраторами тегом @аll и вы будете получать уведомления.
    """


class Commands:
    global_mute = "Отправка сообщений в беседе {state}!"
    unknown = "Отправлена неизвестная команда!\n\nДля получения списка всех команд напишите /help"
    unlock = "разблокирована"
    lock = "заблокирована"
    help = """
    Команды бота:\n
    /help - получение списка команд
    /global_mute - переключение состояния блокировки сообщений в беседе
    """


class Dialogs:
    permission = Permissions
    transit = Transits
    commands = Commands
