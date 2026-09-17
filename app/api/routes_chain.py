"""Vulnerability Chain Analysis API."""
from fastapi import APIRouter
from app.modules.chain_builder import chain_builder
from app.modules.database import get_findings, get_exchanges

router = APIRouter(prefix="/api/chains", tags=["chains"])

@router.get("/analyze")
async def analyze_chains(program_id: str = None):
    """Mevcut finding'ler arasindaki zafiyet zincirlerini analiz et."""
    findings = get_findings(program_id=program_id)
    exchanges = get_exchanges(program_id=program_id, interest_level="critical", limit=500)
    
    all_items = findings + exchanges
    chains = chain_builder.analyze_chains(all_items)
    suggestions = chain_builder.suggest_missing_vulns(all_items)
    
    return {
        "chains": [
            {
                "name": c.name,
                "severity": c.severity,
                "description": c.description,
                "bounty_estimate": c.bounty_estimate,
                "coverage": round(c.coverage * 100),
                "matched_vulns": c.matched_vulns,
                "required_vulns": c.required_vulns,
            }
            for c in chains
        ],
        "suggestions": suggestions,
        "total_chains": len(chains),
    }
