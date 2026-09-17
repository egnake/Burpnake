"""
Enhanced Markdown & SARIF Report Engine.
Generates submission-ready reports for HackerOne, Bugcrowd, YesWeHack, Intigriti, and SARIF 2.1.0.
"""
import base64
import json
from typing import Optional, Dict, Any

from app.modules.cvss_calculator import cvss_calculator
from app.modules.remediation_engine import remediation_engine


async def generate_report(finding: dict, exchange: dict, platform: str = "hackerone") -> str:
    try:
        from app.core.llm_gateway import llm_gateway

        title = finding.get("title", "Untitled Vulnerability")
        severity = finding.get("severity", "medium").capitalize()
        description = finding.get("description", "")
        steps = finding.get("steps_to_test", "")
        vuln_type = finding.get("interest_reason", "") or finding.get("vuln_type", "other")

        # Request / Response decoding
        try:
            req_text = base64.b64decode(exchange.get("request_b64", "")).decode("utf-8", errors="ignore")[:3000]
        except Exception:
            req_text = exchange.get("request_b64", "")[:500]

        try:
            res_text = base64.b64decode(exchange.get("response_b64", "")).decode("utf-8", errors="ignore")[:2000]
        except Exception:
            res_text = ""

        method = exchange.get("method", "GET")
        url = exchange.get("url", "") + exchange.get("path", "")

        # Taxonomy & Remediation Blueprint
        blueprint = remediation_engine.get_blueprint(vuln_type or title)

        # CVSS Calculation
        cvss_obj = None
        cvss_raw = finding.get("cvss_score") or finding.get("cvss_vector")
        if cvss_raw and "CVSS:3.1" in str(cvss_raw):
            try:
                cvss_obj = cvss_calculator.calculate_from_vector(str(cvss_raw))
            except Exception:
                pass

        if not cvss_obj:
            default_vec = cvss_calculator.get_default_vector(vuln_type or title)
            cvss_obj = cvss_calculator.calculate_from_vector(default_vec)

        # Impact and CoT from finding or AI
        impact = finding.get("impact", "")
        if not impact:
            try:
                ai_prompt = f"""Write an impact assessment for this vulnerability report:
Title: {title}
Severity: {severity}
Description: {description[:400]}

Provide 2-3 concise sentences detailing the realistic business and security impact to the affected organization."""
                impact = await llm_gateway.generate(ai_prompt)
            except Exception:
                impact = f"Exploitation of this {severity.lower()}-severity issue may compromise confidentiality and integrity of user and application data."

        # Steps formatting
        steps_formatted = ""
        if steps:
            lines = [l.strip() for l in steps.split("\n") if l.strip()]
            steps_formatted = "\n".join(
                f"{i+1}. {line}" for i, line in enumerate(lines) if not line[0].isdigit()
            ) or steps
        else:
            steps_formatted = "1. Intercept the request to the affected endpoint.\n2. Observe the missing validation or unauthenticated response.\n3. Verify that unauthorized state modification or information disclosure occurred."

        # Code remediation block
        remediation_code_block = ""
        if blueprint.code_examples:
            first_lang = list(blueprint.code_examples.keys())[0]
            first_code = blueprint.code_examples[first_lang]
            remediation_code_block = f"\n\n**Example Fix ({first_lang.capitalize()}):**\n```{first_lang}\n{first_code}\n```"

        # Platform Formatting
        if platform == "sarif":
            sarif_doc = {
                "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
                "version": "2.1.0",
                "runs": [{
                    "tool": {
                        "driver": {
                            "name": "BurpNake",
                            "semanticVersion": "2.0.0",
                            "informationUri": "https://github.com/burpnake/burpnake",
                            "rules": [{
                                "id": blueprint.cwe_id,
                                "name": blueprint.cwe_name,
                                "shortDescription": {"text": title},
                                "helpUri": blueprint.cwe_url,
                                "defaultConfiguration": {"level": "error" if severity in ["Critical", "High"] else "warning"}
                            }]
                        }
                    },
                    "results": [{
                        "ruleId": blueprint.cwe_id,
                        "level": "error" if severity in ["Critical", "High"] else "warning",
                        "message": {"text": f"{title}: {description[:200]}"},
                        "locations": [{
                            "physicalLocation": {
                                "artifactLocation": {"uri": url or "https://target.com/endpoint"}
                            }
                        }]
                    }]
                }]
            }
            return json.dumps(sarif_doc, indent=2)

        elif platform == "bugcrowd":
            return f"""### Description
{description}

### Proof of Concept
**Endpoint:** `{method} {url}`

**HTTP Request:**
```http
{req_text[:2000]}
```

**HTTP Response:**
```http
{res_text[:1000]}
```

### Steps to Reproduce
{steps_formatted}

### Severity & CVSS
**Severity:** {severity}
**CVSS Vector:** `{cvss_obj.vector}` (Base Score: **{cvss_obj.base_score}**)
**OWASP Category:** {blueprint.owasp_category}
**CWE:** [{blueprint.cwe_id} - {blueprint.cwe_name}]({blueprint.cwe_url})

### Impact
{impact}

### Recommended Remediation
{blueprint.guidance}{remediation_code_block}
"""

        elif platform == "yeswehack":
            return f"""## Vulnerability Description
{description}

## Technical Details & Endpoint
- Target: `{method} {url}`
- Classification: {blueprint.cwe_id} ({blueprint.cwe_name})
- CVSS v3.1: `{cvss_obj.vector}` (Score: {cvss_obj.base_score} {cvss_obj.severity})

## Proof of Concept
```http
{req_text[:2000]}
```

## Steps to Reproduce
{steps_formatted}

## Impact Assessment
{impact}

## Remediation
{blueprint.guidance}
"""

        elif platform == "intigriti":
            return f"""# {title}

## Summary
{description}

## Vulnerability Details
- **Affected URL:** `{method} {url}`
- **CWE:** {blueprint.cwe_id}: {blueprint.cwe_name}
- **OWASP:** {blueprint.owasp_category}
- **CVSS v3.1 Score:** {cvss_obj.base_score} ({cvss_obj.severity})
- **Vector:** `{cvss_obj.vector}`

## Step-by-step Reproduction
{steps_formatted}

## Proof of Concept
```http
{req_text[:2000]}
```

## Business Impact
{impact}

## Remediation & Mitigation
{blueprint.guidance}{remediation_code_block}
"""

        else:  # hackerone (default)
            return f"""## Summary
{description}

## Vulnerability Classification
- **CWE:** [{blueprint.cwe_id}: {blueprint.cwe_name}]({blueprint.cwe_url})
- **OWASP:** {blueprint.owasp_category}
- **Severity:** {severity}
- **CVSS v3.1 Score:** {cvss_obj.base_score} ({cvss_obj.severity}) — `{cvss_obj.vector}`

## Steps To Reproduce
{steps_formatted}

### HTTP Request
```http
{req_text[:2000]}
```

### HTTP Response Preview
```http
{res_text[:1000]}
```

## Impact
{impact}

## Remediation Guidance
{blueprint.guidance}{remediation_code_block}

## References
- [{blueprint.cwe_id} Definition]({blueprint.cwe_url})
- [OWASP Top 10 Web Application Security Risks](https://owasp.org/Top10/)
"""

    except Exception as e:
        return f"## {finding.get('title', 'Finding')}\n\n{finding.get('description', '')}\n\n*Rapor olusturma hatasi: {e}*"
