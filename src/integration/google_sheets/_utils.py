from json import loads
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def get_service_account_creds_with_path(path: Path) -> dict[str, str]:
    try:
        with path.open("rb") as f:
            return loads(f.read())
    except FileNotFoundError as e:
        msg = f"Credentials file not found! {path}"
        raise FileNotFoundError(msg) from e
