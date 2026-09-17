"""Data import API routes."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.modules.burp_importer import burp_importer

router = APIRouter(prefix="/api/import", tags=["import"])


class RawImportRequest(BaseModel):
    request: str
    response: str = ""


@router.post("/burp-xml")
async def import_burp_xml(file: UploadFile = File(...)):
    """Import Burp Suite XML export file."""
    content = await file.read()
    try:
        exchanges = burp_importer.import_burp_xml(content)
        return {
            "status": "ok",
            "imported": len(exchanges),
            "total": len(burp_importer.exchanges),
            "summary": burp_importer.get_summary(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {e}")


@router.post("/har")
async def import_har(file: UploadFile = File(...)):
    """Import HAR file."""
    content = await file.read()
    try:
        exchanges = burp_importer.import_har(content)
        return {
            "status": "ok",
            "imported": len(exchanges),
            "total": len(burp_importer.exchanges),
            "summary": burp_importer.get_summary(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {e}")


@router.post("/raw")
async def import_raw(req: RawImportRequest):
    """Import a raw HTTP request/response pair."""
    exchange = burp_importer.import_raw(req.request, req.response)
    return {
        "status": "ok",
        "exchange_id": exchange.id,
        "summary": exchange.summary,
    }


@router.get("/exchanges")
async def list_exchanges(
    method: str | None = None,
    status_code: int | None = None,
    path_contains: str | None = None,
    limit: int = 100,
):
    """List imported exchanges with optional filters."""
    exchanges = burp_importer.get_exchanges(
        method=method,
        status_code=status_code,
        path_contains=path_contains,
    )
    return {
        "total": len(exchanges),
        "exchanges": [
            {
                "id": e.id,
                "method": e.request.method,
                "url": e.request.url,
                "path": e.request.path,
                "status": e.response.status_code,
                "params": e.request.params_summary,
                "content_type": e.request.content_type,
                "has_body": bool(e.request.body),
                "summary": e.summary,
            }
            for e in exchanges[:limit]
        ],
    }


@router.get("/exchanges/{exchange_id}")
async def get_exchange(exchange_id: int):
    """Get full details of a specific exchange."""
    ex = burp_importer.get_exchange(exchange_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exchange not found")
    return {
        "id": ex.id,
        "request": {
            "method": ex.request.method,
            "url": ex.request.url,
            "path": ex.request.path,
            "host": ex.request.host,
            "headers": [{"name": h.name, "value": h.value} for h in ex.request.headers],
            "body": ex.request.body,
            "content_type": ex.request.content_type,
            "params": ex.request.params_summary,
            "raw": ex.request.raw,
        },
        "response": {
            "status_code": ex.response.status_code,
            "status_text": ex.response.status_text,
            "headers": [{"name": h.name, "value": h.value} for h in ex.response.headers],
            "body": ex.response.body,
            "content_type": ex.response.content_type,
            "raw": ex.response.raw,
        },
    }


@router.get("/summary")
async def get_summary():
    """Get import statistics."""
    return burp_importer.get_summary()


@router.delete("/clear")
async def clear_imports():
    """Clear all imported data."""
    burp_importer.clear()
    return {"status": "ok", "message": "All data cleared"}
