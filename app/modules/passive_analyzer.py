"""
Gelistirilmis Pasif Trafik Analisti (Proactive + Contextual AI).
Sadece regex ile degil, LLM'i arkaplanda baglam (context) analizi icin kullanir.
Isteklerin response'larindan cikarimlar yapar (error analizi, state degisimi, sızıntı).
"""
import asyncio
from app.modules.dom_analyzer import dom_analyzer
import base64
import json
import re
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

from app.modules.database import (
    get_pending_exchanges, update_exchange_triage,
    get_unanalyzed_exchanges, mark_exchange_analyzed, save_finding, get_db
)

RULES = {
    "idor_candidate":           80,
    "sensitive_data_exposure":  90,
    "mass_assignment":          70,
    "auth_anomaly":             65,
    "open_redirect":            55,
    "sqli_candidate":           85,
    "xss_candidate":            60,
    "ssrf_candidate":           75,
    "lfi_candidate":            85,
    "rce_candidate":            95,
    "xxe_candidate":            85,
    "ssti_candidate":           80,
    "deserialization_candidate": 90,
    "crlf_injection":           60,
    "cors_misconfig":           45,
    "rate_limit_missing":       40,
    "interesting_param":        25,
    "jwt_detected":             30,
    "graphql_detected":         45,
    "file_upload":              55,
}

INTEREST_THRESHOLD = {"critical": 85, "interesting": 45, "low": 20}

