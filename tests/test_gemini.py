import asyncio
from app.models.http_exchange import HttpExchange, HttpRequest, HttpResponse, HttpHeader
from app.modules.vulnerability_analyzer import vulnerability_analyzer
import app.core.llm_gateway
from app.config import settings

# Force gemini testing mode if we have api key
import google.generativeai as genai
import os

async def main():
    if not settings.GEMINI_API_KEY and not os.getenv("GEMINI_API_KEY"):
        print("MOCKING GEMINI RESPONSE (No API key found)")
        print("\n=== SYSTEM PROMPT ===")
        from app.core.prompt_engine import get_prompt
        print(get_prompt("analyzer"))
        print("\n=== USER PROMPT ===")
        req = HttpRequest(
            method="POST",
            url="https://api.target.com/api/v2/document/export",
            path="/api/v2/document/export",
            host="api.target.com",
            protocol="https",
            port=443,
            headers=[
                HttpHeader(name="Host", value="api.target.com"),
                HttpHeader(name="Content-Type", value="application/json"),
                HttpHeader(name="Authorization", value="Bearer eyJ..."),
            ],
            body='{\n  "doc_id": "789",\n  "format": "pdf",\n  "options": {\n    "margin": "1cm",\n    "headerTemplate": "<h1>Draft</h1>"\n  }\n}',
            raw='POST /api/v2/document/export HTTP/1.1\r\nHost: api.target.com\r\nContent-Type: application/json\r\nAuthorization: Bearer eyJ...\r\n\r\n{\n  "doc_id": "789",\n  "format": "pdf",\n  "options": {\n    "margin": "1cm",\n    "headerTemplate": "<h1>Draft</h1>"\n  }\n}'
        )
        resp = HttpResponse(
            status_code=500,
            status_text="Internal Server Error",
            headers=[
                HttpHeader(name="Content-Type", value="application/json"),
                HttpHeader(name="X-Powered-By", value="Express"),
            ],
            body='{\n  "error": "Generation failed",\n  "details": "Error: Failed to launch chrome!\\n[1105/103412.123:ERROR:zygote_host_impl_linux.cc(90)] Running as root without --no-sandbox is not supported."\n}',
            raw='HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\n\r\n{\n  "error": "Generation failed",\n  "details": "Error: Failed to launch chrome!\\n[1105/103412.123:ERROR:zygote_host_impl_linux.cc(90)] Running as root without --no-sandbox is not supported."\n}',
            content_type="application/json",
            content_length=150
        )
        exchange = HttpExchange(id=999, request=req, response=resp)
        prompt = f"""Perform a deep security analysis of this HTTP exchange.

REQUEST:
{exchange.request.raw}

RESPONSE:
{exchange.response.raw}

Provide:
1. Deep Chain-of-Thought (CoT) Analysis: Walk through your thought process. What does the response body tell you? Did you get an error? What does the status code imply? For example, "I see the response body reflects our input, but the angle brackets are HTML-encoded, so XSS is unlikely here. However, wait, in the JSON response, the input is unescaped..."
2. Identified vulnerabilities or suspicious patterns based on your analysis
3. Specific parameters to test
4. Exact payloads to try (Provide Plan A, Plan B, and Plan C for creative fallbacks like Unicode manipulation, Request Smuggling, etc.)
5. Actionable Next Steps:
   - Provide the exact `curl` command.
   - If dynamic modification is needed, provide Burp Suite Match and Replace rules.
   - If automation is needed (e.g. race condition, fuzzing), provide a short Python `requests` script.
6. Expected behavior if vulnerable
7. Impact assessment
"""
        print(prompt)
        print("\n\nTest successfully generated prompts.")
        return

if __name__ == "__main__":
    asyncio.run(main())
