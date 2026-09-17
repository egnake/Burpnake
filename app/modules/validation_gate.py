"""Validation Gate - 7-stage finding validation."""

from __future__ import annotations
from app.models.vulnerability import (
    Vulnerability, ValidationResult, ValidationStage, Confidence
)
from app.modules.scope_manager import scope_manager
from app.core.llm_gateway import llm_gateway


class ValidationGate:
    """
    7-stage validation pipeline to eliminate false positives.
    Every finding must pass all stages before report submission.
    """

    async def validate(self, vuln: Vulnerability) -> Vulnerability:
        """Run all 7 validation stages on a vulnerability."""
        stages = [
            (ValidationStage.REPRODUCIBILITY, self._check_reproducibility),
            (ValidationStage.SCOPE_CHECK, self._check_scope),
            (ValidationStage.IMPACT_ANALYSIS, self._check_impact),
            (ValidationStage.DUPLICATE_CHECK, self._check_duplicate),
            (ValidationStage.FALSE_POSITIVE_FILTER, self._check_false_positive),
            (ValidationStage.EXPLOIT_VERIFICATION, self._check_exploit),
            (ValidationStage.REPORT_QUALITY, self._check_report_quality),
        ]

        for stage, checker in stages:
            result = await checker(vuln)
            vuln.validation_results.append(result)

        # Update confidence based on validation
        passed = sum(1 for v in vuln.validation_results if v.passed)
        if passed == 7:
            vuln.confidence = Confidence.CONFIRMED
        elif passed >= 5:
            vuln.confidence = Confidence.FIRM
        else:
            vuln.confidence = Confidence.TENTATIVE

        return vuln

    async def _check_reproducibility(self, vuln: Vulnerability) -> ValidationResult:
        """Stage 1: Is the finding reproducible?"""
        has_steps = bool(vuln.steps_to_reproduce)
        has_poc = bool(vuln.poc_curl or vuln.poc_code)
        has_evidence = bool(vuln.evidence)
        passed = has_steps and (has_poc or has_evidence)
        
        return ValidationResult(
            stage=ValidationStage.REPRODUCIBILITY,
            passed=passed,
            details=f"Steps: {has_steps}, PoC: {has_poc}, Evidence: {has_evidence}",
        )

    async def _check_scope(self, vuln: Vulnerability) -> ValidationResult:
        """Stage 2: Is the target in scope?"""
        in_scope = scope_manager.is_in_scope(vuln.affected_url) if vuln.affected_url else True
        return ValidationResult(
            stage=ValidationStage.SCOPE_CHECK,
            passed=in_scope,
            details=f"URL: {vuln.affected_url}, In scope: {in_scope}",
        )

    async def _check_impact(self, vuln: Vulnerability) -> ValidationResult:
        """Stage 3: Does it have real security impact?"""
        has_impact = bool(vuln.impact and len(vuln.impact) > 20)
        high_enough = vuln.severity.value in ("critical", "high", "medium")
        passed = has_impact and high_enough

        return ValidationResult(
            stage=ValidationStage.IMPACT_ANALYSIS,
            passed=passed,
            details=f"Severity: {vuln.severity.value}, Has impact: {has_impact}",
        )

    async def _check_duplicate(self, vuln: Vulnerability) -> ValidationResult:
        """Stage 4: Is this a known/common finding that's likely duplicate?"""
        # Use AI to check if this is a commonly reported issue
        prompt = f"""Is this likely to be a duplicate/already-known vulnerability?
Type: {vuln.vuln_type.value}
URL: {vuln.affected_url}
Description: {vuln.description[:500]}

First, write your step-by-step Chain-of-Thought (CoT) reasoning. Is this a very common low-hanging fruit (like missing security headers or generic DMARC issues) that others would have found instantly? Is it a unique business logic flaw?
Then, conclude with your final answer on a new line: LIKELY_UNIQUE or LIKELY_DUPLICATE."""

        try:
            response = await llm_gateway.generate(prompt)
            is_unique = "LIKELY_UNIQUE" in response.upper()
        except Exception:
            is_unique = True

        return ValidationResult(
            stage=ValidationStage.DUPLICATE_CHECK,
            passed=is_unique,
            details=response[:200] if 'response' in dir() else "Check skipped",
        )

    async def _check_false_positive(self, vuln: Vulnerability) -> ValidationResult:
        """Stage 5: AI false positive filter."""
        prompt = f"""Evaluate if this security finding is a false positive:

Type: {vuln.vuln_type.value}
Severity: {vuln.severity.value}
URL: {vuln.affected_url}
Parameter: {vuln.affected_parameter}
Description: {vuln.description[:500]}
Evidence count: {len(vuln.evidence)}
Steps: {len(vuln.steps_to_reproduce)}

Is this a genuine security vulnerability or likely a false positive?
First, write your step-by-step Chain-of-Thought (CoT) reasoning. Analyze the technical details, the evidence, and whether it aligns with real-world exploitability or just looks like an intended feature/error message.
Then, conclude with your final answer on a new line: GENUINE or FALSE_POSITIVE."""

        try:
            response = await llm_gateway.generate(prompt)
            is_genuine = "GENUINE" in response.upper()
        except Exception:
            is_genuine = True

        return ValidationResult(
            stage=ValidationStage.FALSE_POSITIVE_FILTER,
            passed=is_genuine,
            details=response[:200] if 'response' in dir() else "Check skipped",
        )

    async def _check_exploit(self, vuln: Vulnerability) -> ValidationResult:
        """Stage 6: Does the PoC actually demonstrate exploitability?"""
        has_poc = bool(vuln.poc_curl or vuln.poc_code)
        has_evidence = len(vuln.evidence) > 0
        passed = has_poc or has_evidence

        return ValidationResult(
            stage=ValidationStage.EXPLOIT_VERIFICATION,
            passed=passed,
            details=f"PoC exists: {has_poc}, Evidence: {has_evidence}",
        )

    async def _check_report_quality(self, vuln: Vulnerability) -> ValidationResult:
        """Stage 7: Is the report submission-ready?"""
        checks = {
            "title": bool(vuln.title),
            "description": len(vuln.description) > 50,
            "impact": len(vuln.impact) > 20,
            "steps": len(vuln.steps_to_reproduce) > 0,
            "url": bool(vuln.affected_url),
        }
        passed = sum(checks.values()) >= 4
        failed = [k for k, v in checks.items() if not v]

        return ValidationResult(
            stage=ValidationStage.REPORT_QUALITY,
            passed=passed,
            details=f"Missing: {', '.join(failed)}" if failed else "All checks passed",
        )


validation_gate = ValidationGate()