IDOR_PATTERNS = [
    r"/(\d{4,})",
    r"[?&](id|user_id|uid|account_id|order_id|invoice_id|record_id|item_id|doc_id)=(\d+)",
]
SENSITIVE_PATTERNS = [
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}',
    r'\b\d{3}-\d{2}-\d{4}\b',
    r'(?i)(password|passwd|secret|api_key|access_token|private_key)\s*[=:]\s*["\']?\S+',
    r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
]
REDIRECT_PARAMS = ["redirect","return","next","callback","continue","dest","destination","redir","redirect_uri","returnTo"]
SQLI_PATTERNS = [r"['\";].*(?:OR|AND)\s+[\d'\"]", r"(?i)(UNION\s+SELECT|DROP\s+TABLE|WAITFOR\s+DELAY)", r"--\s*$"]
XSS_PATTERNS  = [r"<script[^>]*>", r"javascript:", r"onerror\s*=", r"onload\s*="]
MASS_ASSIGN   = ["admin","is_admin","role","roles","permission","permissions","superuser","staff","verified","approved"]
SSRF_PATTERNS = [r"(http|https|ftp)://(?:localhost|127\.|169\.254\.|10\.|192\.168\.)", r"[?&](url|endpoint|host|server|target)=https?://"]
LFI_PATTERNS  = [r"(?i)(?:\.\./|\.\.\\|/etc/passwd|/windows/win\.ini)"]
RCE_PATTERNS  = [r"(?i)(?:;|\|\||&&|\$\(|\`)\s*(?:ls|id|whoami|ping|curl|wget|nc)"]
SSTI_PATTERNS = [r"(?i)(?:\{\{|\{\%|\$\{|<%|<%=).*(?:%\}|\}\}|%>)"]
DESER_PATTERNS = [r"(?i)(?:rO0AB|Tzo|a:[0-9]+:\{)"]
SMUGGLING_PATTERNS = [r"(?i)Transfer-Encoding:\s*chunked", r"(?i)Content-Length:\s*\d+.*\r\nTransfer-Encoding:"]
CACHE_POISON_PATTERNS = [r"(?i)X-Forwarded-Host|X-Forwarded-Scheme|X-Rewrite-URL|X-Original-URL"]
GRAPHQL_PATTERNS = [r"(?i)__schema", r"(?i)__type", r"(?i)IntrospectionQuery", r"(?i)query\s*\{", r"(?i)mutation\s*\{"]
JWT_VULN_PATTERNS = [r"(?i)eyJhbGciOiJub25lIiw", r"(?i)eyJhbGciOiJub25lIn0", r"(?i)eyJhbGciOiJIUzI1NiJ9\."]  # alg: none or suspicious downgrade
OAUTH_PATTERNS = [r"(?i)response_type=(?:token|code)", r"(?i)client_id=[^&]+", r"(?i)redirect_uri=[^&]+"]
PROTO_POLLUTION_PATTERNS = [r"(?i)__proto__", r"(?i)constructor(?:\[|\.)prototype"]
CLOUD_SSRF_PATTERNS = [r"169\.254\.169\.254", r"(?i)metadata\.google\.internal", r"(?i)InstanceMetadata", r"100\.100\.100\.200"] # Added Alibaba
SAML_PATTERNS = [r"(?i)SAMLResponse=", r"(?i)<saml:Assertion"]
ESI_PATTERNS = [r"(?i)<esi:include", r"(?i)<!--#include"]
JSONP_PATTERNS = [r"(?i)[?&]callback=[a-zA-Z0-9_]+", r"(?i)[?&]jsonp=[a-zA-Z0-9_]+"]
XSLT_PATTERNS = [r"(?i)<xsl:stylesheet", r"(?i)<xsl:template"]
GRPC_PATTERNS = [r"(?i)application/grpc", r"(?i)application/grpc-web"]
MASS_ASSIGNMENT_CANDIDATE = [r"(?i)\"(?:is_admin|role|permissions|isAdmin|superuser)\"\s*:\s*(?:true|\"admin\")"]
NGINX_OFF_BY_SLASH = [r"/[a-zA-Z0-9_-]+/[.]{2}/"]
WEBSOCKET_UPGRADE = [r"(?i)Upgrade:\s*websocket", r"(?i)Connection:\s*Upgrade"]
LLM_INJECTION = [r"(?i)<\|system\|>", r"(?i)Ignore all previous instructions", r"(?i)You are now", r"(?i)system prompt"]
PDF_GENERATOR_SIGS = [r"(?i)wkhtmltopdf", r"(?i)puppeteer", r"(?i)headlesschrome", r"(?i)application/pdf"]
JNDI_PATTERNS = [r"(?i)\$\{jndi:(?:ldap|rmi|dns|iiop|http)"]
ACTUATOR_PATTERNS = [r"(?i)/actuator/(?:env|heapdump|gateway|routes)", r"(?i)/env", r"(?i)/heapdump"]
NOSQLI_PATTERNS = [r"\{\s*\"\$gt\"\s*:", r"\{\s*\"\$ne\"\s*:"]
WEBRTC_SSRF_PATTERNS = [r"(?i)stun:[^:]+:\d+", r"(?i)turn:[^:]+:\d+"]
SPEL_PATTERNS = [r"(?i)[$#]\{.*T\s*\(\s*java\.lang\.(?:Runtime|ProcessBuilder)"]
PATH_MATRIX_BYPASS = [r"/\.\.;/", r"/%2e%2e%3b/"]
PHP_MAGIC_HASHES = [r"0e\d{10,}"]
GRAPHQL_ALIAS_DOS = [r"(?i)(?:alias\d+\s*:\s*[a-zA-Z0-9_]+\s*\{.*?){5,}"]
INTERNAL_IP_SPOOFING = [r"(?i)(?:X-Forwarded-For|X-Real-IP|True-Client-IP|Client-IP):\s*(?:127\.0\.0\.1|localhost|10\.\d+\.\d+\.\d+)"]

# Advanced Deserialization Magic Bytes / Formats
DESER_EXT_PATTERNS = [
    r"(?i)rO0AB",           # Java Serialization
    r"(?i)Tzo",             # PHP Object Injection
    r"(?i)a:[0-9]+:\{",     # PHP Array Serialized
    r"(?i)gASV",            # Python Pickle
    r"(?i)!![a-zA-Z]+",     # YAML tags (Ruby/Python Deserialization)
]

TECH_SIGS = {
    "WordPress":["wp-content","wp-json","wp-login"],
    "Laravel":["laravel_session","X-Powered-By: PHP"],
    "Django":["csrftoken","Django"],
    "Rails":["_rails_session"],
    "Spring":["JSESSIONID"],
    "Express":["X-Powered-By: Express"],
    "Next.js":["__NEXT_DATA__","_next/static"],
    "GraphQL":["/graphql","__typename","IntrospectionQuery"],
    "Swagger":["/swagger","/api-docs"],
    "JWT":["eyJ"],
}


