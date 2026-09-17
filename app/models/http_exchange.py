"""HTTP exchange data models for Burp Suite data."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class HttpHeader(BaseModel):
    """Single HTTP header."""
    name: str
    value: str


class HttpRequest(BaseModel):
    """Parsed HTTP request."""
    id: int = 0
    method: str = "GET"
    url: str = ""
    path: str = ""
    host: str = ""
    port: int = 443
    protocol: str = "https"
    http_version: str = "HTTP/1.1"
    headers: list[HttpHeader] = Field(default_factory=list)
    body: str = ""
    content_type: str = ""
    cookies: str = ""
    raw: str = ""

    @property
    def has_params(self) -> bool:
        return "?" in self.url or bool(self.body)

    @property
    def params_summary(self) -> str:
        """Extract parameter names from URL and body."""
        params: list[str] = []
        if "?" in self.url:
            query = self.url.split("?", 1)[1]
            for pair in query.split("&"):
                if "=" in pair:
                    params.append(pair.split("=", 1)[0])
        if self.body and "=" in self.body:
            for pair in self.body.split("&"):
                if "=" in pair:
                    params.append(pair.split("=", 1)[0])
        return ", ".join(params) if params else "none"

    def get_header(self, name: str) -> Optional[str]:
        for h in self.headers:
            if h.name.lower() == name.lower():
                return h.value
        return None


class HttpResponse(BaseModel):
    """Parsed HTTP response."""
    status_code: int = 0
    status_text: str = ""
    http_version: str = "HTTP/1.1"
    headers: list[HttpHeader] = Field(default_factory=list)
    body: str = ""
    content_type: str = ""
    content_length: int = 0
    raw: str = ""

    def get_header(self, name: str) -> Optional[str]:
        for h in self.headers:
            if h.name.lower() == name.lower():
                return h.value
        return None


class HttpExchange(BaseModel):
    """A complete HTTP request-response pair from Burp Suite."""
    id: int = 0
    request: HttpRequest = Field(default_factory=HttpRequest)
    response: HttpResponse = Field(default_factory=HttpResponse)
    timestamp: Optional[datetime] = None
    source: str = "burp_import"  # burp_import, har_import, manual
    tags: list[str] = Field(default_factory=list)
    notes: str = ""

    @property
    def summary(self) -> str:
        return (
            f"#{self.id} {self.request.method} {self.request.path} "
            f"→ {self.response.status_code} "
            f"[params: {self.request.params_summary}]"
        )
