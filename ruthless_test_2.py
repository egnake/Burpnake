import asyncio
import traceback
from app.models.http_exchange import HttpExchange, HttpRequest, HttpResponse, HttpHeader
from app.modules.passive_analyzer import triage_exchange
from app.modules.vulnerability_analyzer import vulnerability_analyzer

def run_passive_test(name, exchange_dict):
    print(f"\n[+] Passive Test: {name}")
    try:
        level, reason, params, score, matched = triage_exchange(exchange_dict)
        print(f"  -> SUCCESS (Score: {score}, Level: {level}, Matched: {matched})")
    except Exception as e:
        print(f"  -> FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()

async def main():
    print("=== STARTING RUTHLESS TESTS 2 ===")

    # 1. Integer types where strings are expected (Type Mismatch)
    run_passive_test("Integer for B64 and URL", {
        "url": 12345, "path": 6789, "method": 404, "request_b64": 99999, "response_b64": -1, "status_code": "NaN"
    })

    # 2. ReDoS attempt on SSTI logic
    run_passive_test("ReDoS SSTI attempt", {
        "url": "http://x.com", "path": "/", "method": "POST",
        "request_b64": "UE9TVCAvIEhUVFAvMS4xDQpIb3N0OiB4DQoNCnt7" + ("A" * 500000) # Ends without }}
    })

    # 3. Massive key in HPP
    run_passive_test("Massive HPP Key", {
        "url": "http://x.com/?" + ("A" * 500000) + "=1&" + ("A" * 500000) + "=2", 
        "path": "/"
    })

if __name__ == "__main__":
    asyncio.run(main())
