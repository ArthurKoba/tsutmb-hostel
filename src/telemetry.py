from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import SpanKind

if TYPE_CHECKING:
    from collections.abc import Iterator

    from settings import ApplicationSettings


_TRACER_NAME = "tsutmb-hostel"
_tracer = trace.get_tracer(_TRACER_NAME)


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


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    *,
    kind: SpanKind = SpanKind.INTERNAL,
) -> Iterator[trace.Span]:
    with _tracer.start_as_current_span(name, attributes=attributes, kind=kind) as span:
        yield span


@contextmanager
def client_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[trace.Span]:
    with trace_span(name, attributes, kind=SpanKind.CLIENT) as span:
        yield span


@dataclass(slots=True)
class TelemetryRuntime:
    logger_provider: LoggerProvider | None = None
    tracer_provider: TracerProvider | None = None
    sink_id: int | None = None

    def flush(self, timeout_millis: int = 5000) -> bool:
        logs_ok = self.logger_provider is None or self.logger_provider.force_flush(
            timeout_millis=timeout_millis
        )
        traces_ok = self.tracer_provider is None or self.tracer_provider.force_flush(
            timeout_millis=timeout_millis
        )
        return logs_ok and traces_ok

    def shutdown(self) -> None:
        if self.sink_id is not None:
            logger.remove(self.sink_id)
        if not self.flush():
            logger.error("OpenTelemetry force_flush timed out")
        if self.logger_provider is not None:
            self.logger_provider.shutdown()
        if self.tracer_provider is not None:
            self.tracer_provider.shutdown()


def _build_resource(settings: ApplicationSettings) -> Resource:
    return Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: settings.OTEL_SERVICE_NAME,
            ResourceAttributes.SERVICE_VERSION: settings.OTEL_SERVICE_VERSION,
            "service.instance.id": settings.get_otel_service_instance_id(),
            "deployment.environment.name": settings.OTEL_ENVIRONMENT,
        }
    )


def setup_telemetry(settings: ApplicationSettings) -> TelemetryRuntime:
    if not settings.OTEL_ENABLED:
        return TelemetryRuntime()

    try:
        resource = _build_resource(settings)
        headers = settings.get_otel_headers()

        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(
                    endpoint=settings.get_otel_logs_endpoint(),
                    headers=headers,
                )
            )
        )
        set_logger_provider(logger_provider)

        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=settings.get_otel_traces_endpoint(),
                    headers=headers,
                )
            )
        )
        trace.set_tracer_provider(tracer_provider)

        handler = LoggingHandler(logger_provider=logger_provider)
        sink_id = logger.add(
            lambda message: handler.emit(_to_logging_record(message)),
            level=settings.OTEL_LOG_LEVEL,
            enqueue=False,
            backtrace=False,
            diagnose=False,
            filter=lambda record: not record["name"].startswith("opentelemetry"),
        )
    except Exception:
        logger.exception("OpenTelemetry initialization failed; continuing without exporter")
        return TelemetryRuntime()

    logger.info(
        "OpenTelemetry enabled | service={} version={} instance={} environment={}",
        settings.OTEL_SERVICE_NAME,
        settings.OTEL_SERVICE_VERSION,
        settings.get_otel_service_instance_id(),
        settings.OTEL_ENVIRONMENT,
    )
    return TelemetryRuntime(
        logger_provider=logger_provider,
        tracer_provider=tracer_provider,
        sink_id=sink_id,
    )
