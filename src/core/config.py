import configparser
import os


DEFAULT_PATH = "../resources/configs.ini"


def get_config(path: str = DEFAULT_PATH) -> configparser.ConfigParser:
    cfg_parser = configparser.ConfigParser()
    cfg_parser.add_section("Tokens")
    cfg_parser.set("Tokens", "group_access_token", "")

    cfg_parser.add_section("Paths")
    cfg_parser.set("Paths", "sheets_service_account_file_path", "../resources/service_account.json")

    cfg_parser.add_section("Sheets")
    cfg_parser.set("Sheets", "spreadsheet_id", "1kw8CkSUDFBwNM59m70oHeteDDUiyYHpwroHstPH7b_c")

    cfg_parser.add_section("Conversation")
    cfg_parser.set("Conversation", "conversation_id", "2000000002")
    cfg_parser.set("Conversation", "notification_join_offset", "20")

    if not os.path.exists(path):
        with open(path, "w") as config_file:
            cfg_parser.write(config_file)

    cfg_parser.read(path)
    return cfg_parser


if __name__ == '__main__':
    if os.path.exists(DEFAULT_PATH):
        os.remove(DEFAULT_PATH)
    parser = get_config()
