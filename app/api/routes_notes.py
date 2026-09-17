from fastapi import APIRouter
from pydantic import BaseModel
from app.modules.database import get_db
import uuid
from datetime import datetime

router = APIRouter()


def _ensure_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            exchange_id TEXT,
            content TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


class NoteCreate(BaseModel):
    exchange_id: str
    content: str


@router.post("/")
def create_note(body: NoteCreate):
    _ensure_table()
    conn = get_db()
    nid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO notes (id, exchange_id, content, created_at) VALUES (?,?,?,?)",
        (nid, body.exchange_id, body.content, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"id": nid, "status": "created"}


@router.get("/{exchange_id}")
def list_notes(exchange_id: str):
    _ensure_table()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notes WHERE exchange_id=? ORDER BY created_at DESC", (exchange_id,)
    ).fetchall()
    conn.close()
    return {"notes": [dict(r) for r in rows]}


@router.delete("/{note_id}")
def delete_note(note_id: str):
    _ensure_table()
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}
