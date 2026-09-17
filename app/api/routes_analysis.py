"""Analysis API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.modules.vulnerability_analyzer import vulnerability_analyzer
from app.modules.burp_importer import burp_importer

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    exchange_ids: list[int] | None = None
    focus: str | None = None  # e.g., "idor", "sqli", "ssrf"


class AnalyzeSingleRequest(BaseModel):
    exchange_id: int
    vuln_type: str | None = None


@router.post("/batch")
async def analyze_batch(req: AnalyzeRequest):
    """Analyze multiple exchanges for vulnerabilities."""
    if req.exchange_ids:
        exchanges = [
            burp_importer.get_exchange(eid)
            for eid in req.exchange_ids
        ]
        exchanges = [e for e in exchanges if e is not None]
    else:
        exchanges = burp_importer.exchanges

    if not exchanges:
        raise HTTPException(status_code=400, detail="No exchanges to analyze")

    findings = await vulnerability_analyzer.analyze_exchanges(
        exchanges, focus=req.focus
    )
    return {"findings": findings, "analyzed_count": len(exchanges)}


@router.post("/single")
async def analyze_single(req: AnalyzeSingleRequest):
    """Deep analysis of a single exchange."""
    exchange = burp_importer.get_exchange(req.exchange_id)
    if not exchange:
        raise HTTPException(status_code=404, detail="Exchange not found")

    analysis = await vulnerability_analyzer.analyze_single(
        exchange, vuln_type=req.vuln_type
    )
    return {"exchange_id": req.exchange_id, "analysis": analysis}
