"""Burp Suite data importer - XML, HAR, raw HTTP."""

from __future__ import annotations
import base64
import json
from pathlib import Path
from app.models.http_exchange import HttpExchange, HttpRequest, HttpResponse, HttpHeader
from app.utils.burp_xml_parser import parse_burp_xml
from app.utils.har_parser import parse_har
from app.utils.http_parser import parse_raw_request, parse_raw_response
from app.modules.scope_manager import scope_manager


class BurpImporter:
    """Imports and manages HTTP exchange data from Burp Suite."""

    def __init__(self):
        self.exchanges: list[HttpExchange] = []
        self._next_id: int = 1

    def _persist_to_db(self, ex: HttpExchange):
        """Import edilen istegi SQLite veritabanina da kaydeder."""
        try:
            from app.modules.database import save_exchange
            req_b64 = base64.b64encode(ex.request.raw.encode()).decode() if ex.request.raw else ""
            res_b64 = base64.b64encode(ex.response.raw.encode()).decode() if ex.response.raw else ""
            save_exchange({
                "id": str(ex.id),
                "host": ex.request.host,
                "url": ex.request.url,
                "path": ex.request.path,
                "method": ex.request.method,
                "status_code": ex.response.status_code,
                "request_b64": req_b64,
                "response_b64": res_b64,
                "request_headers": {h.name: h.value for h in ex.request.headers},
                "response_headers": {h.name: h.value for h in ex.response.headers},
                "interest_level": "pending",
                "score": 0,
            })
        except Exception:
            pass

    def _row_to_exchange(self, row: dict) -> HttpExchange:
        """SQLite veritabani satirini HttpExchange nesnesine donusturur."""
        try:
            req_raw = base64.b64decode(row.get("request_b64", "")).decode("utf-8", errors="ignore")
        except Exception:
            req_raw = row.get("request_b64", "")

        try:
            res_raw = base64.b64decode(row.get("response_b64", "")).decode("utf-8", errors="ignore")
        except Exception:
            res_raw = row.get("response_b64", "")

        try:
            req_h_dict = json.loads(row.get("request_headers", "{}") or "{}")
        except Exception:
            req_h_dict = {}

        try:
            res_h_dict = json.loads(row.get("response_headers", "{}") or "{}")
        except Exception:
            res_h_dict = {}

        req_headers = [HttpHeader(name=k, value=str(v)) for k, v in req_h_dict.items()]
        res_headers = [HttpHeader(name=k, value=str(v)) for k, v in res_h_dict.items()]

        req = HttpRequest(
            id=str(row.get("id")),
            method=row.get("method") or "GET",
            url=row.get("url") or "",
            path=row.get("path") or "",
            host=row.get("host") or "",
            headers=req_headers,
            raw=req_raw,
        )
        res = HttpResponse(
            status_code=row.get("status_code") or 0,
            headers=res_headers,
            raw=res_raw,
        )
        return HttpExchange(
            id=str(row.get("id")),
            request=req,
            response=res,
            source="sqlite",
        )

    def import_burp_xml(self, content: str | bytes) -> list[HttpExchange]:
        """Import from Burp Suite XML export."""
        new_exchanges = parse_burp_xml(content)
        return self._add_exchanges(new_exchanges)

    def import_har(self, content: str | bytes) -> list[HttpExchange]:
        """Import from HAR file."""
        new_exchanges = parse_har(content)
        return self._add_exchanges(new_exchanges)

    def import_raw(self, raw_request: str, raw_response: str = "") -> HttpExchange:
        """Import a single raw HTTP request/response pair."""
        request = parse_raw_request(raw_request)
        response = parse_raw_response(raw_response) if raw_response else None

        exchange = HttpExchange(
            id=str(self._next_id),
            request=request,
            response=response or HttpExchange().response,
            source="manual",
        )
        self._next_id += 1
        self.exchanges.append(exchange)
        self._persist_to_db(exchange)
        return exchange

    def _add_exchanges(self, new: list[HttpExchange]) -> list[HttpExchange]:
        """Add exchanges with reassigned IDs and scope filtering."""
        for ex in new:
            ex.id = str(self._next_id)
            ex.request.id = str(self._next_id)
            self._next_id += 1

        # Filter by scope
        in_scope = scope_manager.filter_exchanges(new)
        self.exchanges.extend(in_scope)
        for ex in in_scope:
            self._persist_to_db(ex)
        return in_scope

    def get_exchange(self, exchange_id: int | str) -> HttpExchange | None:
        """Get a specific exchange by ID from memory or SQLite."""
        target_id = str(exchange_id)
        for ex in self.exchanges:
            if str(ex.id) == target_id:
                return ex

        # SQLite arama yedegi
        try:
            from app.modules.database import get_db
            conn = get_db()
            row = conn.execute("SELECT * FROM exchanges WHERE id=?", (target_id,)).fetchone()
            conn.close()
            if row:
                return self._row_to_exchange(dict(row))
        except Exception:
            pass

        return None

    def get_exchanges(
        self,
        method: str | None = None,
        status_code: int | None = None,
        path_contains: str | None = None,
        has_params: bool | None = None,
    ) -> list[HttpExchange]:
        """Filter exchanges with various criteria."""
        result = self.exchanges
        if not result:
            try:
                from app.modules.database import get_exchanges
                db_rows = get_exchanges(limit=200)
                result = [self._row_to_exchange(r) for r in db_rows]
            except Exception:
                result = []

        if method:
            result = [e for e in result if e.request.method.upper() == method.upper()]
        if status_code:
            result = [e for e in result if e.response.status_code == status_code]
        if path_contains:
            result = [
                e for e in result if path_contains.lower() in e.request.path.lower()
            ]
        if has_params is not None:
            result = [e for e in result if e.request.has_params == has_params]

        return result

    def get_summary(self) -> dict:
        """Get import summary statistics."""
        methods: dict[str, int] = {}
        status_codes: dict[int, int] = {}
        hosts: set[str] = set()

        for ex in self.exchanges:
            methods[ex.request.method] = methods.get(ex.request.method, 0) + 1
            sc = ex.response.status_code
            status_codes[sc] = status_codes.get(sc, 0) + 1
            if ex.request.host:
                hosts.add(ex.request.host)

        return {
            "total_exchanges": len(self.exchanges),
            "methods": methods,
            "status_codes": status_codes,
            "unique_hosts": list(hosts),
            "with_params": sum(1 for e in self.exchanges if e.request.has_params),
        }

    def list_exchanges(self, limit: int = 50) -> list[str]:
        """Get a human-readable list of exchanges."""
        return [ex.summary for ex in self.exchanges[:limit]]

    def clear(self) -> None:
        """Clear all imported data."""
        self.exchanges.clear()
        self._next_id = 1


# Singleton
burp_importer = BurpImporter()
