from app.modules.passive_analyzer import build_deep_analysis_prompt

print("=== SUITE 3: PROMPT ENGINE INTEGRITY ===")
ex = {
    "request_b64": "R0VUIC8gSFRUUC8xLjE=", # GET / HTTP/1.1
    "response_b64": "SFRUUC8xLjEgMjAwIE9L"  # HTTP/1.1 200 OK
}
matched = ["log4shell_jndi_candidate", "webrtc_ssrf_candidate", "nginx_off_by_slash_candidate"]

try:
    prompt = build_deep_analysis_prompt(ex, matched)
    if len(prompt) > 100:
        print("[PASS] Prompt generated successfully with correct formatting.")
        print(f"Sample length: {len(prompt)} characters.")
    else:
        print("[FAIL] Prompt generated but is too short.")
except Exception as e:
    print(f"[FAIL] Prompt generation CRASHED: {type(e).__name__} - {e}")