def _decode(b64: str) -> str:
    try:
        return base64.b64decode(b64 or "").decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_params(url: str, req_body: str) -> list:
    params = []
    try:
        params.extend(list(parse_qs(urlparse(url).query).keys()))
    except Exception:
        pass
    try:
        params.extend(list(parse_qs(req_body).keys()))
    except Exception:
        pass
    try:
        body_json = json.loads(req_body)
        if isinstance(body_json, dict):
            params.extend(list(body_json.keys()))
    except Exception:
        pass
    return list(set(params))


def triage_exchange(ex: dict) -> tuple:
    req_text = str(_decode(ex.get("request_b64", "")))
    res_text = str(_decode(ex.get("response_b64", "")))
    
    url_base = str(ex.get("url") or "")
    path_base = str(ex.get("path") or "")
    if url_base and path_base and not url_base.endswith(path_base):
        url = url_base.rstrip("/") + "/" + path_base.lstrip("/")
    else:
        url = url_base or path_base
    
    full = url + "\n" + req_text[:10000] + "\n" + res_text[:10000]
    method = str(ex.get("method", "GET") or "GET")
    status   = ex.get("status_code", 0) or 0

    score, matched = 0, []
    req_body_start = req_text.find("\r\n\r\n")
    req_body = req_text[req_body_start + 4:] if req_body_start >= 0 else ""
    interesting_params = _extract_params(url, req_body)
    if interesting_params:
        score += RULES["interesting_param"]

    # --- REGEX BASE ---
    for p in SENSITIVE_PATTERNS:
        if re.search(p, res_text[:20000], re.IGNORECASE):
            score += RULES["sensitive_data_exposure"]; matched.append("sensitive_data_exposure"); break

    if req_text and method in ("POST","PUT","PATCH") and any(k in req_body.lower() for k in MASS_ASSIGN):
        score += RULES["mass_assignment"]; matched.append("mass_assignment")

    if req_text and status in (401, 403) and "authorization" not in req_text.lower() and "cookie" not in req_text.lower():
        score += RULES["auth_anomaly"]; matched.append("auth_anomaly")

    if any(p in url.lower() for p in REDIRECT_PARAMS):
        score += RULES["open_redirect"]; matched.append("open_redirect")

    # --- CONTEXTUAL ANALYSIS (Hardcoded checks) ---
    req_content_type = ""
    for line in req_text.split('\n'):
        if line.lower().startswith("content-type:"):
            req_content_type = line.split(":", 1)[1].strip().lower()

    res_content_type = ""
    for line in res_text.split('\n'):
        if line.lower().startswith("content-type:"):
            res_content_type = line.split(":", 1)[1].strip().lower()

    res_body_start = res_text.find("\r\n\r\n")
    res_body = res_text[res_body_start + 4:] if res_body_start >= 0 else res_text

    # 1. SQLi Error Context
    SQL_ERRORS = ["syntax error at or near", "mysql_fetch_array", "ora-01756", "postgresql query failed", "sqlite3.operationalerror"]
    if any(err in res_body.lower() for err in SQL_ERRORS):
        score += RULES["sqli_candidate"] + 10
        matched.append("sqli_candidate (Error Based)")
    else:
        for p in SQLI_PATTERNS:
            if re.search(p, full, re.IGNORECASE):
                score += RULES["sqli_candidate"]; matched.append("sql_injection_candidate"); break

    # 2. XSS Reflection Context
    for p in XSS_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += RULES["xss_candidate"]
            matched.append("xss_candidate")
            break

    # 3. LFI Read Context
    if "root:x:0:0" in res_body or "[extensions]" in res_body or "bin/bash" in res_body:
        score += RULES["lfi_candidate"] + 10
        matched.append("lfi_candidate (Confirmed)")
    else:
        for p in LFI_PATTERNS:
            if re.search(p, full, re.IGNORECASE):
                score += RULES["lfi_candidate"]; matched.append("lfi_candidate"); break

    # 4. SSRF Interaction Context
    for p in SSRF_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            if "cisco" in res_body.lower() or "metadata" in res_body.lower() or "instance-id" in res_body.lower():
                score += RULES["ssrf_candidate"] + 10
                matched.append("cloud_metadata_ssrf_candidate")
            else:
                score += RULES["ssrf_candidate"]
                matched.append("cloud_metadata_ssrf_candidate")
            break

    # 5. IDOR & Auth Bypass Context
    for p in IDOR_PATTERNS:
        if re.search(p, url, re.IGNORECASE) and not re.search(r'id=1[\'\";]', url, re.IGNORECASE):
            if "Authorization:" not in req_text and "Cookie:" not in req_text:
                score += RULES["idor_candidate"] + 10
                matched.append("idor_candidate")
            else:
                score += RULES["idor_candidate"]
                matched.append("idor_candidate")
            break

    # 6. RCE Execution Context
    for p in RCE_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            if "uid=" in res_body and "gid=" in res_body or "TTL=" in res_body:
                score += RULES["rce_candidate"] + 10
                matched.append("rce_candidate (Confirmed)")
            else:
                score += RULES["rce_candidate"]
                matched.append("rce_candidate")
            break

    # Others
    if "<?xml" in full.lower() and ("!ENTITY" in full or "!DOCTYPE" in full):
        score += RULES["xxe_candidate"]; matched.append("xxe_candidate")
    for p in SSTI_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += RULES["ssti_candidate"]; matched.append("ssti_candidate"); break
    for p in DESER_EXT_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 90; matched.append("advanced_deserialization_candidate"); break
            
    for p in GRPC_PATTERNS:
        if re.search(p, req_text, re.IGNORECASE) or re.search(p, res_text, re.IGNORECASE):
            score += 60; matched.append("grpc_endpoint_detected"); break

    for p in XSLT_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 85; matched.append("xslt_injection_candidate"); break
            
    for p in MASS_ASSIGNMENT_CANDIDATE:
        if re.search(p, full, re.IGNORECASE):
            score += 80; matched.append("mass_assignment_candidate"); break
    
    # Enterprise Vectors
    for p in SMUGGLING_PATTERNS:
        if re.search(p, req_text, re.IGNORECASE):
            score += 90; matched.append("request_smuggling_candidate"); break
    
    for p in CACHE_POISON_PATTERNS:
        if re.search(p, req_text, re.IGNORECASE) and any(h in res_text.lower() for h in ["x-cache", "age:", "cache-control"]):
            score += 85; matched.append("web_cache_poisoning_candidate"); break
            
    for p in GRAPHQL_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 75; matched.append("graphql_introspection_candidate"); break
            
    for p in JWT_VULN_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 95; matched.append("jwt_alg_none_candidate"); break
            
    for p in OAUTH_PATTERNS:
        if re.search(p, url, re.IGNORECASE):
            # Check for missing state parameter in OAuth
            if "state=" not in url.lower():
                score += 80; matched.append("oauth_csrf_missing_state"); break

    # Extreme Enterprise Vectors
    for p in PROTO_POLLUTION_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 85; matched.append("prototype_pollution_candidate"); break
            
    for p in CLOUD_SSRF_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 95; matched.append("cloud_metadata_ssrf_candidate"); break
            
    for p in SAML_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 65; matched.append("saml_auth_candidate"); break
            
    for p in ESI_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 85; matched.append("esi_ssi_injection_candidate"); break
            
    for p in JSONP_PATTERNS:
        if re.search(p, url, re.IGNORECASE) and "application/json" in res_text[:2000].lower():
            score += 70; matched.append("jsonp_hijacking_candidate"); break
            
    for p in NGINX_OFF_BY_SLASH:
        if re.search(p, url, re.IGNORECASE):
            score += 70; matched.append("nginx_off_by_slash_candidate"); break
            
    if any(re.search(p, req_text, re.IGNORECASE) for p in WEBSOCKET_UPGRADE):
        score += 55; matched.append("websocket_smuggling_candidate")
        
    for p in LLM_INJECTION:
        if re.search(p, full, re.IGNORECASE):
            score += 90; matched.append("llm_prompt_injection_candidate"); break
            
    for p in PDF_GENERATOR_SIGS:
        if re.search(p, res_text, re.IGNORECASE) or re.search(p, req_text, re.IGNORECASE):
            score += 85; matched.append("pdf_headless_ssrf_candidate"); break
            
    for p in JNDI_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 100; matched.append("log4shell_jndi_candidate"); break
            
    for p in ACTUATOR_PATTERNS:
        if re.search(p, url, re.IGNORECASE):
            score += 90; matched.append("spring_actuator_exposure"); break
            
    for p in NOSQLI_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 85; matched.append("nosql_injection_candidate"); break
            
    for p in WEBRTC_SSRF_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 80; matched.append("webrtc_ssrf_candidate"); break
            
    for p in SPEL_PATTERNS:
        if re.search(p, full, re.IGNORECASE):
            score += 100; matched.append("spel_injection_candidate"); break
            
    for p in PATH_MATRIX_BYPASS:
        if re.search(p, url, re.IGNORECASE):
            score += 75; matched.append("spring_path_matrix_bypass"); break
            
    for p in PHP_MAGIC_HASHES:
        if re.search(p, full, re.IGNORECASE):
            score += 65; matched.append("php_magic_hash_candidate"); break
            
    for p in GRAPHQL_ALIAS_DOS:
        if re.search(p, full, re.IGNORECASE):
            score += 70; matched.append("graphql_alias_dos_candidate"); break
            
    for p in INTERNAL_IP_SPOOFING:
        if re.search(p, req_text, re.IGNORECASE):
            score += 60; matched.append("ip_spoofing_bypass_candidate"); break
            
    # HTTP Parameter Pollution (HPP) Detection
    # If the same parameter is sent more than once in the query string or body
    param_counts = {}
    params_list = urlparse(url).query.split('&') + req_body.split('&')
    for p in params_list:
        k = p.split('=')[0]
        if k:
            param_counts[k] = param_counts.get(k, 0) + 1
            if param_counts[k] > 1:
                score += 75; matched.append("hpp_candidate"); break

    if "%0d%0a" in url.lower() or "\r\n" in url.lower():
        score += RULES["crlf_injection"]; matched.append("crlf_injection")
    if "Access-Control-Allow-Origin: *" in res_text or "Access-Control-Allow-Credentials: true" in res_text:
        score += RULES["cors_misconfig"]; matched.append("cors_misconfig")
    if re.search(r'eyJ[A-Za-z0-9_-]+\.eyJ', full):
        score += RULES["jwt_detected"]; matched.append("jwt_detected")
    if "/graphql" in url.lower() or "__typename" in full:
        score += RULES["graphql_detected"]; matched.append("graphql_detected")
    if "multipart/form-data" in req_text.lower() or "filename=" in req_text.lower():
        score += RULES["file_upload"]; matched.append("file_upload")

    # === RESPONSE HEADER SECURITY ANALYSIS ===
    if res_text:
        security_headers_missing = []
        if "strict-transport-security" not in res_text.lower():
            security_headers_missing.append("HSTS")
        if "content-security-policy" not in res_text.lower():
            security_headers_missing.append("CSP")
        if "x-frame-options" not in res_text.lower():
            security_headers_missing.append("X-Frame-Options")
        if "x-content-type-options" not in res_text.lower():
            security_headers_missing.append("X-Content-Type-Options")
        if security_headers_missing and status in (200, 301, 302):
            score += 15
            matched.append(f"missing_security_headers:{','.join(security_headers_missing)}")

    # === COOKIE SECURITY FLAGS ===
    set_cookie_pattern = re.findall(r'(?i)Set-Cookie:\s*([^\r\n]+)', res_text)
    for cookie_line in set_cookie_pattern:
        cookie_issues = []
        if 'httponly' not in cookie_line.lower():
            cookie_issues.append("no-HttpOnly")
        if 'secure' not in cookie_line.lower():
            cookie_issues.append("no-Secure")
        if 'samesite' not in cookie_line.lower():
            cookie_issues.append("no-SameSite")
        if cookie_issues:
            score += 20
            matched.append(f"insecure_cookie:{','.join(cookie_issues)}")
            break

    # === VERSION / TECHNOLOGY LEAK ===
    version_patterns = [
        r'(?i)Server:\s*(?:Apache|nginx|IIS|Tomcat|Jetty)[/\s][\d.]+',
        r'(?i)X-Powered-By:\s*\S+',
        r'(?i)X-AspNet-Version:\s*[\d.]+',
        r'(?i)X-Runtime:\s*[\d.]+',
    ]
    for vp in version_patterns:
        if re.search(vp, res_text):
            score += 10
            matched.append("server_version_disclosure")
            break

    # === DEBUG / STACK TRACE DETECTION ===
    debug_patterns = [
        r'(?i)Traceback \(most recent call last\)',
        r'(?i)at \w+\.\w+\(\w+\.java:\d+\)',
        r'(?i)#\d+\s+\S+\.php\(\d+\)',
        r'(?i)DEBUG\s*=\s*True',
        r'(?i)DJANGO_SETTINGS_MODULE',
    ]
    for dp in debug_patterns:
        if re.search(dp, res_body) or re.search(dp, full):
            score += 40
            matched.append("debug_info_disclosure")
            break

    # === SUBDOMAIN TAKEOVER SIGNALS ===
    takeover_sigs = [
        "There isn't a GitHub Pages site here",
        "NoSuchBucket",
        "No such app",
        "Heroku | No such app",
        "NXDOMAIN",
        "The request could not be satisfied",
        "Repository not found",
    ]
    for sig in takeover_sigs:
        if sig.lower() in res_body.lower():
            score += 80
            matched.append("subdomain_takeover_candidate")
            break

    detected_tech = [t for t, sigs in TECH_SIGS.items() if any(s in full for s in sigs)]
    if detected_tech:
        interesting_params.append("TECH:" + ",".join(detected_tech))

    if score >= INTEREST_THRESHOLD["critical"]:
        level = "critical"
    elif score >= INTEREST_THRESHOLD["interesting"]:
        level = "interesting"
    elif score >= INTEREST_THRESHOLD["low"]:
        level = "low"
    else:
        level = "normal"

    reason = ", ".join(set(matched)) if matched else ""
    return level, reason, interesting_params, score, matched


