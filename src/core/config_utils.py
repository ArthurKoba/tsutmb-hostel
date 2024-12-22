import os
from core.loggers import config_logger as logger
from configparser import ConfigParser, DuplicateOptionError
from typing import Dict
from core.config import DEFAULT_OUTDATED_OPTIONS_SECTION


def get_default_parser() -> ConfigParser:
    config_parser = ConfigParser()

    config_parser.add_section("Tokens")
    config_parser.set("Tokens", "group_access_token", "...")

    config_parser.add_section("Paths")

    config_parser.add_section("Sheets")
    config_parser.set("Sheets", "sheets_service_account_file_path", "service_account.json")
    config_parser.set("Sheets", "spreadsheet_id", "1kw8CkSUDFBwNM59m70oHeteDDUiyYHpwroHstPH7b_c")
    config_parser.set("Sheets", "database_sheet_name", "Лист1")
    config_parser.set("Sheets", "database_sheet_start_range", "1")
    config_parser.set("Sheets", "database_sheet_end_range", "10")

    config_parser.add_section("Conversation")
    config_parser.set("Conversation", "conversation_id", "2000000000")
    config_parser.set("Conversation", "notification_join_offset", "20")

    return config_parser


def compare_and_combine_configs(
        default_parser: ConfigParser,
        target_parser: ConfigParser,
        outdated_section: str) -> bool:

    default_map: Dict[str, str] = {}
    target_map: Dict[str, str] = {}

    is_not_identical_configuration_structure = False
    is_created_outdated_options_section = outdated_section in target_parser.sections()

    for section in default_parser.sections():
        if section not in target_parser.sections() and default_parser.options(section):
            target_parser.add_section(section)
            logger.debug(f"Создана секция \"{section}\".")
            is_not_identical_configuration_structure = True
        for option in default_parser.options(section):
            if option in default_map.keys():
                raise DuplicateOptionError("ALL CONFIG FILE", option)
            default_map.update({option: section})

    for section in target_parser.sections():
        for option in target_parser.options(section):
            if option in target_map.keys():
                raise DuplicateOptionError("ALL CONFIG FILE", option)
            target_map.update({option: section})
        if not target_parser.options(section) and section not in default_parser.sections():
            is_not_identical_configuration_structure = True
            target_parser.remove_section(section)
            logger.debug(f"Удалена пустая устаревшая секция \"{section}\".")

    for option in target_map.keys():
        if option not in default_map.keys():
            if not is_created_outdated_options_section:
                target_parser.add_section(outdated_section)
                is_created_outdated_options_section = True
                logger.debug(f"Создана секция-архив: \"{outdated_section}\".")
            target_parser.set(outdated_section, option, target_parser.get(target_map[option], option))
            if target_map[option] != outdated_section:
                logger.debug(f"Опция \"{option}\" помещена в секцию-архив.")
                target_parser.remove_option(target_map[option], option)
        elif target_map[option] != default_map[option]:
            target_parser.set(default_map[option], option, target_parser.get(target_map[option], option))
            target_parser.remove_option(target_map[option], option)
            is_not_identical_configuration_structure = True
            logger.debug(f"Опция \"{option}\" перемещена из секции {target_map[option]} в секцию {default_map[option]}.")

    for option in default_map.keys():
        if option not in target_map.keys():
            is_not_identical_configuration_structure = True
            target_parser.set(default_map[option], option, default_parser.get(default_map[option], option))
            logger.debug(f"Добавлена отсутствующая опция \"{option}\" со стандартным значением.")

    for section in target_parser.sections():
        if not target_parser.options(section):
            is_not_identical_configuration_structure = True
            target_parser.remove_section(section)
            logger.debug(f"Удалена пустая секция \"{section}\".")

    if is_not_identical_configuration_structure:
        logger.warning(f"Была произведена адаптация конфигурационного файла. ")
    else:
        logger.debug(f"Структура конфигурационных файлов идентична.")
    return is_not_identical_configuration_structure


def get_config(
        directory_path: str,
        config_filename: str
        ) -> ConfigParser:

    default_config_parser = get_default_parser()
    full_path = os.path.join(directory_path, config_filename)
    config_file_exist = os.path.exists(full_path)

    if config_file_exist:
        logger.debug(f"Обнаружен файл конфигурации: \"{full_path}\". Чтение и проверка структуры...")
        target_config_parser = ConfigParser()
        target_config_parser.read(full_path, encoding="utf-8")
        if compare_and_combine_configs(default_config_parser, target_config_parser, DEFAULT_OUTDATED_OPTIONS_SECTION):
            with open(full_path, "w") as config_file:
                target_config_parser.write(config_file)
    else:
        with open(full_path, "w") as config_file:
            default_config_parser.write(config_file)
        logger.warning(f"Файл конфигурации был автоматически создан, так как не был обнаружен.")
        target_config_parser = default_config_parser

    return target_config_parser
