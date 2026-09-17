"""Report data models."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ReportPlatform(str, Enum):
    HACKERONE = "hackerone"
    BUGCROWD = "bugcrowd"
    YESWEHACK = "yeswehack"
    GENERIC = "generic"


class Report(BaseModel):
    """A generated vulnerability report."""
    id: str = ""
    vulnerability_id: str = ""
    platform: ReportPlatform = ReportPlatform.GENERIC
    title: str = ""
    content: str = ""
    format: str = "markdown"  # markdown, html
    created_at: datetime = Field(default_factory=datetime.now)
    exported: bool = False
    file_path: str = ""
