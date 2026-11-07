"""Vulnerability Chain Analysis API."""
from fastapi import APIRouter
from app.modules.chain_builder import chain_builder, ai_chain_agent
from app.modules.database import get_findings, get_exchanges

router = APIRouter(prefix="/api/chains", tags=["chains"])

@router.get("/analyze")
async def analyze_chains(program_id: str | None = None, use_ai: bool = False):
    """Mevcut finding'ler arasindaki zafiyet zincirlerini analiz et."""
    findings = get_findings(program_id=program_id)
    exchanges = get_exchanges(program_id=program_id, interest_level="critical", limit=500)
    
    all_items = findings + exchanges
    chains = chain_builder.analyze_chains(all_items)
    if use_ai and len(all_items) >= 2:
        ai_chain = await ai_chain_agent.analyze_dynamic_chains(all_items[:15])
        if ai_chain:
            chains.append(ai_chain)
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
