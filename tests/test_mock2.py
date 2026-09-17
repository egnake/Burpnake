import asyncio
from app.models.http_exchange import HttpExchange, HttpRequest, HttpResponse, HttpHeader
from app.modules.vulnerability_analyzer import vulnerability_analyzer
import app.core.llm_gateway

# Mock the LLM gateway
async def mock_generate(prompt: str, system: str = "", **kwargs):
    print("====== SYSTEM PROMPT ======")
    print(system)
    print("\n====== USER PROMPT ======")
    print(prompt)
    print("\n=========================")
    return "MOCK_RESPONSE"

app.core.llm_gateway.llm_gateway.generate = mock_generate

async def main():
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
    
    await vulnerability_analyzer.analyze_single(exchange)

if __name__ == "__main__":
    asyncio.run(main())
