from fastapi import APIRouter, HTTPException
from typing import Optional

from app.modules.database import get_findings, get_stats, save_finding, get_db
from app.modules.report_generator import generate_report

router = APIRouter()


@router.get("/stats")
def findings_stats(program_id: Optional[str] = None):
    return get_stats(program_id)


@router.get("/")
def list_findings(
    program_id: Optional[str] = None,
    severity: Optional[str] = None,
    confirmed_only: bool = False,
):
    findings = get_findings(
        program_id=program_id,
        severity=severity,
        confirmed_only=confirmed_only,
    )
    return {"findings": findings}


@router.get("/{fid}")
def get_finding(fid: str):
    conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT * FROM findings WHERE id=?", (fid,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Finding not found")
    return dict(row)


@router.put("/{fid}/confirm")
def confirm_finding(fid: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE findings SET confirmed=1 WHERE id=?", (fid,))
    conn.commit()
    conn.close()
    return {"status": "confirmed"}


@router.put("/{fid}/dismiss")
def dismiss_finding(fid: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE findings SET dismissed=1 WHERE id=?", (fid,))
    conn.commit()
    conn.close()
    return {"status": "dismissed"}


@router.get("/{fid}/report")
async def get_finding_report(fid: str, platform: str = "hackerone"):
    conn = get_db()
    c = conn.cursor()
    frow = c.execute("SELECT * FROM findings WHERE id=?", (fid,)).fetchone()
    if not frow:
        conn.close()
        raise HTTPException(status_code=404, detail="Finding not found")
    finding = dict(frow)

    exrow = c.execute(
        "SELECT * FROM exchanges WHERE id=?", (finding.get("exchange_id", ""),)
    ).fetchone()
    conn.close()
    exchange = dict(exrow) if exrow else {}

    report_md = await generate_report(finding, exchange, platform)

    # Raporu findings tablosuna kaydet
    conn2 = get_db()
    c2 = conn2.cursor()
    c2.execute("UPDATE findings SET confirmed=1 WHERE id=?", (fid,))
    conn2.commit()
    conn2.close()

    return {"report": report_md, "platform": platform}
