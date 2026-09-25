"""Centralized Loguru configuration for the application."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from loguru import logger

from .env_type import EnvType

if TYPE_CHECKING:
    from pathlib import Path

    from loguru import Record


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


def _install_caller_patcher(width: int) -> None:
    def _patcher(record: Record) -> None:
        full = f"{record['name']}:{record['function']}:{record['line']}"
        if len(full) > width:
            full = "…" + full[-(width - 1) :]
        record["extra"]["caller"] = full

    logger.configure(patcher=_patcher)


def _build_format(
    *, colorize: bool, show_ms: bool, timezone: bool, caller_width: int | None
) -> str:
    timestamp = "YYYY-MM-DD HH:mm:ss.SSS" if show_ms else "YYYY-MM-DD HH:mm:ss"
    timestamp = timestamp + "ZZ" if timezone else timestamp
    caller = (
        f"{{extra[caller]:<{caller_width}}}"
        if caller_width is not None
        else "{name}:{function}:{line}"
    )

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
    logs_base_path: Path | None = None,
    console_enabled: bool = True,
    log_to_file: bool = False,
    rotation_rule: str = "10 MB",
    retention_days: int = 14,
    serialize: bool = False,
    show_ms: bool = False,
    caller_width: int | None = None,
    env_type: EnvType | None = None,
) -> None:
    """Configure console/file sinks and intercept stdlib logging."""
    logger.disable("vkbottle")

    env_type = EnvType.get_current() if env_type is None else env_type
    retention = f"{retention_days} days"

    logger.remove()
    if caller_width is not None:
        _install_caller_patcher(caller_width)

    console_level = "INFO" if env_type == EnvType.PROD else level
    console_format = _build_format(
        colorize=True, show_ms=show_ms, caller_width=caller_width, timezone=True
    )
    file_format = _build_format(
        colorize=False, show_ms=show_ms, caller_width=caller_width, timezone=True
    )

    if console_enabled:
        logger.add(
            sys.stderr,
            format=console_format,
            level=console_level,
            colorize=True,
            backtrace=True,
            diagnose=env_type != EnvType.PROD,
        )

    if log_to_file:
        if logs_base_path is None:
            msg = "logs_base_path is required when file logging is enabled"
            raise ValueError(msg)
        logs_base_path.mkdir(parents=True, exist_ok=True)
        logger.add(
            logs_base_path / "app.log",
            format=file_format,
            level=level,
            rotation=rotation_rule,
            retention=retention,
            compression="gz",
            encoding="utf-8",
            serialize=serialize,
            backtrace=True,
            diagnose=False,
            enqueue=True,
        )
        logger.add(
            logs_base_path / "errors.log",
            format=file_format,
            level="ERROR",
            rotation=rotation_rule,
            retention=retention,
            compression="gz",
            encoding="utf-8",
            serialize=serialize,
            backtrace=True,
            diagnose=False,
            enqueue=True,
        )

    _setup_stdlib_intercept()
    logger.info(
        "Logging initialised | env={} console={} file={}",
        env_type.value,
        console_enabled,
        log_to_file,
    )
