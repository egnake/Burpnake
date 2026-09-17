"""Interactive AI Hunter - Chat-based vulnerability hunting."""

from __future__ import annotations
from datetime import datetime
from app.core.llm_gateway import llm_gateway
from app.core.prompt_engine import get_prompt
from app.models.http_exchange import HttpExchange
from app.modules.burp_importer import burp_importer
from app.modules.scope_manager import scope_manager


class InteractiveHunter:
    """
    Interactive chat-based vulnerability hunting assistant.
    Maintains conversation context and guides the user through testing.
    """

    def __init__(self):
        self.conversations: dict[str, list[dict[str, str]]] = {}

    def new_session(self, session_id: str | None = None) -> str:
        """Start a new hunting session."""
        sid = session_id or datetime.now().strftime("hunt_%Y%m%d_%H%M%S")
        self.conversations[sid] = [
            {"role": "system", "content": get_prompt("hunter")}
        ]
        return sid

    async def chat(
        self,
        session_id: str,
        message: str,
        exchange_ids: list[int] | None = None,
    ) -> str:
        """
        Send a message in the hunting session.
        Optionally attach specific HTTP exchanges by ID.
        """
        if session_id not in self.conversations:
            session_id = self.new_session(session_id)

        # Build context with exchange data if referenced
        full_message = message
        if exchange_ids:
            exchange_data = []
            for eid in exchange_ids:
                ex = burp_importer.get_exchange(eid)
                if ex:
                    exchange_data.append(self._format_exchange(ex))
            if exchange_data:
                full_message += "\n\n--- Attached HTTP Exchanges ---\n"
                full_message += "\n---\n".join(exchange_data)

        # Add scope context on first real message
        if len(self.conversations[session_id]) <= 2:
            scope_info = scope_manager.get_scope_summary()
            import_info = burp_importer.get_summary()
            context = f"""
[Session Context]
Scope: {scope_info}
Imported Data: {import_info.get('total_exchanges', 0)} exchanges, 
Methods: {import_info.get('methods', {})}, 
Hosts: {import_info.get('unique_hosts', [])}

Available exchange IDs: {[e.id for e in burp_importer.exchanges[:50]]}
"""
            self.conversations[session_id].append(
                {"role": "system", "content": context}
            )

        # Add user message
        self.conversations[session_id].append(
            {"role": "user", "content": full_message}
        )

        # Get AI response
        response = await llm_gateway.chat(
            self.conversations[session_id],
            temperature=0.4,
        )

        # Store response
        self.conversations[session_id].append(
            {"role": "assistant", "content": response}
        )

        return response

    async def auto_analyze(self, session_id: str) -> str:
        """
        Auto-analyze all imported exchanges and start hunting.
        This is the initial analysis that identifies promising targets.
        """
        if session_id not in self.conversations:
            session_id = self.new_session(session_id)

        exchanges = burp_importer.exchanges
        if not exchanges:
            return "No exchanges imported yet. Please import Burp data first."

        # Build summary of all exchanges
        summaries = [ex.summary for ex in exchanges[:100]]
        exchange_list = "\n".join(summaries)

        message = f"""I've imported {len(exchanges)} HTTP exchanges. Here's the overview:

{exchange_list}

Please analyze these exchanges. Before answering, walk through your thought process (Chain-of-Thought) for each interesting item. "Ah, I see #5 returns a 500 error on a search endpoint, which might indicate SQLi..."

Identify and explain:
1. Top 5 most promising targets for vulnerability testing
2. For each, explain what vulnerability type might exist and why (based on your CoT analysis)
3. Which exchange should we investigate first?
4. What specific request/response data do you need me to send?
5. Provide the exact `curl` command or next step for the first target you want to investigate.

Focus on HIGH and CRITICAL severity vulnerabilities only."""

        return await self.chat(session_id, message)

    def _format_exchange(self, ex: HttpExchange) -> str:
        """Format an exchange for the AI context."""
        req = ex.request
        resp = ex.response

        # Rebuild raw request if not available
        req_text = req.raw
        if not req_text:
            lines = [f"{req.method} {req.path} {req.http_version}"]
            lines.append(f"Host: {req.host}")
            for h in req.headers:
                lines.append(f"{h.name}: {h.value}")
            if req.body:
                lines.append("")
                lines.append(req.body)
            req_text = "\n".join(lines)

        resp_text = resp.raw
        if not resp_text:
            lines = [f"{resp.http_version} {resp.status_code} {resp.status_text}"]
            for h in resp.headers:
                lines.append(f"{h.name}: {h.value}")
            if resp.body:
                lines.append("")
                lines.append(resp.body[:3000])
            resp_text = "\n".join(lines)

        return f"""=== Exchange #{ex.id} ===
--- REQUEST ---
{req_text}

--- RESPONSE ---
{resp_text}
"""

    def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        """Get conversation history (excluding system messages)."""
        if session_id not in self.conversations:
            return []
        return [
            msg for msg in self.conversations[session_id]
            if msg["role"] != "system"
        ]

    def list_sessions(self) -> list[str]:
        return list(self.conversations.keys())


# Singleton
interactive_hunter = InteractiveHunter()
