"""Scope Manager - Bug bounty program scope management."""

from __future__ import annotations
from app.models.scope import ProgramScope, ScopeRule
from app.models.http_exchange import HttpExchange


class ScopeManager:
    """Manages bug bounty program scope and filters traffic."""

    def __init__(self):
        self.scope = ProgramScope()

    def set_scope(self, scope: ProgramScope) -> None:
        self.scope = scope

    def set_from_domains(
        self,
        program_name: str,
        include_domains: list[str],
        exclude_domains: list[str] | None = None,
        platform: str = "hackerone",
    ) -> ProgramScope:
        """Quick scope setup from domain lists."""
        self.scope = ProgramScope(
            program_name=program_name,
            platform=platform,
        )
        for domain in include_domains:
            self.scope.add_include(domain)
        for domain in (exclude_domains or []):
            self.scope.add_exclude(domain)
        return self.scope

    def is_in_scope(self, url: str) -> bool:
        """Check if URL is within scope."""
        if not self.scope.rules:
            return True  # No scope defined = everything allowed
        return self.scope.is_in_scope(url)

    def filter_exchanges(
        self, exchanges: list[HttpExchange]
    ) -> list[HttpExchange]:
        """Filter exchanges to only in-scope items."""
        if not self.scope.rules:
            return exchanges
        return [e for e in exchanges if self.is_in_scope(e.request.url)]

    def get_scope_summary(self) -> dict:
        """Get a summary of the current scope."""
        includes = [
            r.pattern for r in self.scope.rules if r.rule_type == "include"
        ]
        excludes = [
            r.pattern for r in self.scope.rules if r.rule_type == "exclude"
        ]
        return {
            "program_name": self.scope.program_name,
            "platform": self.scope.platform,
            "includes": includes,
            "excludes": excludes,
            "total_rules": len(self.scope.rules),
        }


# Singleton
scope_manager = ScopeManager()
