import base64
from app.modules.passive_analyzer import triage_exchange

def b64(text): 
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

tests = [
    ("PHP Magic Hash", "http://x.com/?t=0e12345678901234", "GET /?t=0e12345678901234 HTTP/1.1\r\nHost: x.com\r\n\r\n", ""),
    ("GraphQL Alias DoS", "http://x.com/graphql", "POST /graphql HTTP/1.1\r\n\r\n{\"query\": \"query { alias1: user { id } alias2: user { id } alias3: user { id } alias4: user { id } alias5: user { id } }\"}", ""),
    ("Cloud SSRF Alibaba", "http://x.com/", "GET / HTTP/1.1\r\nHost: 100.100.100.200\r\n\r\n", ""),
    ("WebRTC STUN", "http://x.com/", "POST / HTTP/1.1\r\n\r\nstun:192.168.1.1:3478", ""),
    ("Desync Smuggling", "http://x.com/", "POST / HTTP/1.1\r\nContent-Length: 5\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n", ""),
    ("XML XXE / SAML", "http://x.com/saml", "POST /saml HTTP/1.1\r\n\r\n<saml:Assertion xmlns:saml=\"urn:oasis:names:tc:SAML:2.0:assertion\">", ""),
]

print("=== SUITE 1: COMPREHENSIVE VULNERABILITY COVERAGE ===")
for name, url, req, res in tests:
    ex = {"url": url, "path": url, "method": req.split(" ")[0], "request_b64": b64(req), "response_b64": b64(res)}
    _, _, _, score, matched = triage_exchange(ex)
    status = "PASS" if matched else "FAIL"
    print(f"[{status}] {name} -> Score: {score} | Matched: {matched}")
