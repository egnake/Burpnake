"""Report generation API routes."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from app.modules.database import get_db, get_findings

router = APIRouter(prefix="/api/report", tags=["report"])


class FindingReportRequest(BaseModel):
    finding_id: str
    platform: str = "hackerone"  # hackerone, bugcrowd, yeswehack


class ManualReportRequest(BaseModel):
    title: str
    vuln_type: str = "other"
    severity: str = "medium"
    description: str
    impact: str = ""
    affected_url: str = ""
    affected_parameter: str = ""
    steps_to_reproduce: List[str] = []
    platform: str = "hackerone"


@router.post("/generate-from-finding")
async def generate_report_from_finding(req: FindingReportRequest):
    """DB'deki bir finding'den platform-spesifik rapor uretir."""
    from app.modules.report_generator import generate_report

    conn = get_db()
    finding_row = conn.execute("SELECT * FROM findings WHERE id=?", (req.finding_id,)).fetchone()
    conn.close()

    if not finding_row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Finding bulunamadi")

    finding = dict(finding_row)

    # Ilgili exchange'i de cek
    exchange = {}
    if finding.get("exchange_id"):
        conn2 = get_db()
        ex_row = conn2.execute("SELECT * FROM exchanges WHERE id=?", (finding["exchange_id"],)).fetchone()
        conn2.close()
        if ex_row:
            exchange = dict(ex_row)

    report_content = await generate_report(finding, exchange, platform=req.platform)
    return {"status": "ok", "platform": req.platform, "content": report_content}


@router.post("/generate")
async def generate_manual_report(req: ManualReportRequest):
    """Manuel olarak girilen bilgilerden rapor ve PoC uretir, dosyaya kaydeder."""
    from datetime import datetime, timezone
    from app.config import settings
    from app.core.llm_gateway import llm_gateway
    from app.models.vulnerability import Vulnerability, VulnType, Severity
    from app.modules.poc_generator import poc_generator

    platform_prompts = {
        "hackerone": "HackerOne submission format: ## Summary, ## Severity, ## Steps To Reproduce, ## Impact",
        "bugcrowd": "Bugcrowd submission format: ### Description, ### Proof of Concept, ### Severity, ### Impact",
        "yeswehack": "YesWeHack format: ## Vulnerability Description, ## Steps to Reproduce, ## Impact Assessment",
    }

    prompt = f"""Write a professional bug bounty report for the following vulnerability:

Title: {req.title}
Type: {req.vuln_type}
Severity: {req.severity}
Description: {req.description}
Affected URL: {req.affected_url}
Parameter: {req.affected_parameter}
Impact: {req.impact}
Steps: {chr(10).join(req.steps_to_reproduce)}

Platform format: {platform_prompts.get(req.platform, platform_prompts['hackerone'])}

Write the complete report now. Be professional, clear, and include CVSS score."""

    try:
        content = await llm_gateway.generate(prompt)
    except Exception as e:
        content = f"## {req.title}\n\n{req.description}\n\n*Report generation error: {e}*"

    # PoC uretimi (LLM + deterministik yedek)
    v_type = next((vt for vt in VulnType if vt.value == req.vuln_type.lower()), VulnType.OTHER)
    v_sev = next((s for s in Severity if s.value == req.severity.lower()), Severity.MEDIUM)
    vuln_obj = Vulnerability(
        title=req.title,
        vuln_type=v_type,
        severity=v_sev,
        description=req.description,
        impact=req.impact,
        affected_url=req.affected_url,
        affected_parameter=req.affected_parameter,
        steps_to_reproduce=req.steps_to_reproduce,
    )
    target_url = req.affected_url or "https://target.local/"
    fallback_curl = f"curl -i -k '{target_url}'"
    try:
        poc_data = await poc_generator.generate(vuln_obj)
        if not isinstance(poc_data, dict):
            poc_data = {"curl": fallback_curl, "python": "", "description": str(poc_data)}
        elif not poc_data.get("curl"):
            poc_data["curl"] = fallback_curl
    except Exception:
        poc_data = {
            "curl": fallback_curl,
            "python": f"import requests\nresp = requests.get({target_url!r}, timeout=15)\nprint(resp.status_code, resp.text[:500])",
            "description": "\n".join(req.steps_to_reproduce),
        }

    # Raporu data/reports dizinine kaydet
    reports_dir = settings.DATA_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_id = f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    file_path = reports_dir / f"{report_id}.md"
    file_path.write_text(content, encoding="utf-8")

    return {
        "status": "ok",
        "report_id": report_id,
        "file_path": str(file_path),
        "platform": req.platform,
        "content": content,
        "poc": poc_data,
    }


@router.get("/findings-list")
async def list_reportable_findings(program_id: Optional[str] = None):
    """Rapor uretilecek finding listesini dondurur."""
    findings = get_findings(program_id=program_id or None)
    return {"findings": findings, "total": len(findings)}
