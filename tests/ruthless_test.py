import asyncio
import traceback
from app.models.http_exchange import HttpExchange, HttpRequest, HttpResponse, HttpHeader
from app.modules.passive_analyzer import triage_exchange
from app.modules.vulnerability_analyzer import vulnerability_analyzer
import app.core.llm_gateway

# Mock LLM to focus on logic/parsing errors
async def mock_generate(prompt: str, system: str = "", **kwargs):
    return "MOCK_RESPONSE"
app.core.llm_gateway.llm_gateway.generate = mock_generate

def run_passive_test(name, exchange_dict):
    print(f"\n[+] Passive Test: {name}")
    try:
        level, reason, params, score, matched = triage_exchange(exchange_dict)
        print(f"  -> SUCCESS (Score: {score}, Level: {level}, Matched: {matched})")
    except Exception as e:
        print(f"  -> FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()

async def run_active_test(name, req, resp):
    print(f"\n[+] Active Test: {name}")
    try:
        ex = HttpExchange(id=1, request=req, response=resp)
        # Mocking the raw properties to ensure _rebuild_request is triggered
        ex.request.raw = ""
        ex.response.raw = ""
        await vulnerability_analyzer.analyze_single(ex)
        print(f"  -> SUCCESS")
    except Exception as e:
        print(f"  -> FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()

async def main():
    print("=== STARTING RUTHLESS TESTS ===")

    # 1. Passive: None Values
    run_passive_test("Completely Empty/None Exchange", {
        "url": None, "path": None, "method": None, "request_b64": None, "response_b64": None
    })

    # 2. Passive: Malformed URL & JSON Body (HPP logic break check)
    run_passive_test("JSON Body in HPP check", {
        "url": "https://test.com", "path": "/api", "method": "POST",
        "request_b64": "UE9TVCAvYXBpIEhUVFAvMS4xDQpIb3N0OiB0ZXN0LmNvbQ0KDQp7ImlkIjogMSwgInRlc3QiOiB0cnVlfQ==",
        "response_b64": ""
    })
    
    # 3. Active: Pydantic safe defaults instead of strict None
    req = HttpRequest(method="GET", url="http://x", path="/", host="x", protocol="http", port=80, headers=[], body="", raw="")
    resp = HttpResponse(status_code=200, status_text="OK", headers=[], body="", raw="", content_type="", content_length=0)
    await run_active_test("Empty Headers & Body", req, resp)

    # 4. Active: Binary Data in Body (Decoding issue check)
    req2 = HttpRequest(method="POST", url="http://x", path="/", host="x", protocol="http", port=80, headers=[], body="\x00\x01\x02\xff\xfe", raw="")
    resp2 = HttpResponse(status_code=200, status_text="OK", headers=[], body="\x89PNG\r\n\x1a\n", raw="", content_type="image/png", content_length=0)
    await run_active_test("Binary Body Data", req2, resp2)

if __name__ == "__main__":
    asyncio.run(main())
