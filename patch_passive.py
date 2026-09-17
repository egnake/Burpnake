import sys

with open('app/modules/passive_analyzer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add DOM analyzer import at the top
if "from app.modules.dom_analyzer import dom_analyzer" not in content:
    content = content.replace("import asyncio", "import asyncio\nfrom app.modules.dom_analyzer import dom_analyzer")

# Update build_deep_analysis_prompt signature and body
old_prompt = r'''def build_deep_analysis_prompt(ex: dict, matched: list) -> str:
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

new_prompt = r'''def build_deep_analysis_prompt(ex: dict, matched: list, dom_context: dict = None) -> str:
    import json
    req_text = _decode(ex.get("request_b64", ""))
    res_text = _decode(ex.get("response_b64", ""))
    req_text = req_text[:5000]
    res_text = res_text[:5000] + ("\n...[TRUNCATED]..." if len(res_text) > 5000 else "")
    cats     = ", ".join(matched) if matched else "unknown"
    method = ex.get("method", "GET")
    url = ex.get("url", "")
    
    dom_str = ""
    if dom_context and any(dom_context.values()):
        dom_str = f"\n=== DOM RECON CONTEXT ===\n{json.dumps(dom_context, indent=2)}\n"
    
    return f"""You are an elite Defensive Security Tester analyzing an HTTP exchange.
The automated triage flagged this as: {cats}
Method: {method}
URL: {url}

=== HTTP REQUEST ===
{req_text}

=== HTTP RESPONSE ===
{res_text}
{dom_str}
TASK: Perform a DEEP contextual security analysis:
1. Chain-of-Thought (CoT) Reasoning: Walk through your thought process visibly. What exactly did you see in the response? If DOM Recon Context is provided, analyze hidden inputs or comments for potential state parameters or secrets.
2. Logical Deductions: "Since the response body contains X, it implies the backend is Y." 
3. Next Verification Vector: "Based on the reflection/error seen in the response, the exact next step to verify this should be trying payload Z."
4. Provide the exact payload/URL modification to safely test this theory.

Write the report in a highly technical, concise, and professional tone."""'''

content = content.replace(old_prompt, new_prompt)

# Update _process_interesting_exchange to use DOM analyzer
old_process = r'''    try:
        prompt   = build_deep_analysis_prompt(ex, matched)'''

new_process = r'''    try:
        dom_context = {}
        res_text = _decode(ex.get("response_b64", ""))
        # Only parse if looks like HTML
        if "<html" in res_text.lower()[:500] or "<body" in res_text.lower()[:500]:
            dom_context = await dom_analyzer.analyze_async(res_text)
            
        prompt   = build_deep_analysis_prompt(ex, matched, dom_context)'''

content = content.replace(old_process, new_process)

with open('app/modules/passive_analyzer.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("DOM Analyzer injected to passive_analyzer.py")