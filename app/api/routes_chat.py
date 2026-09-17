"""Interactive chat API routes."""

from fastapi import APIRouter
from pydantic import BaseModel
from app.modules.interactive_hunter import interactive_hunter

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str = ""
    message: str
    exchange_ids: list[int] | None = None


@router.post("/send")
async def send_message(req: ChatRequest):
    """Send a message in the hunting chat session."""
    session_id = req.session_id or interactive_hunter.new_session()
    response = await interactive_hunter.chat(
        session_id=session_id,
        message=req.message,
        exchange_ids=req.exchange_ids,
    )
    return {
        "session_id": session_id,
        "response": response,
    }


@router.post("/auto-analyze")
async def auto_analyze(session_id: str = ""):
    """Start auto-analysis of imported exchanges."""
    sid = session_id or interactive_hunter.new_session()
    response = await interactive_hunter.auto_analyze(sid)
    return {
        "session_id": sid,
        "response": response,
    }


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat session history."""
    history = interactive_hunter.get_session_history(session_id)
    return {"session_id": session_id, "messages": history}


@router.get("/sessions")
async def list_sessions():
    """List all hunting sessions."""
    return {"sessions": interactive_hunter.list_sessions()}


@router.post("/new-session")
async def new_session():
    """Create a new hunting session."""
    sid = interactive_hunter.new_session()
    return {"session_id": sid}
