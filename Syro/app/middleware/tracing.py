"""Middleware pour traces OpenTelemetry."""

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


def setup_tracing(
    service_name: str = "syro-api",
    otlp_endpoint: str | None = None,
    enabled: bool = True,
):
    """
    Configurer OpenTelemetry tracing.

    Args:
        service_name: Nom du service
        otlp_endpoint: Endpoint OTLP (ex: http://localhost:4317)
        enabled: Si False, désactiver le tracing
    """
    if not OPENTELEMETRY_AVAILABLE or not enabled:
        return

    if not otlp_endpoint:
        # Si pas d'endpoint configuré, ne pas initialiser
        return

    try:
        # Créer l'exporter OTLP
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)

        # Créer le TracerProvider avec le nom du service
        provider = TracerProvider(resource=Resource({"service.name": service_name}))

        # Ajouter le processor
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        # Définir le provider global
        trace.set_tracer_provider(provider)

        # Instrumenter FastAPI et HTTPX
        FastAPIInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()

    except Exception as e:
        # Logger l'erreur mais ne pas faire échouer l'application
        import logging

        logger = logging.getLogger("syro.tracing")
        logger.warning(f"Failed to setup OpenTelemetry: {e}")


def get_tracer(name: str):
    """
    Obtenir un tracer OpenTelemetry.

    Usage:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("operation_name") as span:
            span.set_attribute("key", "value")
            # ... code ...
    """
    if not OPENTELEMETRY_AVAILABLE:
        # Retourner un tracer no-op
        class NoOpTracer:
            def start_as_current_span(self, *args, **kwargs):
                return NoOpSpan()

        class NoOpSpan:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def set_attribute(self, *args, **kwargs):
                pass

            def set_status(self, *args, **kwargs):
                pass

        return NoOpTracer()

    return trace.get_tracer(name)