def build_deep_analysis_prompt(ex: dict, matched: list) -> str:
    """
    Sadece zafiyetleri listelemez. Gercek bir pentester gibi response body'yi 
    okumasini ve "Burada soyle bir hata donmus, demek ki WAF yok, bypass icin soyle yapmali" 
    seklinde derin dusunmesini isteriz.
    """
    req_text = _decode(ex.get("request_b64", ""))[:3000]
    res_text = _decode(ex.get("response_b64", ""))[:3000]
    cats     = ", ".join(matched) if matched else "unknown"
    
    return f"""You are an elite Bug Bounty hunter analyzing an HTTP exchange.
The automated triage flagged this as: {cats}

=== HTTP REQUEST ===
{req_text}

=== HTTP RESPONSE ===
{res_text}

TASK: Do NOT just list generic vulnerabilities. Perform a DEEP contextual analysis:
1. Chain-of-Thought (CoT) Reasoning: Walk through your thought process visibly. What exactly did you see in the response body? What does the status code mean? Did it reflect our input, or throw a specific error?
2. Logical Deductions: "Since the response body contains X, it implies the backend is Y." 
3. Next Attack Vector: "Based on the reflection/error seen in the response, the exact next step should be trying payload Z."
4. Provide the exact payload/URL modification to test this theory.
5. IF the attack requires automation, write a Python `requests` script to exploit it (e.g. for Race Conditions, Bruteforcing, padding or fuzzing).
6. IF the attack requires dynamic modification in a proxy, provide the exact "Burp Suite Match and Replace Rule" or a Burp Macro instruction.

Write the report in a highly technical, concise, and professional tone, starting with your detailed CoT analysis.
"""


