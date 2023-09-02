from json import loads
from typing import Dict


def get_service_account_creds_with_path(path: str) -> Dict[str, str]:
    try:
        with open(path, 'rb') as f:
            creds = loads(f.read())
            return creds
    except FileNotFoundError:
        raise FileNotFoundError(f'Credentials file not found! {path}')
