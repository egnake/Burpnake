"""BurpNake Agent API Routes."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import asyncio

from app.modules.database import get_exchanges, get_findings, get_db, save_finding
from app.modules.event_broadcaster import broadcast

router = APIRouter(prefix="/api/agent", tags=["agent"])


class HuntRequest(BaseModel):
    exchange_id: str
    force: bool = False


class BatchHuntRequest(BaseModel):
    exchange_ids: List[str]
    min_score: int = 70


@router.post("/hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    """Belirli bir exchange uzerinde otonom agent dongusunu baslatir."""
    from app.modules.agent_loop import autonomous_agent
    if autonomous_agent is None:
        raise HTTPException(status_code=503, detail="Agent henuz baslatilmadi")

    conn = get_db()
    row = conn.execute("SELECT * FROM exchanges WHERE id=?", (req.exchange_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Exchange bulunamadi")

    ex_dict = dict(row)
    if ex_dict.get("interest_level") == "confirmed" and not req.force:
        raise HTTPException(status_code=409, detail="Bu exchange zaten onaylandi. Force=true ile tekrar calistir.")

    reason = ex_dict.get("interest_reason", "")
    matched_vulns = [r.strip() for r in reason.split(",") if r.strip()] or ["unknown"]

    async def run_agent():
        result = await autonomous_agent.hunt(ex_dict, matched_vulns, broadcast)
        await broadcast("agent_complete", {
            "exchange_id": req.exchange_id, "success": result.success,
            "finding_id": result.finding_id, "iterations": result.iterations,
            "summary": result.summary,
            "msg": f"{'🎯 Acik bulundu!' if result.success else '🔍 Acik bulunamadi'} ({result.iterations} iter)",
        })

    background_tasks.add_task(run_agent)
    return {
        "status": "started", "exchange_id": req.exchange_id,
        "matched_vulns": matched_vulns,
        "msg": f"Agent baslatildi: {ex_dict.get('method','GET')} {ex_dict.get('path','/')}",
    }


@router.post("/hunt-batch")
async def start_batch_hunt(req: BatchHuntRequest, background_tasks: BackgroundTasks):
    """Birden fazla exchange uzerinde ardisik otonom avlanma."""
    from app.modules.agent_loop import autonomous_agent
    if autonomous_agent is None:
        raise HTTPException(status_code=503, detail="Agent henuz baslatilmadi")

    started = []
    skipped = []
    for eid in req.exchange_ids:
        conn = get_db()
        row = conn.execute("SELECT * FROM exchanges WHERE id=?", (eid,)).fetchone()
        conn.close()
        if not row:
            skipped.append(eid)
            continue
        ex_dict = dict(row)
        if ex_dict.get("score", 0) < req.min_score:
            skipped.append(eid)
            continue
        reason = ex_dict.get("interest_reason", "")
        matched_vulns = [r.strip() for r in reason.split(",") if r.strip()] or ["unknown"]

        async def run_one(ex=ex_dict, mv=matched_vulns):
            result = await autonomous_agent.hunt(ex, mv, broadcast)
            await broadcast("agent_complete", {
                "exchange_id": ex["id"], "success": result.success,
                "finding_id": result.finding_id, "iterations": result.iterations,
                "msg": f"{'🎯' if result.success else '🔍'} {ex.get('path','/')} ({result.iterations} iter)",
            })

        background_tasks.add_task(run_one)
        started.append(eid)

    return {"status": "batch_started", "started": len(started), "skipped": len(skipped),
            "started_ids": started, "skipped_ids": skipped}


@router.get("/auto-hunt-queue")
async def get_auto_hunt_queue():
    """Henuz incelenmemis kritik/interesting exchange'leri dondurur."""
    conn = get_db()
    rows = conn.execute(
        """SELECT id, host, path, method, status_code, score, interest_level, interest_reason
           FROM exchanges WHERE interest_level IN ('critical','interesting') AND ai_analyzed=0
           ORDER BY score DESC LIMIT 50"""
    ).fetchall()
    conn.close()
    return {"queue": [dict(r) for r in rows], "total": len(rows)}


@router.post("/auto-hunt-all")
async def auto_hunt_all_pending(background_tasks: BackgroundTasks, min_score: int = 70):
    """Kuyruktaki tum critical/interesting exchange'leri otomatik avlar."""
    from app.modules.agent_loop import autonomous_agent
    if autonomous_agent is None:
        raise HTTPException(status_code=503, detail="Agent henuz baslatilmadi")

    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM exchanges
           WHERE interest_level IN ('critical','interesting') AND ai_analyzed=0 AND score >= ?
           ORDER BY score DESC LIMIT 20""",
        (min_score,),
    ).fetchall()
    conn.close()

    if not rows:
        return {"status": "empty", "msg": "Kuyrukta islenecek exchange yok"}

    items = [dict(r) for r in rows]

    async def run_all():
        await broadcast("agent_batch_started", {
            "total": len(items),
            "msg": f"🤖 Toplu avlanma basladi: {len(items)} exchange",
        })
        for ex in items:
            reason = ex.get("interest_reason", "")
            matched_vulns = [r.strip() for r in reason.split(",") if r.strip()] or ["unknown"]
            await autonomous_agent.hunt(ex, matched_vulns, broadcast)
            await asyncio.sleep(1)
        await broadcast("agent_batch_complete", {
            "total": len(items),
            "msg": f"✅ Toplu avlanma tamamlandi: {len(items)} exchange islendi",
        })

    background_tasks.add_task(run_all)
    return {"status": "batch_started", "total": len(items),
            "msg": f"🤖 {len(items)} exchange icin agent baslatildi"}


@router.get("/status")
async def agent_status():
    """Agent durumu ve istatistikleri."""
    from app.modules.agent_loop import autonomous_agent
    conn = get_db()
    total_ex = conn.execute("SELECT COUNT(*) FROM exchanges").fetchone()[0]
    confirmed = conn.execute("SELECT COUNT(*) FROM exchanges WHERE interest_level='confirmed'").fetchone()[0]
    critical = conn.execute("SELECT COUNT(*) FROM exchanges WHERE interest_level='critical' AND ai_analyzed=0").fetchone()[0]
    interesting = conn.execute("SELECT COUNT(*) FROM exchanges WHERE interest_level='interesting' AND ai_analyzed=0").fetchone()[0]
    total_findings = conn.execute("SELECT COUNT(*) FROM findings WHERE dismissed=0").fetchone()[0]
    conn.close()
    return {
        "agent_ready": autonomous_agent is not None,
        "stats": {
            "total_exchanges": total_ex, "confirmed_vulns": confirmed,
            "pending_critical": critical, "pending_interesting": interesting,
            "total_findings": total_findings,
        }
    }
