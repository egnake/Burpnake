"""
CVSS & Remediation API Routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.modules.cvss_calculator import cvss_calculator, CVSSResult
from app.modules.remediation_engine import remediation_engine

router = APIRouter(prefix="/api/cvss", tags=["cvss"])


class CVSSCalcRequest(BaseModel):
    vector: Optional[str] = None
    av: Optional[str] = "N"
    ac: Optional[str] = "L"
    pr: Optional[str] = "N"
    ui: Optional[str] = "N"
    s: Optional[str] = "U"
    c: Optional[str] = "N"
    i: Optional[str] = "N"
    a: Optional[str] = "N"


@router.post("/calculate")
async def calculate_cvss(req: CVSSCalcRequest):
    """Calculates CVSS v3.1 base score and breakdown."""
    try:
        if req.vector and "CVSS:3.1" in req.vector:
            res = cvss_calculator.calculate_from_vector(req.vector)
        else:
            res = cvss_calculator.calculate(
                av=req.av or "N",
                ac=req.ac or "L",
                pr=req.pr or "N",
                ui=req.ui or "N",
                s=req.s or "U",
                c=req.c or "N",
                i=req.i or "N",
                a=req.a or "N",
            )
        return {
            "vector": res.vector,
            "base_score": res.base_score,
            "severity": res.severity,
            "exploitability_score": res.exploitability_score,
            "impact_score": res.impact_score,
            "metrics": res.metrics,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CVSS calculation error: {e}")


@router.get("/suggest/{vuln_type}")
async def suggest_vector(vuln_type: str):
    """Provides default suggested CVSS v3.1 vector and score for a vulnerability type."""
    vector = cvss_calculator.get_default_vector(vuln_type)
    res = cvss_calculator.calculate_from_vector(vector)
    return {
        "vuln_type": vuln_type,
        "suggested_vector": res.vector,
        "base_score": res.base_score,
        "severity": res.severity,
    }


@router.get("/remediation/{vuln_type}")
async def get_remediation(vuln_type: str):
    """Retrieves taxonomy and secure code remediation patterns for a vulnerability."""
    bp = remediation_engine.get_blueprint(vuln_type)
    return {
        "cwe_id": bp.cwe_id,
        "cwe_name": bp.cwe_name,
        "cwe_url": bp.cwe_url,
        "owasp_category": bp.owasp_category,
        "guidance": bp.guidance,
        "code_examples": bp.code_examples,
    }
