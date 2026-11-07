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
        if not url or not self.pattern:
            return False

        normalized_url = url if "://" in url else f"https://{url}"
        parsed = urlparse(normalized_url)
        host = (parsed.hostname or "").lower()
        port = parsed.port
        scheme = (parsed.scheme or "").lower()

        raw_pattern = self.pattern.strip()
        pattern_scheme = None
        if "://" in raw_pattern:
            p_parsed = urlparse(raw_pattern)
            pattern_scheme = (p_parsed.scheme or "").lower()
            host_pattern = (p_parsed.hostname or "").lower()
            pattern_port = p_parsed.port
            path_pattern = p_parsed.path or ""
        else:
            slash_idx = raw_pattern.find("/")
            host_part = raw_pattern[:slash_idx] if slash_idx >= 0 else raw_pattern
            path_pattern = raw_pattern[slash_idx:] if slash_idx >= 0 else ""
            pattern_port = None
            if ":" in host_part:
                hp, p_str = host_part.rsplit(":", 1)
                if p_str.isdigit():
                    host_part = hp
                    pattern_port = int(p_str)
            host_pattern = host_part.lower()

        if not host_pattern:
            return False

        # Check protocol
        effective_proto = self.protocol.lower()
        if effective_proto != "any" and scheme != effective_proto:
            return False
        if effective_proto == "any" and pattern_scheme and scheme and scheme != pattern_scheme:
            # Only enforce pattern scheme if URL explicitly provided a non-matching scheme
            if "://" in url:
                return False

        # Check port
        effective_port = self.port if self.port is not None else pattern_port
        if effective_port is not None:
            actual_port = port or (443 if scheme == "https" else 80 if scheme == "http" else None)
            if actual_port != effective_port:
                return False

        # Safe regex for domain pattern (supports wildcards without regex injection)
        if host_pattern.startswith("*."):
            base_domain = host_pattern[2:]
            escaped_base = re.escape(base_domain).replace(r"\*", ".*")
            regex_host = rf"(?:.+\.)?{escaped_base}"
        else:
            regex_host = re.escape(host_pattern).replace(r"\*", ".*")
        if not re.match(f"^{regex_host}$", host, re.IGNORECASE):
            return False

        # Optional path wildcard check if pattern specifies a non-trivial path
        if path_pattern and path_pattern != "/":
            actual_path = parsed.path or "/"
            regex_path = re.escape(path_pattern).replace(r"\*", ".*")
            if not path_pattern.endswith("*"):
                regex_path += ".*"
            if not re.match(f"^{regex_path}$", actual_path, re.IGNORECASE):
                return False

        return True


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
