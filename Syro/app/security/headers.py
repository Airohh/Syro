"""Headers de sécurité HTTP."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware pour ajouter des headers de sécurité HTTP."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Headers de sécurité
        security_headers = {
            # Empêcher le MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Empêcher le clickjacking
            "X-Frame-Options": "DENY",
            
            # Politique de référent
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy (anciennement Feature Policy)
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=(), "
                "accelerometer=()"
            ),
        }
        
        # Ajouter HSTS seulement en HTTPS
        if request.url.scheme == "https":
            security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Ajouter les headers à la réponse
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response

