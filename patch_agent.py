import re

with open('app/modules/agent_loop.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace PROMPT
old_prompt = r'''"body": "optional new body"
  },'''
new_prompt = r'''"body": "optional new body"
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
  ],'''

content = content.replace(old_prompt, new_prompt)

old_rule = r'''CRITICAL EXPLOITATION RULES (FLAWLESS EXECUTION):'''
new_rule = r'''NOTE: You can provide EITHER 'payload_modifications' (for a single request) OR 'macro_modifications' (a JSON array for multi-step stateful attacks where cookies/sessions are preserved between steps). DO NOT provide both.

CRITICAL EXPLOITATION RULES (FLAWLESS EXECUTION):'''
content = content.replace(old_rule, new_rule)

# 2. Add _send_macro_requests function
new_func = r'''
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
'''

# Add _send_macro_requests just before _send_modified_request
content = content.replace("async def _send_modified_request", new_func + "\nasync def _send_modified_request")

# 3. Patch hunt() to call macro
hunt_patch = r'''
                    if "macro_modifications" in j_data and isinstance(j_data["macro_modifications"], list):
                        mods = j_data["macro_modifications"]
                        payload_desc = "[MACRO] " + str(j_data.get("payload_description", "Multi-step attack"))
                        new_req_text, new_res_text = await _send_macro_requests(ex, mods, base_req_text)
                    else:
                        mods = j_data.get("payload_modifications", {})
                        payload_desc = j_data.get("payload_description", "Unknown payload")
                        new_req_text, new_res_text = await _send_modified_request(ex, mods, current_req_text)
'''

# We need to replace the try block in hunt
# In hunt():
old_hunt_call = r'''                        mods = j_data.get("payload_modifications", {})
                        payload_desc = j_data.get("payload_description", "Unknown payload")
                        
                        new_req_text, new_res_text = await _send_modified_request(ex, mods, current_req_text)'''

content = content.replace(old_hunt_call, hunt_patch)

with open('app/modules/agent_loop.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Agent Loop Macro Fuzzing injected successfully.")