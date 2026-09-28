from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

if TYPE_CHECKING:
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


@dataclass(slots=True)
class TelemetryRuntime:
    provider: LoggerProvider | None = None
    sink_id: int | None = None

    def flush(self, timeout_millis: int = 5000) -> bool:
        if self.provider is None:
            return True
        return self.provider.force_flush(timeout_millis=timeout_millis)

    def shutdown(self) -> None:
        if self.sink_id is not None:
            logger.remove(self.sink_id)
        if self.provider is not None:
            if not self.provider.force_flush(timeout_millis=5000):
                logger.error("OpenTelemetry force_flush timed out")
            self.provider.shutdown()


def setup_telemetry(settings: ApplicationSettings) -> TelemetryRuntime:
    if not settings.OTEL_ENABLED:
        return TelemetryRuntime()

    try:
        endpoint = settings.get_otel_logs_endpoint()
        provider = LoggerProvider(
            resource=Resource.create({ResourceAttributes.SERVICE_NAME: settings.OTEL_SERVICE_NAME})
        )
        exporter = OTLPLogExporter(
            endpoint=endpoint,
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
        return TelemetryRuntime()

    runtime = TelemetryRuntime(provider=provider, sink_id=sink_id)
    logger.info(
        "OpenTelemetry log export enabled | service={} endpoint={}",
        settings.OTEL_SERVICE_NAME,
        endpoint,
    )
    logger.info("OpenTelemetry startup probe")
    if not runtime.flush():
        logger.error("OpenTelemetry startup probe flush timed out")

    return runtime
