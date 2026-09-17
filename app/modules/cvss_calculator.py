"""
CVSS v3.1 Calculator Engine
Strict implementation of FIRST Common Vulnerability Scoring System v3.1 specifications.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
import math

# Metric Weights as per CVSS v3.1 Specification
AV_VALUES = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
AC_VALUES = {"L": 0.77, "H": 0.44}
PR_VALUES_UNCHANGED = {"N": 0.85, "L": 0.62, "H": 0.27}
PR_VALUES_CHANGED = {"N": 0.85, "L": 0.68, "H": 0.5}
UI_VALUES = {"N": 0.85, "R": 0.62}

CIA_VALUES = {"N": 0.0, "L": 0.22, "H": 0.56}

SEVERITY_LEVELS = [
    (0.0, "None"),
    (0.1, "Low"),
    (4.0, "Medium"),
    (7.0, "High"),
    (9.0, "Critical"),
]

DEFAULT_VECTORS = {
    "sqli": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",          # 9.8 Critical
    "rce": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",           # 9.8 Critical
    "ssrf": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N",          # 8.6 High
    "idor": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N",          # 8.1 High
    "xss": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",           # 6.1 Medium
    "csrf": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:H/A:N",          # 6.5 Medium
    "open_redirect": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N", # 6.1 Medium
    "cors": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:N/A:N",          # 6.5 Medium
    "jwt": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",           # 9.1 Critical
    "lfi": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",           # 7.5 High
}

def roundup(val: float) -> float:
    """Official CVSS v3.1 Roundup function."""
    int_val = round(val * 100000)
    if (int_val % 10000) == 0:
        return int_val / 100000.0
    return (math.floor(int_val / 10000.0) + 1) / 10.0

@dataclass
class CVSSResult:
    vector: str
    base_score: float
    severity: str
    exploitability_score: float
    impact_score: float
    metrics: Dict[str, str]

class CVSSCalculator:
    """Computes CVSS v3.1 Scores and Vectors."""

    @staticmethod
    def parse_vector(vector_str: str) -> Dict[str, str]:
        """Parses a CVSS:3.1 string into a dict of metrics."""
        parts = vector_str.strip().split("/")
        metrics = {}
        for part in parts:
            if ":" in part:
                k, v = part.split(":", 1)
                metrics[k.upper()] = v.upper()
        return metrics

    @staticmethod
    def get_severity(score: float) -> str:
        for threshold, name in reversed(SEVERITY_LEVELS):
            if score >= threshold:
                return name
        return "None"

    def calculate(
        self,
        av: str = "N",
        ac: str = "L",
        pr: str = "N",
        ui: str = "N",
        s: str = "U",
        c: str = "N",
        i: str = "N",
        a: str = "N",
    ) -> CVSSResult:
        """
        Calculate CVSS v3.1 base score from individual metrics.
        """
        av, ac, pr, ui, s, c, i, a = (
            av.upper(), ac.upper(), pr.upper(), ui.upper(),
            s.upper(), c.upper(), i.upper(), a.upper()
        )

        scope_changed = (s == "C")

        # Exploitability sub-score
        w_av = AV_VALUES.get(av, 0.85)
        w_ac = AC_VALUES.get(ac, 0.77)
        w_pr = (PR_VALUES_CHANGED if scope_changed else PR_VALUES_UNCHANGED).get(pr, 0.85)
        w_ui = UI_VALUES.get(ui, 0.85)

        exploitability = 8.22 * w_av * w_ac * w_pr * w_ui

        # ISS (Impact Sub-Score)
        w_c = CIA_VALUES.get(c, 0.0)
        w_i = CIA_VALUES.get(i, 0.0)
        w_a = CIA_VALUES.get(a, 0.0)

        iss = 1.0 - ((1.0 - w_c) * (1.0 - w_i) * (1.0 - w_a))

        # Impact
        if scope_changed:
            impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)
        else:
            impact = 6.42 * iss

        # Base Score
        if impact <= 0:
            base_score = 0.0
        else:
            if not scope_changed:
                base_score = roundup(min(impact + exploitability, 10.0))
            else:
                base_score = roundup(min(1.08 * (impact + exploitability), 10.0))

        vector = f"CVSS:3.1/AV:{av}/AC:{ac}/PR:{pr}/UI:{ui}/S:{s}/C:{c}/I:{i}/A:{a}"
        severity = self.get_severity(base_score)

        return CVSSResult(
            vector=vector,
            base_score=base_score,
            severity=severity,
            exploitability_score=round(exploitability, 2),
            impact_score=round(impact, 2),
            metrics={"AV": av, "AC": ac, "PR": pr, "UI": ui, "S": s, "C": c, "I": i, "A": a},
        )

    def calculate_from_vector(self, vector_str: str) -> CVSSResult:
        metrics = self.parse_vector(vector_str)
        return self.calculate(
            av=metrics.get("AV", "N"),
            ac=metrics.get("AC", "L"),
            pr=metrics.get("PR", "N"),
            ui=metrics.get("UI", "N"),
            s=metrics.get("S", "U"),
            c=metrics.get("C", "N"),
            i=metrics.get("I", "N"),
            a=metrics.get("A", "N"),
        )

    def get_default_vector(self, vuln_type: str) -> str:
        clean_type = vuln_type.lower().replace("-", "_").replace(" ", "_")
        for key, vec in DEFAULT_VECTORS.items():
            if key in clean_type:
                return vec
        return "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N"

cvss_calculator = CVSSCalculator()
