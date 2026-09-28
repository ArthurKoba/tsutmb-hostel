"""Centralized Loguru configuration for the application."""

from __future__ import annotations

import logging
import sys

from loguru import logger

from .env_type import EnvType


class _InterceptHandler(logging.Handler):
    """Route stdlib logging records into Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        logger.patch(
            lambda item: item.update(
                name=record.name,
                function=record.funcName,
                line=record.lineno,
            )
        ).opt(exception=record.exc_info).log(level, record.getMessage())


def _setup_stdlib_intercept(noisy_level: str = "WARNING") -> None:
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    for logger_name in ("vkbottle", "vkbottle.api"):
        library_logger = logging.getLogger(logger_name)
        library_logger.handlers = [_InterceptHandler()]
        library_logger.propagate = False

    for noisy in ("asyncio", "urllib3.connectionpool", "opentelemetry"):
        logging.getLogger(noisy).setLevel(noisy_level)


def _build_format(*, colorize: bool, show_ms: bool, timezone: bool) -> str:
    timestamp = "YYYY-MM-DD HH:mm:ss.SSS" if show_ms else "YYYY-MM-DD HH:mm:ss"
    timestamp = timestamp + "ZZ" if timezone else timestamp
    caller = "{name}:{function}:{line}"

    if colorize:
        return (
            f"<green>{{time:{timestamp}}}</green>|"
            "<level>{level: <4}</level>|"
            f"<cyan>{caller}</cyan> "
            "<level>{message}</level>"
        )
    return f"{{time:{timestamp}}}|{{level: <4}}|{caller} {{message}}"


def setup_logging(
    *,
    level: str = "DEBUG",
    console_enabled: bool = True,
    show_ms: bool = False,
    env_type: EnvType | None = None,
) -> None:
    """Configure the operational console sink and intercept stdlib logging."""
    logger.disable("vkbottle")

    env_type = EnvType.get_current() if env_type is None else env_type
    logger.remove()

    if console_enabled:
        console_level = "INFO" if env_type == EnvType.PROD else level
        logger.add(
            sys.stderr,
            format=_build_format(colorize=True, show_ms=show_ms, timezone=True),
            level=console_level,
            colorize=True,
            backtrace=True,
            diagnose=env_type != EnvType.PROD,
        )

    _setup_stdlib_intercept()
    logger.info(
        "Logging initialised | env={} console={}",
        env_type.value,
        console_enabled,
    )
