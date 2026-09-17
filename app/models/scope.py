"""Scope management data models."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
import re
from urllib.parse import urlparse


class ScopeRule(BaseModel):
    """A single scope rule (in-scope or out-of-scope)."""
    pattern: str  # Domain or URL pattern (supports wildcards)
    rule_type: str = "include"  # include or exclude
    protocol: str = "any"  # http, https, any
    port: Optional[int] = None
    note: str = ""

    def matches(self, url: str) -> bool:
        """Check if a URL matches this scope rule."""
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port
        scheme = parsed.scheme

        # Check protocol
        if self.protocol != "any" and scheme != self.protocol:
            return False

        # Check port
        if self.port is not None and port != self.port:
            return False

        # Check domain pattern (supports wildcards)
        regex_pattern = self.pattern.replace(".", r"\.").replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", host, re.IGNORECASE))


class ProgramScope(BaseModel):
    """Bug bounty program scope definition."""
    program_name: str = ""
    platform: str = ""  # hackerone, bugcrowd, yeswehack, other
    program_url: str = ""
    rules: list[ScopeRule] = Field(default_factory=list)
    notes: str = ""
    vulnerability_types: list[str] = Field(default_factory=list)
    out_of_scope_notes: str = ""

    def is_in_scope(self, url: str) -> bool:
        """Check if a URL is within the program scope."""
        # Check excludes first
        for rule in self.rules:
            if rule.rule_type == "exclude" and rule.matches(url):
                return False

        # Check includes
        for rule in self.rules:
            if rule.rule_type == "include" and rule.matches(url):
                return True

        # Default: out of scope if no include rule matched
        return False

    def add_include(self, pattern: str, **kwargs) -> None:
        self.rules.append(ScopeRule(pattern=pattern, rule_type="include", **kwargs))

    def add_exclude(self, pattern: str, **kwargs) -> None:
        self.rules.append(ScopeRule(pattern=pattern, rule_type="exclude", **kwargs))
