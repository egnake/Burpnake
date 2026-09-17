"""Scope management API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.modules.scope_manager import scope_manager


router = APIRouter(prefix="/api/scope", tags=["scope"])


class ScopeSetRequest(BaseModel):
    program_name: str
    platform: str = "hackerone"
    include_domains: list[str]
    exclude_domains: list[str] = []


class ScopeCheckRequest(BaseModel):
    url: str


@router.post("/set")
async def set_scope(req: ScopeSetRequest):
    """Set the bug bounty program scope."""
    scope = scope_manager.set_from_domains(
        program_name=req.program_name,
        include_domains=req.include_domains,
        exclude_domains=req.exclude_domains,
        platform=req.platform,
    )
    return {"status": "ok", "scope": scope_manager.get_scope_summary()}


@router.get("/current")
async def get_scope():
    """Get the current scope configuration."""
    return scope_manager.get_scope_summary()


@router.post("/check")
async def check_scope(req: ScopeCheckRequest):
    """Check if a URL is in scope."""
    in_scope = scope_manager.is_in_scope(req.url)
    return {"url": req.url, "in_scope": in_scope}