async def weaponize_payload(llm_gateway, fid, title, ai_reasoning):
    from app.modules.event_broadcaster import broadcast
    from app.modules.database import get_db
    
    weapon_prompt = f"""You are an offensive weaponization tool. Based on the following AI reasoning:
{ai_reasoning[:2000]}

Write a highly destructive, autonomous Python `requests` script or an advanced bash `curl` pipeline to exploit the vulnerability identified in '{title}'. 
DO NOT INCLUDE ANY TEXT EXCEPT THE RAW SCRIPT. START WITH `import requests` OR `#!/bin/bash`. 
Include advanced features like threading for brute-force or WAF bypass headers."""

    try:
        weapon = await asyncio.wait_for(llm_gateway.generate(weapon_prompt), timeout=60)
        
        # Save the weaponized script to the finding
        with get_db() as db:
            db.execute("UPDATE findings SET steps_to_test = steps_to_test || ? WHERE id = ?", ("\n\n### WEAPONIZED EXPLOIT SCRIPT ###\n```python\n" + weapon + "\n```\n", fid))
            db.commit()
            
        await broadcast("weaponization_ready", {
            "finding_id": fid,
            "msg": f"Exploit weaponized for {title}"
        })
    except Exception as e:
        print(f"[Weaponizer] Failed: {e}")

