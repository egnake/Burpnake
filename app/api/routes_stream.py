from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.modules.event_broadcaster import event_stream

router = APIRouter()


@router.get("/stream")
async def sse_stream():
    """
    Server-Sent Events endpoint.
    Frontend buraya baglanir ve backend'den anlık bildirimler alir.
    """
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
