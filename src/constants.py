from pathlib import Path

from utils import EnvType

env_type = EnvType.get_current()

BASE_DIR_NAME = "resources"

BASE_PATH = (
    Path(__file__).parent.parent / BASE_DIR_NAME
    if env_type == EnvType.LOCAL
    else Path(f"/app/{BASE_DIR_NAME}")
)

LOGS_DIR = BASE_PATH / "logs"

__all__ = ["BASE_PATH", "LOGS_DIR"]