async def _process_interesting_exchange(ex, llm_gateway):
    from app.modules.event_broadcaster import broadcast
    level  = ex.get("interest_level", "normal")
    reason = ex.get("interest_reason", "")
    matched = [r.strip() for r in reason.split(",") if r.strip()]

    await broadcast("ai_analyzing", {
        "id":   ex["id"],
        "path": ex.get("path", ""),
        "msg":  f"AI Deep Analysis: {ex.get('method')} {ex.get('path')}...",
    })

    try:
        dom_context = {}
        res_text = _decode(ex.get("response_b64", ""))
        # Only parse if looks like HTML
        if "<html" in res_text.lower()[:500] or "<body" in res_text.lower()[:500]:
            dom_context = await dom_analyzer.analyze_async(res_text)
            
        prompt   = build_deep_analysis_prompt(ex, matched, dom_context)
        ai_resp  = await asyncio.wait_for(llm_gateway.generate(prompt), timeout=120)

        fid = save_finding({
            "exchange_id": ex["id"],
            "program_id":  ex.get("program_id", ""),
            "title":       f"[{level.upper()}] {ex.get('method','GET')} {ex.get('path','')}",
            "severity":    "high" if level == "critical" else "medium",
            "description": ai_resp[:3000],
            "steps_to_test": ai_resp,
            "ai_provider": getattr(llm_gateway, "last_used", "ai"),
            "confirmed": 0
        })

        await broadcast("new_finding", {
            "finding_id": fid,
            "exchange_id": ex["id"],
            "method":  ex.get("method","GET"),
            "path":    ex.get("path",""),
            "level":   level,
            "summary": "Deep analysis complete. Check findings.",
            "msg":     f"Analysis Ready: {ex.get('method')} {ex.get('path')}",
        })
        
        asyncio.create_task(weaponize_payload(llm_gateway, fid, f"[{level.upper()}] {ex.get('method','GET')} {ex.get('path','')}", ai_resp, ex))

    except asyncio.TimeoutError:
        save_finding({
            "exchange_id": ex["id"],
            "program_id":  ex.get("program_id", ""),
            "title":       f"[{level.upper()}] {ex.get('method','GET')} {ex.get('path','')}",
            "severity":    "medium",
            "description": f"Rule-based fallback due to AI timeout: {reason}",
            "steps_to_test": "",
            "ai_provider": "rule-based",
            "confirmed": 0
        })
    except Exception as e:
        print(f"[PassiveAnalyzer] AI Error: {e}")

    mark_exchange_analyzed(ex["id"], level, reason)


