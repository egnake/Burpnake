"""HAR (HTTP Archive) file parser."""

from __future__ import annotations
import json
from pathlib import Path
from app.models.http_exchange import HttpExchange, HttpRequest, HttpResponse, HttpHeader
from urllib.parse import urlparse


def parse_har(har_content: str | bytes) -> list[HttpExchange]:
    """Parse a HAR file into HttpExchange list."""
    if isinstance(har_content, bytes):
        har_content = har_content.decode("utf-8", errors="replace")

    data = json.loads(har_content)
    entries = data.get("log", {}).get("entries", [])
    exchanges: list[HttpExchange] = []

    for idx, entry in enumerate(entries, 1):
        try:
            exchange = _parse_entry(entry, idx)
            exchanges.append(exchange)
        except Exception:
            continue

    return exchanges


def _parse_entry(entry: dict, idx: int) -> HttpExchange:
    """Parse a single HAR entry."""
    req_data = entry.get("request", {})
    resp_data = entry.get("response", {})

    # Parse request
    parsed_url = urlparse(req_data.get("url", ""))
    headers = [
        HttpHeader(name=h["name"], value=h["value"])
        for h in req_data.get("headers", [])
    ]

    body = ""
    post_data = req_data.get("postData", {})
    if post_data:
        body = post_data.get("text", "")

    content_type = ""
    cookies = ""
    for h in headers:
        if h.name.lower() == "content-type":
            content_type = h.value
        elif h.name.lower() == "cookie":
            cookies = h.value

    req_method = req_data.get("method", "GET")
    req_path = parsed_url.path + ("?" + parsed_url.query if parsed_url.query else "") or "/"
    req_host = parsed_url.hostname or ""
    req_ver = req_data.get("httpVersion", "HTTP/1.1")
    raw_req_lines = [f"{req_method} {req_path} {req_ver}"]
    if req_host and not any(h.name.lower() == "host" for h in headers):
        raw_req_lines.append(f"Host: {req_host}")
    for h in headers:
        raw_req_lines.append(f"{h.name}: {h.value}")
    raw_req_lines.append("")
    if body:
        raw_req_lines.append(body)
    raw_req = "\r\n".join(raw_req_lines)

    request = HttpRequest(
        id=str(idx),
        method=req_method,
        url=req_data.get("url", ""),
        path=req_path,
        host=req_host,
        port=parsed_url.port or (443 if parsed_url.scheme == "https" else 80),
        protocol=parsed_url.scheme or "https",
        http_version=req_ver,
        headers=headers,
        body=body,
        content_type=content_type,
        cookies=cookies,
        raw=raw_req,
    )

    # Parse response
    resp_headers = [
        HttpHeader(name=h["name"], value=h["value"])
        for h in resp_data.get("headers", [])
    ]

    resp_content = resp_data.get("content", {})
    resp_body = resp_content.get("text", "")
    resp_ct = resp_content.get("mimeType", "")
    resp_status = resp_data.get("status", 0)
    resp_status_text = resp_data.get("statusText", "")
    resp_ver = resp_data.get("httpVersion", "HTTP/1.1")

    raw_resp_lines = [f"{resp_ver} {resp_status} {resp_status_text}".strip()]
    for h in resp_headers:
        raw_resp_lines.append(f"{h.name}: {h.value}")
    raw_resp_lines.append("")
    if resp_body:
        raw_resp_lines.append(resp_body)
    raw_resp = "\r\n".join(raw_resp_lines)

    response = HttpResponse(
        status_code=resp_status,
        status_text=resp_status_text,
        http_version=resp_ver,
        headers=resp_headers,
        body=resp_body,
        content_type=resp_ct,
        content_length=resp_content.get("size", 0),
        raw=raw_resp,
    )

    return HttpExchange(
        id=str(idx),
        request=request,
        response=response,
        source="har_import",
    )


def parse_har_file(file_path: str | Path) -> list[HttpExchange]:
    """Parse a HAR file from disk."""
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    return parse_har(content)
