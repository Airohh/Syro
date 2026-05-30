from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse

from .config import settings
from .domains import get_domain_config, list_domains
from .routers import admin, agents, auth, chat, documents, mlops, profile, permissions
from .services.vector_store import VectorStoreError
from .middleware import (
    setup_logging,
    CorrelationIDMiddleware,
    MetricsMiddleware,
    setup_tracing,
    get_metrics_response,
)
from .security import SecurityHeadersMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from scripts.init_db import init_db
        init_db()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("DB init skipped: %s", e)
    yield

# Configurer le tracing OpenTelemetry
setup_tracing(
    service_name=settings.app_name.lower(),
    otlp_endpoint=settings.otlp_endpoint,
    enabled=settings.tracing_enabled
)

domain_config = get_domain_config(settings.domain)
app = FastAPI(
    title=domain_config.name,
    description=domain_config.description,
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    swagger_ui_parameters={"tryItOutEnabled": True}
)

# Middlewares d'observabilité (ordre important : correlation ID d'abord, puis metrics)
app.add_middleware(CorrelationIDMiddleware)
if settings.metrics_enabled:
    app.add_middleware(MetricsMiddleware)

# Middleware de sécurité (headers HTTP)
if settings.enable_security_headers:
    app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware (configurable)
cors_origins = settings.cors_allow_origins.split(",") if "," in settings.cors_allow_origins else (
    [settings.cors_allow_origins] if settings.cors_allow_origins != "*" else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(chat.domain_router)
app.include_router(documents.router)
app.include_router(documents.domain_router)  # Routes multi-domaines pour documents
app.include_router(profile.router)
app.include_router(permissions.router)
app.include_router(admin.router)
app.include_router(agents.router)
app.include_router(mlops.router)

@app.exception_handler(VectorStoreError)
async def vector_store_error_handler(request: Request, exc: VectorStoreError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "Qdrant connection failed",
            "message": str(exc),
            "solution": "Please ensure Qdrant is running: docker-compose up -d qdrant"
        }
    )

@app.get("/health")
def healthcheck():
    domain_config = get_domain_config(settings.domain)
    return {
        "status": "ok",
        "domain": settings.domain,
        "app_name": domain_config.name,
    }

@app.get("/domains/{domain}/health")
def healthcheck_domain(domain: str):
    """Healthcheck pour un domaine spécifique."""
    from fastapi import HTTPException
    domain_config = get_domain_config(domain)
    # Si le domaine n'existe pas, get_domain_config retourne "general" par défaut
    # Vérifier si le domaine demandé existe vraiment
    from .domains import DOMAINS
    if domain.lower() not in DOMAINS:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")
    
    return {
        "status": "ok",
        "domain": domain,
        "app_name": domain_config.name,
        "description": domain_config.description,
    }

@app.get("/domains")
def get_domains():
    """List all available domains."""
    return {
        "current_domain": settings.domain,
        "current_config": {
            "name": get_domain_config(settings.domain).name,
            "description": get_domain_config(settings.domain).description,
        },
        "available_domains": list_domains(),
    }

@app.get("/metrics")
def metrics():
    """Endpoint Prometheus pour les métriques."""
    metrics_data, content_type = get_metrics_response()
    return Response(content=metrics_data, media_type=content_type)
