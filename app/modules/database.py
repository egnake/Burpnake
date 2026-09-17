"""
SQLite veritabani katmani - tum verileri kalici olarak saklar.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "burpnake.db"


def get_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            platform TEXT DEFAULT 'hackerone',
            scope_json TEXT DEFAULT '{}',
            is_active INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS exchanges (
            id TEXT PRIMARY KEY,
            program_id TEXT,
            host TEXT,
            url TEXT,
            path TEXT,
            method TEXT,
            status_code INTEGER,
            request_b64 TEXT,
            response_b64 TEXT,
            request_headers TEXT DEFAULT '{}',
            response_headers TEXT DEFAULT '{}',
            interest_level TEXT DEFAULT 'pending',
            interest_reason TEXT DEFAULT '',
            interesting_params TEXT DEFAULT '[]',
            tags TEXT DEFAULT '[]',
            score INTEGER DEFAULT 0,
            ai_analyzed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (program_id) REFERENCES programs(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS findings (
            id TEXT PRIMARY KEY,
            exchange_id TEXT,
            program_id TEXT,
            title TEXT,
            severity TEXT DEFAULT 'info',
            description TEXT,
            steps_to_test TEXT,
            impact TEXT DEFAULT '',
            cvss_score TEXT DEFAULT '',
            ai_provider TEXT,
            confirmed INTEGER DEFAULT 0,
            dismissed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (exchange_id) REFERENCES exchanges(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            role TEXT,
            content TEXT,
            exchange_ids TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized.")


# --- Exchange CRUD ---

def save_exchange(data: dict) -> str:
    conn = get_db()
    c = conn.cursor()
    eid = data.get("id") or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    c.execute("""
        INSERT OR REPLACE INTO exchanges
        (id, program_id, host, url, path, method, status_code, request_b64,
         response_b64, request_headers, response_headers, interest_level,
         interest_reason, interesting_params, tags, score, ai_analyzed, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        eid,
        data.get("program_id", ""),
        data.get("host", ""),
        data.get("url", ""),
        data.get("path", ""),
        data.get("method", "GET"),
        data.get("status_code", 0),
        data.get("request_b64", ""),
        data.get("response_b64", ""),
        json.dumps(data.get("request_headers", {})),
        json.dumps(data.get("response_headers", {})),
        data.get("interest_level", "pending"),
        data.get("interest_reason", ""),
        json.dumps(data.get("interesting_params", [])),
        json.dumps(data.get("tags", [])),
        data.get("score", 0),
        int(data.get("ai_analyzed", False)),
        now,
    ))
    conn.commit()
    conn.close()
    return eid


def get_exchanges(program_id=None, interest_level=None, limit=200):
    conn = get_db()
    c = conn.cursor()
    query = "SELECT * FROM exchanges"
    params = []
    conditions = []
    if program_id:
        conditions.append("program_id = ?")
        params.append(program_id)
    if interest_level:
        conditions.append("interest_level = ?")
        params.append(interest_level)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = c.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unanalyzed_exchanges(limit=10):
    conn = get_db()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM exchanges WHERE ai_analyzed = 0 AND interest_level != 'pending' ORDER BY score DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_exchanges(limit=20):
    conn = get_db()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM exchanges WHERE interest_level = 'pending' ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_exchange_triage(eid: str, interest_level: str, interest_reason: str,
                            interesting_params: list, score: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE exchanges
        SET interest_level=?, interest_reason=?, interesting_params=?, score=?
        WHERE id=?
    """, (interest_level, interest_reason, json.dumps(interesting_params), score, eid))
    conn.commit()
    conn.close()


def mark_exchange_analyzed(eid: str, interest_level: str, interest_reason: str):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE exchanges SET ai_analyzed=1, interest_level=?, interest_reason=? WHERE id=?",
        (interest_level, interest_reason, eid)
    )
    conn.commit()
    conn.close()


# --- Finding CRUD ---

def save_finding(data: dict) -> str:
    conn = get_db()
    c = conn.cursor()
    fid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    c.execute("""
        INSERT INTO findings
        (id, exchange_id, program_id, title, severity, description, steps_to_test,
         impact, cvss_score, ai_provider, confirmed, dismissed, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        fid,
        data.get("exchange_id", ""),
        data.get("program_id", ""),
        data.get("title", "Untitled"),
        data.get("severity", "info"),
        data.get("description", ""),
        data.get("steps_to_test", ""),
        data.get("impact", ""),
        data.get("cvss_score", ""),
        data.get("ai_provider", "unknown"),
        int(data.get("confirmed", 0)), 0,
        now,
    ))
    conn.commit()
    conn.close()
    return fid


