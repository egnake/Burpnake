import asyncio
from app.modules.passive_analyzer import triage_exchange

def run_passive_test(name, exchange_dict):
    print(f"\n[+] Passive Test: {name}")
    try:
        level, reason, params, score, matched = triage_exchange(exchange_dict)
        print(f"  -> SUCCESS (Score: {score}, Level: {level}, Matched: {matched})")
    except Exception as e:
        print(f"  -> FAILED: {type(e).__name__}: {e}")

async def main():
    print("=== STARTING ABYSS-TIER (FINAL) TESTS ===")

    # 1. SpEL Injection (Spring Expression Language)
    run_passive_test("SpEL Injection", {
        "url": "http://test.com", "method": "POST",
        "request_b64": "JHtfVFQoamF2YS5sYW5nLlJ1bnRpbWUpLnVudGltZSgpfQ==" # ${ T(java.lang.Runtime).untime() }
    })

    # 2. Spring Path Matrix Bypass
    run_passive_test("Path Matrix Bypass", {
        "url": "http://test.com/admin/..;/login", "method": "GET"
    })

    # 3. PHP Magic Hash (Type Juggling)
    run_passive_test("PHP Magic Hash", {
        "url": "http://test.com/?token=0e12345678901234", "method": "GET"
    })
    
    # 4. IP Spoofing (WAF/Auth Bypass)
    run_passive_test("IP Spoofing", {
        "url": "http://test.com", "method": "GET",
        "request_b64": "WC1Gb3J3YXJkZWQtRm9yOiAxMjcuMC4wLjE=" # X-Forwarded-For: 127.0.0.1
    })

if __name__ == "__main__":
    asyncio.run(main())
