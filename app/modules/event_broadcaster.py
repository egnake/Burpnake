"""
Gercek zamanli event broadcaster.
SSE (Server-Sent Events) ile frontend'e aninda bildirim gonderir.
"""
import asyncio
import json
from typing import AsyncGenerator
from datetime import datetime

# Global event queue - tum SSE baglantilari bunu dinler
_subscribers: list[asyncio.Queue] = []


async def broadcast(event_type: str, data: dict):
    """Tum bagli frontend'lere event gonder."""
    payload = {
        "type": event_type,
        "data": data,
        "ts": datetime.utcnow().isoformat(),
    }
    dead = []
    for q in _subscribers:
        try:
            await q.put(payload)
        except Exception:
            dead.append(q)
    for q in dead:
        _subscribers.remove(q)


async def event_stream() -> AsyncGenerator[str, None]:
    """SSE stream generator - her baglanan client icin ayri queue."""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(q)
    try:
        # Baglanti mesaji
        yield f"data: {json.dumps({'type': 'connected', 'data': {'msg': 'BurpNake stream baglandi'}})}\n\n"
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=25)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Keepalive ping
                yield ": ping\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        if q in _subscribers:
            _subscribers.remove(q)
