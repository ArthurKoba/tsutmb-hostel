import logging
import sys
from enum import Enum
from os import getenv

logger = logging.getLogger(__name__)


class EnvType(Enum):
    LOCAL = "LOCAL"
    DEV = "DEVELOPMENT"
    PROD = "PRODUCTION"
    __default = LOCAL

    @classmethod
    def get_current(cls) -> EnvType:
        build_type = getenv("ENV_TYPE")
        if build_type is None:
            build_type = EnvType.__default
            logger.warning("Env variable ENV_TYPE not set. Used default: '%s'", build_type)
        build_type = str(build_type).upper()
        try:
            return cls(build_type)
        except ValueError:
            allowed = ", ".join([bt.value for bt in cls])
            logger.exception("Invalid ENV_TYPE: '%s'. Allowed values: %s", build_type, allowed)
            sys.exit(1)

    def __str__(self) -> str:
        return self.value.upper()
