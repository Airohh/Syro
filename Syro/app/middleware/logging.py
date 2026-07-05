"""Middleware pour logging structuré avec correlation IDs."""

import json
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Logger structuré JSON
class JSONFormatter(logging.Formatter):
    """Formatter pour logs JSON structurés."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Ajouter correlation_id si présent
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        
        # Ajouter request_id si présent
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Ajouter user_id si présent
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        # Ajouter domain si présent
        if hasattr(record, "domain"):
            log_data["domain"] = record.domain
        
        # Ajouter exception info si présent
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Ajouter extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)

def setup_logging(log_level: str = "INFO", json_format: bool = True):
    """
    Configurer le logging structuré.
    
    Args:
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Si True, utiliser le format JSON
    """
    # Obtenir le logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Supprimer les handlers existants
    root_logger.handlers.clear()
    
    # Créer un handler console
    handler = logging.StreamHandler()
    handler.setLevel(getattr(logging, log_level.upper()))
    
    # Utiliser le formatter JSON ou standard
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Désactiver les logs verbeux de certaines libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware pour ajouter un correlation ID à chaque requête."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Générer un correlation ID unique
        correlation_id = str(uuid.uuid4())
        
        # Ajouter au contexte de la requête
        request.state.correlation_id = correlation_id
        
        # Ajouter au header de la réponse
        start_time = time.time()
        
        # Logger la requête entrante
        logger = logging.getLogger("syro.request")
        logger.info(
            "Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
            }
        )
        
        # Traiter la requête
        try:
            response = await call_next(request)
            
            # Calculer la durée
            duration_ms = (time.time() - start_time) * 1000
            
            # Logger la réponse
            logger.info(
                "Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
            
            # Ajouter le correlation ID au header
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            
            # Logger l'erreur
            logger = logging.getLogger("syro.request")
            logger.error(
                "Request failed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "exception": str(exc),
                },
                exc_info=True,
            )
            
            raise

def get_logger(name: str) -> logging.Logger:
    """
    Obtenir un logger avec support du correlation ID.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Message", extra={"user_id": 123, "domain": "tech"})
    """
    return logging.getLogger(name)

