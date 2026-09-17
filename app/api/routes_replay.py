"""Request Replay API — Burp Repeater benzeri istek tekrarlama."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import httpx
import time

router = APIRouter(prefix="/api/replay", tags=["replay"])

class ReplayRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = {}
    body: Optional[str] = ""
    follow_redirects: bool = False

@router.post("/send")
async def replay_request(req: ReplayRequest):
    """HTTP istegi gonder ve yaniti dondur."""
    try:
        start = time.time()
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=req.follow_redirects,
            verify=False,
        ) as client:
            headers = {k: v for k, v in (req.headers or {}).items()
                      if k.lower() not in ('content-length', 'host', 'transfer-encoding')}
            
            resp = await client.request(
                method=req.method,
                url=req.url,
                headers=headers,
                content=req.body.encode() if req.body else None,
            )
            elapsed = (time.time() - start) * 1000
            
            return {
                "status_code": resp.status_code,
                "reason": resp.reason_phrase,
                "headers": dict(resp.headers),
                "body": resp.text[:50000],
                "elapsed_ms": round(elapsed, 2),
                "content_length": len(resp.content),
                "http_version": str(resp.http_version),
            }
    except httpx.ConnectError as e:
        raise HTTPException(status_code=502, detail=f"Baglanti hatasi: {e}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Istek zaman asimina ugradi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
