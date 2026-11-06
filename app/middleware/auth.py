import logging
import secrets
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.config import settings

logger = logging.getLogger("burpnake.auth")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Dev mode: API_KEY tanimli degilse tum isteklere izin ver
        if not settings.API_KEY:
            return await call_next(request)

        # 2. CORS Preflight istekleri yetkilendirme basligina sahip olmaz
        if request.method == "OPTIONS":
            return await call_next(request)

        # 3. Genel muafiyet rotalari
        exempt_paths = ["/", "/health", "/docs", "/openapi.json", "/api/stream/stream", "/api/import/live"]
        if request.url.path == "/" or any(request.url.path.startswith(p) for p in exempt_paths if p != "/"):
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid authorization header"})
            
        parts = auth_header.split(" ", 1)
        if len(parts) != 2:
            return JSONResponse(status_code=401, content={"detail": "Invalid authorization header format"})

        token = parts[1].strip()
        if not secrets.compare_digest(token, settings.API_KEY):
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
            
        return await call_next(request)
