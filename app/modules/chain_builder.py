import json
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.core.llm_gateway import llm_gateway

logger = logging.getLogger("burpnake.chain")

KNOWN_CHAINS = [
    # (Same as before)
    {
        "name": "OAuth Account Takeover",
        "requires": ["open_redirect", "oauth_csrf_missing_state"],
        "severity": "critical",
        "description": "Open Redirect + OAuth state eksikligi = Token theft ile hesap ele gecirme",
        "bounty_estimate": ",000 - ,000",
    },
    {
        "name": "SSRF to Cloud Takeover",
        "requires": ["ssrf_candidate", "cloud_metadata_ssrf_candidate"],
        "severity": "critical",
        "description": "SSRF ile cloud metadata erisimi = AWS/GCP key sizintisi ile tam kontrol",
        "bounty_estimate": ",000 - ,000",
    },
    {
        "name": "XSS to Account Takeover",
        "requires": ["xss_candidate", "cors_misconfig"],
        "severity": "critical",
        "description": "XSS + CORS misconfiguration = Cookie/token calma ile hesap ele gecirme",
        "bounty_estimate": ",000 - ,000",
    },
    {
        "name": "IDOR + Info Disclosure",
        "requires": ["idor_candidate", "sensitive_data_exposure"],
        "severity": "critical",
        "description": "IDOR ile diger kullanicilarin hassas verilerine erisim",
        "bounty_estimate": ",000 - ,000",
    }
]

@dataclass
class VulnChain:
    name: str
    severity: str
    description: str
    bounty_estimate: str
    matched_findings: List[Dict[str, Any]]
    required_vulns: List[str]
    matched_vulns: List[str]
    coverage: float
    poc_python: str = ""

class ChainBuilder:
    def analyze_chains(self, findings: List[Dict[str, Any]]) -> List[VulnChain]:
        all_vulns: set[str] = set()
        vuln_to_findings: Dict[str, List[Dict[str, Any]]] = {}
        
        for finding in findings:
            reason = finding.get("interest_reason", "") or finding.get("title", "")
            vulns = [v.strip() for v in reason.split(",") if v.strip()]
            for v in vulns:
                v_clean = v.strip().lower()
                all_vulns.add(v_clean)
                if v_clean not in vuln_to_findings:
                    vuln_to_findings[v_clean] = []
                vuln_to_findings[v_clean].append(finding)
        
        detected_chains: List[VulnChain] = []
        
        for chain_def in KNOWN_CHAINS:
            required = set(r.lower() for r in chain_def["requires"])
            matched = required & all_vulns
            coverage = len(matched) / len(required) if required else 0
            
            if coverage >= 0.5:
                matched_findings_list = []
                for v in matched:
                    matched_findings_list.extend(vuln_to_findings.get(v, []))
                
                chain = VulnChain(
                    name=chain_def["name"],
                    severity=chain_def["severity"],
                    description=chain_def["description"],
                    bounty_estimate=chain_def["bounty_estimate"],
                    matched_findings=matched_findings_list,
                    required_vulns=list(required),
                    matched_vulns=list(matched),
                    coverage=coverage,
                )
                detected_chains.append(chain)
        
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        detected_chains.sort(key=lambda c: (severity_order.get(c.severity, 0), c.coverage), reverse=True)
        return detected_chains

    def suggest_missing_vulns(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        all_vulns: set[str] = set()
        for finding in findings:
            reason = finding.get("interest_reason", "") or finding.get("title", "")
            for v in reason.split(","):
                all_vulns.add(v.strip().lower())
        
        suggestions = []
        for chain_def in KNOWN_CHAINS:
            required = set(r.lower() for r in chain_def["requires"])
            matched = required & all_vulns
            missing = required - all_vulns
            
            if matched and missing:
                suggestions.append({
                    "chain": chain_def["name"],
                    "have": list(matched),
                    "need": list(missing),
                    "severity_if_complete": chain_def["severity"],
                    "bounty_if_complete": chain_def["bounty_estimate"],
                    "hint": f"'{', '.join(matched)}' zafiyetiniz var. "
                            f"Eger '{', '.join(missing)}' da bulunursa -> {chain_def['name']} ({chain_def['severity'].upper()})",
                })
        return suggestions


class AIChainAgent:
    async def analyze_dynamic_chains(self, findings: List[Dict[str, Any]]) -> Optional[VulnChain]:
        if len(findings) < 2:
            return None
            
        summary = ""
        for f in findings:
            summary += f"- Title: {f.get('title', 'Unknown')}\n  Path: {f.get('path', 'Unknown')}\n  Details: {f.get('interest_reason', '')}\n"
            
        prompt = f'''You are BurpNake Chain Agent. Can you combine these isolated vulnerabilities into a single High/Critical exploit chain?
Findings:
{summary}

If YES, output ONLY a JSON:
{{
  "chain_possible": true,
  "name": "Chain Name (e.g. Account Takeover via XSS and CSRF)",
  "severity": "critical",
  "description": "How they combine",
  "bounty_estimate": "",
  "poc_python": "Python requests code demonstrating the multi-step chain"
}}
If NO, output {{"chain_possible": false}}.'''
        
        try:
            resp = await llm_gateway.generate([{"role": "user", "content": prompt}], temperature=0.2)
            import re
            m = re.search(r'\{[\s\S]*\}', resp)
            if m:
                data = json.loads(m.group())
                if data.get("chain_possible"):
                    return VulnChain(
                        name=data.get("name", "AI Discovered Chain"),
                        severity=data.get("severity", "high"),
                        description=data.get("description", ""),
                        bounty_estimate=data.get("bounty_estimate", ""),
                        matched_findings=findings,
                        required_vulns=[],
                        matched_vulns=[],
                        coverage=1.0,
                        poc_python=data.get("poc_python", "")
                    )
        except Exception as e:
            logger.error(f"[AIChain] Failed: {e}")
        return None

chain_builder = ChainBuilder()
ai_chain_agent = AIChainAgent()