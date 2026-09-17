"""Burp Suite data importer - XML, HAR, raw HTTP."""

from __future__ import annotations
from pathlib import Path
from app.models.http_exchange import HttpExchange
from app.utils.burp_xml_parser import parse_burp_xml
from app.utils.har_parser import parse_har
from app.utils.http_parser import parse_raw_request, parse_raw_response
from app.modules.scope_manager import scope_manager


class BurpImporter:
    """Imports and manages HTTP exchange data from Burp Suite."""

    def __init__(self):
        self.exchanges: list[HttpExchange] = []
        self._next_id: int = 1

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
            id=self._next_id,
            request=request,
            response=response or HttpExchange().response,
            source="manual",
        )
        self._next_id += 1
        self.exchanges.append(exchange)
        return exchange

    def _add_exchanges(self, new: list[HttpExchange]) -> list[HttpExchange]:
        """Add exchanges with reassigned IDs and scope filtering."""
        for ex in new:
            ex.id = self._next_id
            ex.request.id = self._next_id
            self._next_id += 1

        # Filter by scope
        in_scope = scope_manager.filter_exchanges(new)
        self.exchanges.extend(in_scope)
        return in_scope

    def get_exchange(self, exchange_id: int) -> HttpExchange | None:
        """Get a specific exchange by ID."""
        for ex in self.exchanges:
            if ex.id == exchange_id:
                return ex
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
