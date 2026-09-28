from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from loguru import logger
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

if TYPE_CHECKING:
    from collections.abc import Callable

    from settings import ApplicationSettings


def _to_logging_record(message) -> logging.LogRecord:
    record = message.record
    exception = record["exception"]
    exc_info = None
    if exception is not None:
        exc_info = (exception.type, exception.value, exception.traceback)

    return logging.LogRecord(
        name=record["name"],
        level=record["level"].no,
        pathname=str(record["file"].path),
        lineno=record["line"],
        msg=record["message"],
        args=(),
        exc_info=exc_info,
        func=record["function"],
    )


def setup_telemetry(settings: ApplicationSettings) -> Callable[[], None]:
    if not settings.OTEL_ENABLED:
        return lambda: None

    try:
        provider = LoggerProvider(
            resource=Resource.create({ResourceAttributes.SERVICE_NAME: settings.OTEL_SERVICE_NAME})
        )
        exporter = OTLPLogExporter(
            endpoint=settings.get_otel_logs_endpoint(),
            headers=settings.get_otel_headers(),
        )
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        set_logger_provider(provider)
        handler = LoggingHandler(logger_provider=provider)
        sink_id = logger.add(
            lambda message: handler.emit(_to_logging_record(message)),
            level=settings.OTEL_LOG_LEVEL,
            enqueue=True,
            backtrace=False,
            diagnose=False,
            filter=lambda record: not record["name"].startswith("opentelemetry"),
        )
    except Exception:
        logger.exception("OpenTelemetry initialization failed; continuing without exporter")
        return lambda: None

    logger.info("OpenTelemetry log export enabled | service={}", settings.OTEL_SERVICE_NAME)

    def shutdown() -> None:
        logger.remove(sink_id)
        provider.shutdown()

    return shutdown
