"""PoC Generator - Creates proof-of-concept code for findings."""

from __future__ import annotations
from app.core.llm_gateway import llm_gateway
from app.core.prompt_engine import get_prompt
from app.models.vulnerability import Vulnerability
from app.models.http_exchange import HttpExchange


class PoCGenerator:
    """Generates proof-of-concept code for confirmed vulnerabilities."""

    async def generate(
        self,
        vulnerability: Vulnerability,
        exchange: HttpExchange | None = None,
    ) -> dict[str, str]:
        """
        Generate PoC in multiple formats.
        Returns dict with 'curl', 'python', 'description' keys.
        """
        exchange_context = ""
        if exchange:
            exchange_context = f"""
Original Request:
{exchange.request.method} {exchange.request.url}
Headers: {', '.join(f'{h.name}: {h.value}' for h in exchange.request.headers[:10])}
Body: {exchange.request.body[:1000]}

Response: {exchange.response.status_code}
Body: {exchange.response.body[:1000]}
"""

        prompt = f"""Generate a precise, working proof-of-concept for this confirmed vulnerability:

Title: {vulnerability.title}
Type: {vulnerability.vuln_type.value}
Severity: {vulnerability.severity.value}
URL: {vulnerability.affected_url}
Parameter: {vulnerability.affected_parameter}
Description: {vulnerability.description}

{exchange_context}

ANTI-HALLUCINATION RULES FOR POC:
1. DO NOT invent parameters, headers, or endpoints. You MUST use exactly what is provided in the Original Request / Response.
2. If it is a blind or out-of-band vulnerability, clearly state where the attacker should place their Burp Collaborator / Webhook URL.
3. The python script MUST include proper error handling and timeouts.
4. Replace actual sensitive auth tokens with `[YOUR_AUTH_TOKEN_HERE]`. Keep all other parameters intact.

Generate PoC in these formats:
1. cURL command (one-liner that demonstrates the vulnerability)
2. Python script using the requests library (ready to run)
3. Step-by-step description for manual reproduction (how to test it in Burp Suite / Browser)

Respond in this JSON format ONLY (No markdown formatting around it):
{{
  "cot": "Chain of thought: I see the vulnerability uses the 'id' parameter. I will construct a curl payload injecting the sleep command...",
  "curl": "curl command here",
  "python": "import requests\\n...",
  "description": "1. Open Burp\\n2. Intercept...",
  "impact_demo": "This allows the attacker to read /etc/passwd or dump the database."
}}
"""
        system = get_prompt("poc")
        response = await llm_gateway.generate(prompt, system=system)

        try:
            import json
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except Exception:
            pass

        return {
            "curl": "",
            "python": "",
            "description": response,
            "impact_demo": "",
        }


poc_generator = PoCGenerator()
