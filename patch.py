import re

with open('app/modules/passive_analyzer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace build_deep_analysis_prompt
old_build_prompt = r'''def build_deep_analysis_prompt(ex: dict, matched: list) -> str:
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
5. IF the attack requires automation, write a Python equests script to exploit it (e.g. for Race Conditions, Bruteforcing, padding or fuzzing).
6. IF the attack requires dynamic modification in a proxy, provide the exact "Burp Suite Match and Replace Rule" or a Burp Macro instruction.

Write the report in a highly technical, concise, and professional tone, starting with your detailed CoT analysis.
"""'''

new_build_prompt = r'''def build_deep_analysis_prompt(ex: dict, matched: list) -> str:
    req_text = _decode(ex.get("request_b64", ""))
    res_text = _decode(ex.get("response_b64", ""))
    req_text = req_text[:5000]
    res_text = res_text[:5000] + ("\n...[TRUNCATED]..." if len(res_text) > 5000 else "")
    cats     = ", ".join(matched) if matched else "unknown"
    method = ex.get("method", "GET")
    url = ex.get("url", "")
    
    return f"""You are an elite Defensive Security Tester analyzing an HTTP exchange.
The automated triage flagged this as: {cats}
Method: {method}
URL: {url}

=== HTTP REQUEST ===
{req_text}

=== HTTP RESPONSE ===
{res_text}

TASK: Perform a DEEP contextual security analysis:
1. Chain-of-Thought (CoT) Reasoning: Walk through your thought process visibly. What exactly did you see in the response?
2. Logical Deductions: "Since the response body contains X, it implies the backend is Y." 
3. Next Verification Vector: "Based on the reflection/error seen in the response, the exact next step to verify this should be trying payload Z."
4. Provide the exact payload/URL modification to safely test this theory.

Write the report in a highly technical, concise, and professional tone."""'''

# Replace weaponize_payload
old_weaponize = r'''async def weaponize_payload(llm_gateway, fid, title, ai_reasoning):
    from app.modules.event_broadcaster import broadcast
    from app.modules.database import get_db
    
    weapon_prompt = f"""You are an offensive weaponization tool. Based on the following AI reasoning:
{ai_reasoning[:2000]}

Write a highly destructive, autonomous Python equests script or an advanced bash curl pipeline to exploit the vulnerability identified in '{title}'. 
DO NOT INCLUDE ANY TEXT EXCEPT THE RAW SCRIPT. START WITH import requests OR #!/bin/bash. 
Include advanced features like threading for brute-force or WAF bypass headers."""

    try:
        weapon = await asyncio.wait_for(llm_gateway.generate(weapon_prompt), timeout=60)
        
        # Save the weaponized script to the finding
        with get_db() as db:
            db.execute("UPDATE findings SET steps_to_test = steps_to_test || ? WHERE id = ?", ("\n\n### WEAPONIZED EXPLOIT SCRIPT ###\n`python\n" + weapon + "\n`\n", fid))
            db.commit()
            
        await broadcast("weaponization_ready", {
            "finding_id": fid,
            "msg": f"Exploit weaponized for {title}"
        })
    except Exception as e:
        print(f"[Weaponizer] Failed: {e}")'''

new_weaponize = r'''async def weaponize_payload(llm_gateway, fid, title, ai_reasoning, ex):
    from app.modules.event_broadcaster import broadcast
    from app.modules.database import get_db
    
    req_text = _decode(ex.get("request_b64", ""))[:2000]
    
    weapon_prompt = f"""You are a Defensive Security Automation Tool. Based on the following AI reasoning:
{ai_reasoning[:3000]}

Original Request Context:
{req_text}

Write a safe, Proof-of-Concept Python equests script to verify the vulnerability identified in '{title}'.
DO NOT INCLUDE ANY TEXT EXCEPT THE RAW PYTHON SCRIPT. START WITH import requests. 
Make sure the script uses the correct URL and method from the context."""

    try:
        weapon = await asyncio.wait_for(llm_gateway.generate(weapon_prompt), timeout=60)
        weapon = weapon.replace("`python", "").replace("`", "").strip()
        
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE findings SET steps_to_test = IFNULL(steps_to_test, '') || ? WHERE id = ?", ("\n\n### VERIFICATION SCRIPT ###\n`python\n" + weapon + "\n`\n", fid))
        conn.commit()
        conn.close()
            
        await broadcast("weaponization_ready", {
            "finding_id": fid,
            "msg": f"PoC generated for {title}"
        })
    except Exception as e:
        print(f"[Weaponizer] Failed: {e}")'''

content = content.replace(old_build_prompt, new_build_prompt)
content = content.replace(old_weaponize, new_weaponize)

# Fix passive_analysis_loop sequential blocking and bugs
old_loop = r'''async def passive_analysis_loop(llm_gateway, interval_seconds: int = 8):'''
new_loop = r'''async def _process_interesting_exchange(ex, llm_gateway):
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
        prompt   = build_deep_analysis_prompt(ex, matched)
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


async def passive_analysis_loop(llm_gateway, interval_seconds: int = 8):'''

content = content.replace(old_loop, new_loop)

# Fix the internal loop logic inside passive_analysis_loop
old_inner_loop = r'''            # 2. AI ile Derinlemesine Contextual Analysis
            interesting = get_unanalyzed_exchanges(limit=3)
            for ex in interesting:
                level  = ex.get("interest_level", "normal")
                reason = ex.get("interest_reason", "")
                if level not in ("critical", "interesting"):
                    mark_exchange_analyzed(ex["id"], level, reason)
                    continue

                matched = [r.strip() for r in reason.split(",") if r.strip()]

                await broadcast("ai_analyzing", {
                    "id":   ex["id"],
                    "path": ex.get("path", ""),
                    "msg":  f"AI Deep Analysis: {ex.get('method')} {ex.get('path')}...",
                })

                try:
                    # Yeni, akilli prompt'u gonderiyoruz
                    prompt   = build_deep_analysis_prompt(ex, matched)
                    ai_resp  = await asyncio.wait_for(llm_gateway.generate(prompt), timeout=120)

                    fid = save_finding({
                        "exchange_id": ex["id"],
                        "program_id":  ex.get("program_id", ""),
                        "title":       f"[{level.upper()}] {ex.get('method','GET')} {ex.get('path','')}",
                        "severity":    "high" if level == "critical" else "medium",
                        "description": ai_resp[:3000],
                        "steps_to_test": ai_resp,
                        "ai_provider": getattr(llm_gateway, "last_provider", "ai"),
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
                    
                    # God Mode: Fire the weaponizer in the background
                    asyncio.create_task(weaponize_payload(llm_gateway, fid, f"[{level.upper()}] {ex.get('method','GET')} {ex.get('path','')}", ai_resp))

                except asyncio.TimeoutError:
                    save_finding({
                        "exchange_id": ex["id"],
                        "program_id":  ex.get("program_id", ""),
                        "title":       f"[{level.upper()}] {ex.get('method','GET')} {ex.get('path','')}",
                        "severity":    "medium",
                        "description": f"Rule-based fallback due to AI timeout: {reason}",
                        "steps_to_test": "",
                        "ai_provider": "rule-based",
                    })
                except Exception as e:
                    print(f"[PassiveAnalyzer] AI Error: {e}")

                mark_exchange_analyzed(ex["id"], level, reason)'''

new_inner_loop = r'''            # 2. AI ile Derinlemesine Contextual Analysis (Concurrent)
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
                await asyncio.gather(*tasks, return_exceptions=True)'''

content = content.replace(old_inner_loop, new_inner_loop)

# Fix endpoint hits infinite memory leak by adding basic clear
content = content.replace("endpoint_hits[path] += 1", "if len(endpoint_hits) > 5000: endpoint_hits.clear()\n                endpoint_hits[path] += 1")


with open('app/modules/passive_analyzer.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Passive analyzer patched successfully")