async def passive_analysis_loop(llm_gateway, interval_seconds: int = 8):
    from app.modules.event_broadcaster import broadcast

    endpoint_hits: dict = defaultdict(int)
    print("[PassiveAnalyzer] Deep Contextual Mode started.")

    while True:
        try:
            # 1. Triage bekleyenleri isle
            pending = get_pending_exchanges(limit=20)
            for ex in pending:
                level, reason, params, score, matched = triage_exchange(ex)

                path = ex.get("path", "")
                if len(endpoint_hits) > 5000: endpoint_hits.clear()
                endpoint_hits[path] += 1
                if endpoint_hits[path] >= 5 and level == "normal":
                    level = "low"
                    reason = (reason + ", rate_limit_candidate").strip(", ")
                    score += RULES["rate_limit_missing"]

                update_exchange_triage(ex["id"], level, reason, params, score)

                if level in ("critical", "interesting"):
                    await broadcast("new_interesting_request", {
                        "id":       ex["id"],
                        "method":   ex.get("method", "GET"),
                        "path":     ex.get("path", ""),
                        "host":     ex.get("host", ""),
                        "level":    level,
                        "reason":   reason,
                        "score":    score,
                        "msg":      f"[{level.upper()}] {ex.get('method')} {ex.get('path')} — {reason}",
                    })

            # 2. AI ile Derinlemesine Contextual Analysis (Concurrent)
            interesting = get_unanalyzed_exchanges(limit=3)
            tasks = []
            for ex in interesting:
                level  = ex.get("interest_level", "normal")
                reason = ex.get("interest_reason", "")
                if level not in ("critical", "interesting"):
                    mark_exchange_analyzed(ex["id"], level, reason)
                    continue
                tasks.append(asyncio.create_task(_process_interesting_exchange(ex, llm_gateway)))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            print(f"[PassiveAnalyzer] Loop Error: {e}")

        await asyncio.sleep(interval_seconds)
