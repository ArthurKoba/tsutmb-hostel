"""
logger.py — centralized loguru setup for Telegram bot / app.

Designed to be imported once at entry point (bot.py / main.py),
then re-used everywhere via `from loguru import logger`.

Extend by adding sinks: Sentry, Loki, Telegram alert channel, etc.
"""

import logging
import sys
from typing import TYPE_CHECKING, ClassVar

from loguru import logger

from .env_type import EnvType

if TYPE_CHECKING:
    from pathlib import Path

    from loguru import Record


class _InterceptHandler(logging.Handler):
    """
    Route stdlib logging records into loguru.
    Libraries (aiogram, httpx, sqlalchemy, …) use stdlib logging.
    This shim forwards everything into loguru so you have ONE log stream.
    """

    _level_map: ClassVar[dict[int, str]] = {}  # cache: stdlib level int → loguru name

    def __init__(self) -> None:
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        # Resolve loguru level name (maybe custom int)
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        # Patch the record to inject stdlib logging info into loguru's context
        # This preserves the original logger name, function, and line number
        logger.patch(
            lambda r: r.update(
                name=record.name,
                function=record.funcName,
                line=record.lineno,
            )
        ).opt(exception=record.exc_info).log(level, record.getMessage())


def _setup_stdlib_intercept(noisy_level: str = "WARNING") -> None:
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # Configure aiogram loggers to use our handler
    for logger_name in ("aiogram", "aiogram.event", "aiogram.dispatcher", "vkbottle.api"):
        aiogram_logger = logging.getLogger(logger_name)
        aiogram_logger.handlers = [_InterceptHandler()]
        aiogram_logger.propagate = False

    # Silence noisy stdlib loggers you don't care about - uncomment if you need
    for noisy in ("asyncio", "urllib3.connectionpool"):
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
    ts = "YYYY-MM-DD HH:mm:ss.SSS" if show_ms else "YYYY-MM-DD HH:mm:ss"
    ts = ts + "ZZ" if timezone else ts

    if caller_width is not None:
        caller = f"{{extra[caller]:<{caller_width}}}"
    else:
        caller = "{name}:{function}:{line}"

    if colorize:
        return (
            f"<green>{{time:{ts}}}</green>|"
            "<level>{level: <4}</level>|"
            f"<cyan>{caller}</cyan> "
            "<level>{message}</level>"
        )
    return f"{{time:{ts}}}|{{level: <4}}|{caller} {{message}}"


def setup_logging(
    *,
    level: str = "DEBUG",
    logs_base_path: Path | None = None,
    log_to_file: bool | None = None,
    rotation_rule: str = "10 MB",
    retention_days: int = 14,
    serialize: bool = False,  # True → JSON lines (for log aggregators)
    show_ms=False,  # 2026-05-08 05:35:39 | INFO     | …
    caller_width: int | None = None,
    env_type: EnvType | None = None,  # "production" suppresses DEBUG on console
) -> None:
    """
    Call once at application startup.

    Args:
        level:              Minimum log level captured globally.
        logs_base_path:     Path for base logs directory
        log_to_file:        Whether to persist logs to logs/ directory.
        rotation_rule:      loguru rotation rule ("10 MB", "1 day", "00:00", …).
        retention_days:     How long to keep rotated files.
        serialize:          Emit JSON lines instead of plain text (for Loki / ELK).
        show_ms:            Show milliseconds in the timestamp (default True).
        caller_width:       Fixed character width of the caller column.
                            Values longer than this are truncated from the left
                            with a leading "…" so the column stays aligned.
                            Recommended range: 20-40.
        env_type:                BuildType.PROD" → console shows INFO+; files keep full DEBUG.
    """

    logger.disable("vkbottle")

    env_type = EnvType.get_current() if env_type is None else env_type
    default_log_level = env_type != EnvType.LOCAL
    log_to_file = default_log_level if log_to_file is None else log_to_file
    retention = f"{retention_days} days"

    logger.remove()  # drop default stderr sink added at import time
    if caller_width is not None:
        _install_caller_patcher(caller_width)

    console_level = "INFO" if env_type == EnvType.PROD else level

    console_fmt = _build_format(
        colorize=True, show_ms=show_ms, caller_width=caller_width, timezone=True
    )
    file_fmt = _build_format(
        colorize=False, show_ms=show_ms, caller_width=caller_width, timezone=True
    )

    logger.add(
        sys.stderr,
        format=console_fmt,
        level=console_level,
        colorize=True,
        backtrace=True,  # extended traceback with variable values
        diagnose=env_type != EnvType.PROD,  # hide locals in prod (security)
    )

    if log_to_file:
        if not logs_base_path:
            msg = "Failed get logs_base_path"
            raise ValueError(msg)

        # Создаём папку для логов только если логирование в файлы включено
        logs_base_path.mkdir(exist_ok=True)

        # ── General log (all levels) ──────────────────────────────────────────
        logger.add(
            logs_base_path / "app.log",
            format=file_fmt,
            level=level,
            rotation=rotation_rule,
            retention=retention,
            compression="gz",
            encoding="utf-8",
            serialize=serialize,
            backtrace=True,
            diagnose=False,  # never write locals to file (leaks data)
            enqueue=True,  # async-safe: writes happen in a background thread
        )

        # ── Errors-only sink (fast triage in production) ──────────────────────
        logger.add(
            logs_base_path / "errors.log",
            format=file_fmt,
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

    _setup_stdlib_intercept(noisy_level="WARNING")

    logger.info(
        "Logging initialised | env={} console_level={} file={}",
        env_type.value,
        console_level,
        log_to_file,
    )
