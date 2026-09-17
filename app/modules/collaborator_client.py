"""
Collaborator Client — Out-of-Band (OOB) callback altyapisi.
"""
import asyncio
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

import httpx

logger = logging.getLogger("burpnake.collaborator")

@dataclass
class OOBCallback:
    callback_id: str
    protocol: str
    source_ip: str
    timestamp: float
    raw_data: str
    finding_context: str

@dataclass 
class CollaboratorSession:
    session_id: str
    subdomain: str
    full_url: str
    dns_host: str
    created_at: float
    context: str
    callbacks: List[OOBCallback] = field(default_factory=list)
    has_interaction: bool = False

class CollaboratorClient:
    def __init__(self, server: str = "oast.fun", token: str = ""):
        self.server = server
        self.token = token
        self._sessions: Dict[str, CollaboratorSession] = {}
        self._client: Optional[httpx.AsyncClient] = None
        self._polling = False
        self._poll_task: Optional[asyncio.Task] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0))
        return self._client
    
    def generate_payload(self, context: str = "") -> CollaboratorSession:
        session_id = secrets.token_hex(8)
        unique_part = hashlib.md5(f"{session_id}{time.time()}".encode()).hexdigest()[:12]
        subdomain = f"{unique_part}.{self.server}"
        
        session = CollaboratorSession(
            session_id=session_id,
            subdomain=subdomain,
            full_url=f"http://{subdomain}",
            dns_host=subdomain,
            created_at=time.time(),
            context=context,
        )
        self._sessions[session_id] = session
        logger.info(f"[Collaborator] Payload generated: {subdomain} for '{context}'")
        return session

    async def start_polling(self, interval: int = 15):
        pass

    async def stop_polling(self):
        pass

    async def close(self):
        await self.stop_polling()
        if self._client and not self._client.is_closed:
            await self._client.aclose()

collaborator_client = CollaboratorClient()
