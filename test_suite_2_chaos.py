import base64
from app.modules.passive_analyzer import triage_exchange

print("=== SUITE 2: CHAOS & RESILIENCE TESTS ===")
chaos_cases = [
    ("Invalid Base64", {"url": "http://x.com", "request_b64": "!!!not_base64!!!"}),
    ("Null Bytes Everywhere", {"url": "http://x.com/\x00\x00", "request_b64": base64.b64encode(b"\x00" * 1000).decode('utf-8')}),
    ("Extremely Long URL", {"url": "http://x.com/" + ("A" * 100000)}),
    ("Missing Everything", {}),
    ("Unicode/Emojis", {"url": "http://x.com/??", "request_b64": base64.b64encode("??????".encode('utf-8')).decode('utf-8')}),
    ("Integer Overflows", {"url": 9999999999999999999999999999999999999, "status_code": 999999999999999999999})
]

for name, ex in chaos_cases:
    try:
        triage_exchange(ex)
        print(f"[PASS] {name} handled safely without crash.")
    except Exception as e:
        print(f"[FAIL] {name} CRASHED: {type(e).__name__} - {e}")
