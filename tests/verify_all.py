"""
BurpNake Comprehensive Verification Suite
Runs end-to-end deterministic verification of all functional modules and APIs.
"""
import sys
import os
import json
import base64

# Force unbuffered output
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.modules.database import init_db, get_db, save_exchange, get_exchanges, save_finding, get_findings
from app.modules.passive_analyzer import triage_exchange
from app.modules.chain_builder import chain_builder

def test_suite():
    print("=" * 60)
    print("  BURPNAKE END-TO-END VERIFICATION SUITE")
    print("=" * 60)
    
    passed = 0
    failed = 0

    def check(name: str, condition: bool, extra: str = ""):
        nonlocal passed, failed
        if condition:
            print(f" [PASS] {name}")
            passed += 1
        else:
            print(f" [FAIL] {name} -> {extra}")
            failed += 1

    # 1. Database Init
    print("\n1. Database Operations:")
    try:
        init_db()
        conn = get_db()
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        check("DB Tables Created", all(t in tables for t in ["programs", "exchanges", "findings", "chat_messages"]))
    except Exception as e:
        check("DB Tables Created", False, str(e))

    # 2. Database CRUD
    try:
        dummy_req = {"url": "https://test.com/api", "method": "GET", "request_b64": base64.b64encode(b"GET /api HTTP/1.1\r\nHost: test.com\r\n\r\n").decode(), "response_b64": base64.b64encode(b"HTTP/1.1 200 OK\r\n\r\n{}").decode(), "status_code": 200}
        eid = save_exchange(dummy_req)
        check("Save Exchange to DB", bool(eid))
        exs = get_exchanges(limit=5)
        check("Retrieve Exchanges from DB", len(exs) > 0)
        
        fid = save_finding({"title": "Test SQLi", "severity": "critical", "interest_reason": "sqli_candidate", "exchange_id": eid})
        check("Save Finding to DB", bool(fid))
        findings = get_findings()
        check("Retrieve Findings from DB", len(findings) > 0)
    except Exception as e:
        check("Database CRUD", False, str(e))

    # 3. FastAPI Client Tests
    print("\n2. Core API Endpoints:")
    with TestClient(app) as client:
        # Health & Root
        r = client.get("/health")
        check("GET /health -> 200", r.status_code == 200 and r.json().get("status") == "healthy")

        r = client.get("/")
        check("GET / -> 200", r.status_code == 200 and r.json().get("app") == "BurpNake")

        # Scope Endpoints
        r = client.post("/api/scope/set", json={
            "program_name": "BugBountyProd",
            "include_domains": ["api.target.com", "*.target.com"],
            "exclude_domains": ["out-of-scope.target.com"]
        })
        check("POST /api/scope/set -> 200", r.status_code == 200)

        r_in = client.post("/api/scope/check", json={"url": "https://api.target.com/v1/auth"})
        r_out = client.post("/api/scope/check", json={"url": "https://out-of-scope.target.com/test"})
        r_sub = client.post("/api/scope/check", json={"url": "https://billing.target.com/pay"})
        check("Scope Check: Included Domain", r_in.json().get("in_scope") is True)
        check("Scope Check: Excluded Domain", r_out.json().get("in_scope") is False)
        check("Scope Check: Wildcard Subdomain", r_sub.json().get("in_scope") is True)

        # Raw HTTP Import
        raw_req = "POST /api/v1/checkout HTTP/1.1\r\nHost: api.target.com\r\nContent-Type: application/json\r\n\r\n{\"amount\": 100}"
        raw_res = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\": \"paid\"}"
        r_imp = client.post("/api/import/raw", json={"request": raw_req, "response": raw_res})
        check("POST /api/import/raw -> 200", r_imp.status_code == 200 and "exchange_id" in r_imp.json())

        # Repeater Endpoint
        r_rep = client.post("/api/replay/send", json={
            "url": "https://httpbin.org/status/200",
            "method": "GET"
        })
        check("POST /api/replay/send -> Handled without crash", r_rep.status_code in [200, 502, 504])

        # Chain Builder API
        r_chain = client.get("/api/chains/analyze")
        check("GET /api/chains/analyze -> 200", r_chain.status_code == 200 and "chains" in r_chain.json())

        # Findings CRUD API
        r_findings = client.get("/api/findings/")
        check("GET /api/findings/ -> 200", r_findings.status_code == 200 and "findings" in r_findings.json())

        # CVSS Calculation API
        r_cvss = client.post("/api/cvss/calculate", json={"av": "N", "ac": "L", "pr": "N", "ui": "N", "s": "U", "c": "H", "i": "H", "a": "H"})
        check("POST /api/cvss/calculate -> 9.8 Critical", r_cvss.status_code == 200 and r_cvss.json().get("base_score") == 9.8 and r_cvss.json().get("severity") == "Critical")

        # CVSS Suggestion API
        r_sug = client.get("/api/cvss/suggest/sqli")
        check("GET /api/cvss/suggest/sqli -> 200", r_sug.status_code == 200 and "suggested_vector" in r_sug.json())

        # Remediation Blueprint API
        r_rem = client.get("/api/cvss/remediation/idor")
        check("GET /api/cvss/remediation/idor -> CWE-639", r_rem.status_code == 200 and r_rem.json().get("cwe_id") == "CWE-639")

        # Multi-Platform Report Engine
        import asyncio
        from app.modules.report_generator import generate_report
        test_finding = {
            "id": fid,
            "title": "Critical SQLi",
            "severity": "critical",
            "description": "SQL injection in search",
            "impact": "Full database takeover and unauthorized access to customer records.",
            "interest_reason": "sqli"
        }
        rep_h1 = asyncio.run(generate_report(test_finding, dummy_req, platform="hackerone"))
        rep_sarif = asyncio.run(generate_report(test_finding, dummy_req, platform="sarif"))
        rep_intigriti = asyncio.run(generate_report(test_finding, dummy_req, platform="intigriti"))

        check("Report Generator: HackerOne Format (CWE & CVSS)", "Vulnerability Classification" in rep_h1 and "CWE-89" in rep_h1)
        check("Report Generator: Intigriti Format", "CVSS v3.1 Score" in rep_intigriti and "CWE-89" in rep_intigriti)
        check("Report Generator: SARIF 2.1.0 Export (JSON Schema)", "2.1.0" in rep_sarif and "CWE-89" in rep_sarif)

    # 4. Chain Builder Logic Verification
    print("\n3. Vulnerability Chaining Logic:")
    sample_findings = [
        {"title": "Open Redirect Found", "interest_reason": "open_redirect"},
        {"title": "OAuth Missing State", "interest_reason": "oauth_csrf_missing_state"},
    ]
    chains = chain_builder.analyze_chains(sample_findings)
    check("Chain Detection: OAuth Takeover (Open Redirect + Missing State)", any(c.name == "OAuth Account Takeover" for c in chains))

    # 5. Passive Analyzer Rules
    print("\n4. Passive Analyzer Triage Engine:")
    tests_triage = [
        ("SQLi in Query", {"url": "http://x.com/?id=1' OR '1'='1", "request_b64": base64.b64encode(b"GET /?id=1'%20OR%20'1'='1 HTTP/1.1\r\nHost: x.com\r\n\r\n").decode(), "response_b64": ""}, "sql_injection_candidate"),
        ("XSS in Query", {"url": "http://x.com/?q=<script>alert(1)</script>", "request_b64": base64.b64encode(b"GET /?q=<script>alert(1)</script> HTTP/1.1\r\nHost: x.com\r\n\r\n").decode(), "response_b64": ""}, "xss_candidate"),
        ("AWS Metadata SSRF", {"url": "http://x.com/?url=http://169.254.169.254/latest/meta-data/", "request_b64": "", "response_b64": ""}, "cloud_metadata_ssrf_candidate"),
        ("Debug Info Disclosure", {"url": "http://x.com/debug", "request_b64": "", "response_b64": base64.b64encode(b"HTTP/1.1 500 Error\r\n\r\nTraceback (most recent call last):\r\n  File app.py, line 42").decode()}, "debug_info_disclosure"),
        ("Insecure Cookie Missing Flags", {"url": "http://x.com/login", "request_b64": "", "response_b64": base64.b64encode(b"HTTP/1.1 200 OK\r\nSet-Cookie: session=abc123\r\n\r\n").decode()}, "insecure_cookie"),
        ("Missing Security Headers", {"url": "http://x.com/", "request_b64": "", "response_b64": base64.b64encode(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html>OK</html>").decode(), "status_code": 200}, "missing_security_headers"),
    ]

    for name, ex_data, expected_tag in tests_triage:
        _, _, _, score, matched = triage_exchange(ex_data)
        has_tag = any(expected_tag in m for m in matched)
        check(f"Triage: {name} (matched={matched})", has_tag)

    print("\n" + "=" * 60)
    print(f"VERIFICATION SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    return failed == 0

if __name__ == "__main__":
    success = test_suite()
    sys.exit(0 if success else 1)
