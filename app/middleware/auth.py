import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.config import settings

logger = logging.getLogger("burpnake.auth")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.API_KEY:
            return await call_next(request)

        exempt_paths = ["/health", "/docs", "/openapi.json", "/api/stream/stream", "/api/import/live"]
        if any(request.url.path.startswith(p) for p in exempt_paths):
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid authorization header"})
            
        token = auth_header.split(" ")[1]
        if token != settings.API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
            
        return await call_next(request)
