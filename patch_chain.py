import sys

with open('app/modules/chain_builder.py', 'r', encoding='utf-8') as f:
    content = f.read()

method = '''
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
'''

content = content.replace('        return detected_chains', '        return detected_chains\n' + method)

with open('app/modules/chain_builder.py', 'w', encoding='utf-8') as f:
    f.write(content)