def get_findings(program_id=None, severity=None, confirmed_only=False):
    conn = get_db()
    c = conn.cursor()
    conditions = ["dismissed = 0"]
    params = []
    if program_id:
        conditions.append("program_id = ?")
        params.append(program_id)
    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if confirmed_only:
        conditions.append("confirmed = 1")
    query = "SELECT * FROM findings WHERE " + " AND ".join(conditions) + " ORDER BY created_at DESC"
    rows = c.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats(program_id=None):
    conn = get_db()
    c = conn.cursor()

    ex_params = []
    ex_where = ""
    if program_id:
        ex_where = "WHERE program_id = ?"
        ex_params = [program_id]

    total = c.execute(f"SELECT COUNT(*) FROM exchanges {ex_where}", ex_params).fetchone()[0]
    in_scope = c.execute(
        f"SELECT COUNT(*) FROM exchanges {ex_where + ' AND' if ex_where else 'WHERE'} interest_level != 'normal'",
        ex_params
    ).fetchone()[0]
    analyzed = c.execute(
        f"SELECT COUNT(*) FROM exchanges {ex_where + ' AND' if ex_where else 'WHERE'} ai_analyzed = 1",
        ex_params
    ).fetchone()[0]

    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    rows = c.execute(
        "SELECT severity, COUNT(*) FROM findings WHERE dismissed=0 GROUP BY severity"
    ).fetchall()
    for row in rows:
        sev = (row[0] or "info").lower()
        if sev in sev_counts:
            sev_counts[sev] = row[1]

    top_ep = c.execute(
        f"SELECT path, COUNT(*) as cnt FROM exchanges {ex_where} GROUP BY path ORDER BY cnt DESC LIMIT 10",
        ex_params
    ).fetchall()

    conn.close()
    return {
        "total": total,
        "in_scope": in_scope,
        "analyzed": analyzed,
        "findings_by_severity": sev_counts,
        "top_endpoints": [{"path": r[0], "count": r[1]} for r in top_ep],
    }


# --- Program CRUD ---

def save_program(data: dict) -> str:
    conn = get_db()
    c = conn.cursor()
    pid = data.get("id") or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    c.execute("""
        INSERT OR REPLACE INTO programs (id, name, platform, scope_json, is_active, created_at)
        VALUES (?,?,?,?,?,?)
    """, (
        pid,
        data.get("name", "Unnamed"),
        data.get("platform", "hackerone"),
        json.dumps(data.get("scope", {})),
        int(data.get("is_active", 0)),
        now,
    ))
    conn.commit()
    conn.close()
    return pid


def get_programs():
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM programs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_program():
    conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT * FROM programs WHERE is_active=1 LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


def activate_program(pid: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE programs SET is_active=0")
    c.execute("UPDATE programs SET is_active=1 WHERE id=?", (pid,))
    conn.commit()
    conn.close()


# --- Chat CRUD ---

def save_message(session_id: str, role: str, content: str, exchange_ids: list = None):
    conn = get_db()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("""
        INSERT INTO chat_messages (id, session_id, role, content, exchange_ids, created_at)
        VALUES (?,?,?,?,?,?)
    """, (str(uuid.uuid4()), session_id, role, content, json.dumps(exchange_ids or []), now))
    conn.commit()
    conn.close()


def get_chat_history(session_id: str):
    conn = get_db()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM chat_messages WHERE session_id=? ORDER BY created_at ASC", (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
