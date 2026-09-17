from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict

from app.modules.database import save_exchange, get_exchanges, get_findings
from app.modules.scope_fetcher import fetch_hackerone_scope
from app.modules.dedup_filter import dedup_filter

router = APIRouter(prefix="/api/import", tags=["live"])


class LiveRequest(BaseModel):
    host: str
    url: str = ""
    path: str = ""
    method: str = "GET"
    status_code: int = 0
    request_b64: str = ""
    response_b64: str = ""
    request_headers: Optional[Dict] = {}
    response_headers: Optional[Dict] = {}
    program_id: Optional[str] = ""
    force_analyze: bool = False


@router.post("/live")
async def receive_live_request(req: LiveRequest):
    """
    BurpNake Connector'dan gelen canli HTTP trafikini alir.
    Deduplication + statik asset filtresi uygular.
    """
    exchange_data = {
        "host": req.host, "url": req.url, "path": req.path,
        "method": req.method, "status_code": req.status_code,
        "request_b64": req.request_b64, "request_headers": req.request_headers or {},
    }
    should_skip, skip_reason = dedup_filter.should_skip(exchange_data)
    if should_skip and not req.force_analyze:
        return {"status": "skipped", "reason": skip_reason}

    eid = save_exchange({
        "host": req.host, "url": req.url, "path": req.path,
        "method": req.method, "status_code": req.status_code,
        "request_b64": req.request_b64, "response_b64": req.response_b64,
        "request_headers": req.request_headers or {},
        "response_headers": req.response_headers or {},
        "program_id": req.program_id or "",
        "interest_level": "pending", "ai_analyzed": False,
    })
    return {"status": "ok", "id": eid, "interest_level": "pending"}


@router.get("/live-pull")
async def pull_live_requests():
    """Web arayuzunun polling ile cektigi canli + kayitli istekler."""
    exchanges = get_exchanges(limit=100)
    return {"exchanges": exchanges}


@router.get("/live-status")
async def live_status():
    """Connector saglik kontrolu - JAR bu endpoint'i ping'ler."""
    from app.modules.database import get_stats
    stats = get_stats()
    return {"status": "online", "app": "BurpNake", "version": "2.0.0", "stats": stats}


@router.get("/findings")
async def get_all_findings(program_id: Optional[str] = None):
    """Tum AI bulgularini dondurur."""
    findings = get_findings(program_id=program_id or None)
    return {"findings": findings}


@router.post("/scope/fetch-hackerone")
async def fetch_h1_scope(handle: str):
    """HackerOne'dan program scope'unu otomatik ceker."""
    result = await fetch_hackerone_scope(handle)
    return result
