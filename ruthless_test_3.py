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
    print("=== STARTING EXTREME PAYLOAD TESTS ===")

    # 1. Python Pickle & YAML Deserialization
    run_passive_test("Python Pickle Magic Bytes", {
        "url": "http://test.com", "method": "POST",
        "request_b64": "gASV" # simulated base64 for Pickle
    })

    # 2. XSLT Injection
    run_passive_test("XSLT Injection", {
        "url": "http://test.com", "method": "POST",
        "request_b64": "PHhzbDpzdHlsZXNoZWV0IHhtbG5zOnhzbD0iaHR0cDovL3d3dy53My5vcmcvMTk5OS9YU0wvVHJhbnNmb3JtIj4=" # <xsl:stylesheet...
    })

    # 3. Mass Assignment / Auto-Binding
    run_passive_test("Mass Assignment (isAdmin: true)", {
        "url": "http://test.com", "method": "POST",
        "response_b64": "eyAiaXNBZG1pbiI6IHRydWUgfc=" # { "isAdmin": true }
    })
    
    # 4. gRPC
    run_passive_test("gRPC Endpoint", {
        "url": "http://test.com", "method": "POST",
        "request_b64": "Q29udGVudC1UeXBlOiBhcHBsaWNhdGlvbi9ncnBjLXdlYg==" # Content-Type: application/grpc-web
    })

if __name__ == "__main__":
    asyncio.run(main())
