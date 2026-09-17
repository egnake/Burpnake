"""Burp Suite XML export parser."""

from __future__ import annotations
import base64
from pathlib import Path
from lxml import etree
from app.models.http_exchange import HttpExchange, HttpRequest, HttpResponse
from app.utils.http_parser import parse_raw_request, parse_raw_response


def parse_burp_xml(xml_content: str | bytes) -> list[HttpExchange]:
    """
    Parse Burp Suite 'Save Items' XML export into HttpExchange list.
    
    Burp XML format:
    <items>
      <item>
        <time>...</time>
        <url>...</url>
        <host ip="...">hostname</host>
        <port>443</port>
        <protocol>https</protocol>
        <method>POST</method>
        <path>/api/endpoint</path>
        <extension>null</extension>
        <request base64="true">...</request>
        <status>200</status>
        <responselength>1234</responselength>
        <mimetype>JSON</mimetype>
        <response base64="true">...</response>
        <comment></comment>
      </item>
    </items>
    """
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8", errors="replace")

    exchanges: list[HttpExchange] = []

    try:
        root = etree.fromstring(xml_content)
    except etree.XMLSyntaxError:
        # Try parsing with recovery mode
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(xml_content, parser=parser)

    items = root.findall(".//item")

    for idx, item in enumerate(items, 1):
        try:
            exchange = _parse_item(item, idx)
            exchanges.append(exchange)
        except Exception:
            continue

    return exchanges


def _parse_item(item: etree._Element, idx: int) -> HttpExchange:
    """Parse a single <item> element."""
    # Parse request
    req_elem = item.find("request")
    if req_elem is not None and req_elem.text:
        is_base64 = req_elem.get("base64", "false").lower() == "true"
        raw_req = (
            base64.b64decode(req_elem.text).decode("utf-8", errors="replace")
            if is_base64
            else req_elem.text
        )
        request = parse_raw_request(raw_req)
    else:
        request = HttpRequest()

    # Parse response
    resp_elem = item.find("response")
    if resp_elem is not None and resp_elem.text:
        is_base64 = resp_elem.get("base64", "false").lower() == "true"
        raw_resp = (
            base64.b64decode(resp_elem.text).decode("utf-8", errors="replace")
            if is_base64
            else resp_elem.text
        )
        response = parse_raw_response(raw_resp)
    else:
        response = HttpResponse()

    # Override with XML metadata
    _el = lambda tag: (item.findtext(tag) or "").strip()

    request.id = idx
    request.method = _el("method") or request.method
    request.path = _el("path") or request.path
    request.host = _el("host") or request.host
    request.protocol = _el("protocol") or request.protocol

    port_str = _el("port")
    if port_str:
        try:
            request.port = int(port_str)
        except ValueError:
            pass

    url = _el("url")
    if url:
        request.url = url

    status_str = _el("status")
    if status_str:
        try:
            response.status_code = int(status_str)
        except ValueError:
            pass

    return HttpExchange(
        id=idx,
        request=request,
        response=response,
        source="burp_import",
        notes=_el("comment"),
    )


def parse_burp_xml_file(file_path: str | Path) -> list[HttpExchange]:
    """Parse a Burp XML file from disk."""
    path = Path(file_path)
    content = path.read_bytes()
    return parse_burp_xml(content)
