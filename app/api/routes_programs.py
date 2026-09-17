from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import json

from app.modules.database import (
    get_programs, save_program, get_db, activate_program
)
from app.modules.scope_fetcher import fetch_hackerone_scope

router = APIRouter()


class ProgramCreate(BaseModel):
    name: str
    platform: str = "hackerone"
    include_domains: list = []
    exclude_domains: list = []


@router.get("/")
def list_programs():
    return {"programs": get_programs()}


@router.post("/")
def create_program(body: ProgramCreate):
    pid = save_program({
        "name": body.name,
        "platform": body.platform,
        "scope": {
            "include": body.include_domains,
            "exclude": body.exclude_domains,
        },
    })
    return {"id": pid, "status": "created"}


@router.post("/fetch-hackerone")
async def fetch_h1(handle: str):
    try:
        result = await fetch_hackerone_scope(handle)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-bugcrowd")
async def fetch_bugcrowd(handle: str):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://bugcrowd.com/{handle}.json",
                headers={"User-Agent": "Mozilla/5.0 BurpNake/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        targets = data.get("targets", {}).get("in_scope", [])
        out_targets = data.get("targets", {}).get("out_of_scope", [])

        include = [t.get("target", "") for t in targets if t.get("target")]
        exclude = [t.get("target", "") for t in out_targets if t.get("target")]

        scope = {"include": include, "exclude": exclude, "all_in_scope": targets}
        pid = save_program({
            "name": data.get("name", handle),
            "platform": "bugcrowd",
            "scope": scope,
        })
        return {"program_id": pid, "name": data.get("name", handle), "scope": scope}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bugcrowd fetch failed: {e}")


@router.get("/{pid}")
def get_program(pid: str):
    conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT * FROM programs WHERE id=?", (pid,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Program not found")
    return dict(row)


@router.put("/{pid}/activate")
def set_active_program(pid: str):
    activate_program(pid)
    return {"status": "activated", "program_id": pid}


@router.delete("/{pid}")
def delete_program(pid: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM programs WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}
