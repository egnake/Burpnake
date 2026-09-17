import asyncio
import os
from app.models.http_exchange import HttpExchange, HttpRequest, HttpResponse, HttpHeader
from app.modules.vulnerability_analyzer import vulnerability_analyzer
from app.core.llm_gateway import llm_gateway

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
    
    print("Sending mock exchange to analyzer...")
    result = await vulnerability_analyzer.analyze_single(exchange)
    
    print("=== AI RESPONSE ===")
    print(result)
    
    await llm_gateway.close()

if __name__ == "__main__":
    asyncio.run(main())
