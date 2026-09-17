"""HTTP request/response parser utilities."""

from __future__ import annotations
from app.models.http_exchange import HttpRequest, HttpResponse, HttpHeader, HttpExchange
from urllib.parse import urlparse


def parse_raw_request(raw: str) -> HttpRequest:
    """Parse a raw HTTP request string into HttpRequest model."""
    lines = raw.strip().split("\n")
    if not lines:
        return HttpRequest(raw=raw)

    # Parse request line
    first_line = lines[0].strip()
    parts = first_line.split(" ", 2)
    method = parts[0] if len(parts) > 0 else "GET"
    path = parts[1] if len(parts) > 1 else "/"
    http_version = parts[2] if len(parts) > 2 else "HTTP/1.1"

    # Parse headers and body
    headers: list[HttpHeader] = []
    body = ""
    header_done = False
    host = ""
    content_type = ""
    cookies = ""

    for i, line in enumerate(lines[1:], 1):
        line = line.rstrip("\r")
        if not header_done:
            if line.strip() == "":
                header_done = True
                body = "\n".join(lines[i + 1 :]).strip()
                break
            if ":" in line:
                name, value = line.split(":", 1)
                name = name.strip()
                value = value.strip()
                headers.append(HttpHeader(name=name, value=value))
                if name.lower() == "host":
                    host = value
                elif name.lower() == "content-type":
                    content_type = value
                elif name.lower() == "cookie":
                    cookies = value

    # Build URL
    protocol = "https"
    port = 443
    if host:
        if ":" in host:
            host_part, port_str = host.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                host_part = host
            host = host_part
        url = f"{protocol}://{host}{path}"
    else:
        url = path

    return HttpRequest(
        method=method,
        url=url,
        path=path,
        host=host,
        port=port,
        protocol=protocol,
        http_version=http_version,
        headers=headers,
        body=body,
        content_type=content_type,
        cookies=cookies,
        raw=raw,
    )


def parse_raw_response(raw: str) -> HttpResponse:
    """Parse a raw HTTP response string into HttpResponse model."""
    lines = raw.strip().split("\n")
    if not lines:
        return HttpResponse(raw=raw)

    # Parse status line
    first_line = lines[0].strip()
    parts = first_line.split(" ", 2)
    http_version = parts[0] if len(parts) > 0 else "HTTP/1.1"
    status_code = int(parts[1]) if len(parts) > 1 else 0
    status_text = parts[2] if len(parts) > 2 else ""

    # Parse headers and body
    headers: list[HttpHeader] = []
    body = ""
    content_type = ""
    content_length = 0

    header_done = False
    for i, line in enumerate(lines[1:], 1):
        line = line.rstrip("\r")
        if not header_done:
            if line.strip() == "":
                header_done = True
                body = "\n".join(lines[i + 1 :]).strip()
                break
            if ":" in line:
                name, value = line.split(":", 1)
                name = name.strip()
                value = value.strip()
                headers.append(HttpHeader(name=name, value=value))
                if name.lower() == "content-type":
                    content_type = value
                elif name.lower() == "content-length":
                    try:
                        content_length = int(value)
                    except ValueError:
                        pass

    return HttpResponse(
        status_code=status_code,
        status_text=status_text,
        http_version=http_version,
        headers=headers,
        body=body,
        content_type=content_type,
        content_length=content_length,
        raw=raw,
    )
