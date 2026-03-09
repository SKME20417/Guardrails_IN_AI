from __future__ import annotations

"""
Output Layer Guardrail
Role-aware output filtering for insurance claims system: strips sensitive data
from responses based on what the current role is allowed to see.
"""

import re
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from guardrails.policy import ROLE_PERMISSIONS


@dataclass
class OutputCheckResult:
    passed: bool
    reason: str
    check_name: str
    filtered_output: Optional[str] = None
    details: dict = field(default_factory=dict)


SENSITIVE_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "api_key": r"(?i)(api[_-]?key|secret[_-]?key|token)\s*[:=]\s*\S+",
    "password": r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+",
}


class OutputGuardrail:

    def check_all(self, llm_output: str, role: str = "agent", query_data: Optional[List[Dict]] = None) -> List[OutputCheckResult]:
        results = []
        results.append(self.check_sensitive_data(llm_output))
        results.append(self.filter_by_role(llm_output, role))
        results.append(self.check_hallucination(llm_output, query_data))
        results.append(self.check_response_length(llm_output))
        results.append(self.check_refusal_leak(llm_output))
        return results

    def is_blocked(self, results: list[OutputCheckResult]) -> bool:
        return any(not r.passed for r in results)

    def get_filtered_output(self, llm_output: str) -> str:
        filtered = llm_output
        for name, pattern in SENSITIVE_PATTERNS.items():
            filtered = re.sub(pattern, f"[REDACTED_{name.upper()}]", filtered)
        return filtered

    def check_sensitive_data(self, llm_output: str) -> OutputCheckResult:
        found = {}
        for name, pattern in SENSITIVE_PATTERNS.items():
            matches = re.findall(pattern, llm_output)
            if matches:
                found[name] = len(matches)

        if found:
            return OutputCheckResult(
                passed=False,
                reason=f"Sensitive data detected in output and redacted: {found}",
                check_name="sensitive_data",
                filtered_output=self.get_filtered_output(llm_output),
                details={"found": found},
            )
        return OutputCheckResult(
            passed=True,
            reason="No sensitive data patterns detected in output.",
            check_name="sensitive_data",
        )

    def filter_by_role(self, llm_output: str, role: str) -> OutputCheckResult:
        perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["agent"])
        filtered = llm_output
        redactions = []

        if not perms.get("can_view_emails", False):
            email_pattern = r"[\w.+-]+@[\w-]+\.[\w.-]+"
            emails_found = re.findall(email_pattern, filtered)
            if emails_found:
                filtered = re.sub(email_pattern, "[EMAIL HIDDEN - restricted for your role]", filtered)
                redactions.append(f"emails ({len(emails_found)} redacted)")

        if not perms.get("can_view_phone", False):
            phone_patterns = [
                r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
                r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
            ]
            for pp in phone_patterns:
                phones_found = re.findall(pp, filtered)
                if phones_found:
                    filtered = re.sub(pp, "[PHONE HIDDEN]", filtered)
                    redactions.append(f"phone numbers ({len(phones_found)} redacted)")

        if not perms.get("can_view_dob", False):
            dob_patterns = [
                r"\b\d{4}-\d{2}-\d{2}\b",
                r"\b\d{2}/\d{2}/\d{4}\b",
            ]
            for dp in dob_patterns:
                dates_found = re.findall(dp, filtered)
                if dates_found:
                    filtered = re.sub(dp, "[DATE HIDDEN]", filtered)
                    redactions.append(f"dates ({len(dates_found)} redacted)")

        if not perms.get("can_view_financial", False):
            money_pattern = r"\$[\d,]+\.?\d*"
            money_found = re.findall(money_pattern, filtered)
            if money_found:
                filtered = re.sub(money_pattern, "[AMOUNT HIDDEN]", filtered)
                redactions.append(f"financial amounts ({len(money_found)} redacted)")

        if not perms.get("can_view_risk_score", False):
            risk_pattern = r"(?i)(risk\s*score\s*[:=]?\s*\d+|\brisk[:\s]+\d+)"
            risk_found = re.findall(risk_pattern, filtered)
            if risk_found:
                filtered = re.sub(risk_pattern, "[RISK SCORE HIDDEN]", filtered)
                redactions.append(f"risk scores ({len(risk_found)} redacted)")

        if not perms.get("can_view_fraud", False):
            fraud_pattern = r"(?i)(fraud[_\s]*(flag|flagged)?[:\s]*(true|yes|positive|detected|suspected))"
            fraud_found = re.findall(fraud_pattern, filtered)
            if fraud_found:
                filtered = re.sub(fraud_pattern, "[FRAUD DATA HIDDEN]", filtered)
                redactions.append(f"fraud flags ({len(fraud_found)} redacted)")

        if not perms.get("can_view_schema", False):
            schema_indicators = [
                r"(?i)(bigserial|bigint|timestamptz|numeric\(\d+,\d+\))",
                r"(?i)(primary\s+key|foreign\s+key|references\s+\w+)",
                r"(?i)(default\s+(now\(\)|current_date|true|false|0\.00))",
                r"(?i)(table:\s*\w+\s*\ncolumns?:)",
            ]
            for sp in schema_indicators:
                if re.search(sp, filtered):
                    filtered = f"Schema information is restricted for role '{role}'. Only auditors can view database structure details."
                    redactions.append("schema details blocked")
                    break

        if redactions:
            return OutputCheckResult(
                passed=False,
                reason=f"Output filtered for role '{role}': {', '.join(redactions)}",
                check_name="role_based_filtering",
                filtered_output=filtered,
                details={"role": role, "redactions": redactions},
            )

        return OutputCheckResult(
            passed=True,
            reason=f"Output is clean for role '{role}' — no restricted data found.",
            check_name="role_based_filtering",
            details={"role": role},
        )

    def check_hallucination(self, llm_output: str, query_data: Optional[List[Dict]] = None) -> OutputCheckResult:
        hallucination_indicators = []

        fabrication_phrases = [
            r"(?i)(as\s+of\s+my\s+(last\s+)?training)",
            r"(?i)(i\s+don'?t\s+have\s+access\s+to\s+(real|actual|live)\s+data)",
            r"(?i)(based\s+on\s+my\s+knowledge)",
            r"(?i)(i\s+cannot\s+verify)",
        ]

        for pattern in fabrication_phrases:
            if re.search(pattern, llm_output):
                hallucination_indicators.append(f"Fabrication indicator: {pattern}")

        if query_data is not None and len(query_data) == 0:
            number_pattern = r"\b\d{2,}\b"
            numbers_in_output = re.findall(number_pattern, llm_output)
            if len(numbers_in_output) > 3:
                hallucination_indicators.append(
                    "LLM output contains specific numbers but query returned no data"
                )

        if hallucination_indicators:
            return OutputCheckResult(
                passed=False,
                reason=f"Possible hallucination detected: {'; '.join(hallucination_indicators)}",
                check_name="hallucination_detection",
                details={"indicators": hallucination_indicators},
            )

        return OutputCheckResult(
            passed=True,
            reason="No hallucination indicators found.",
            check_name="hallucination_detection",
        )

    def check_response_length(self, llm_output: str) -> OutputCheckResult:
        max_length = 10000
        if len(llm_output) > max_length:
            return OutputCheckResult(
                passed=False,
                reason=f"Response too long ({len(llm_output)} chars). Truncated to {max_length}.",
                check_name="response_length",
                filtered_output=llm_output[:max_length] + "\n\n[Response truncated]",
                details={"length": len(llm_output), "max": max_length},
            )
        return OutputCheckResult(
            passed=True,
            reason="Response length is within limits.",
            check_name="response_length",
            details={"length": len(llm_output)},
        )

    def check_refusal_leak(self, llm_output: str) -> OutputCheckResult:
        leak_patterns = [
            r"(?i)(my\s+system\s+prompt\s+(is|says|reads))",
            r"(?i)(here\s+(is|are)\s+my\s+instructions?)",
            r"(?i)(i\s+was\s+told\s+to\s+never)",
            r"(?i)(my\s+rules?\s+(state|say|are))",
        ]
        for pattern in leak_patterns:
            if re.search(pattern, llm_output):
                return OutputCheckResult(
                    passed=False,
                    reason="Output may be leaking system instructions.",
                    check_name="refusal_leak",
                    filtered_output="I'm an insurance database assistant. How can I help you with policyholder, policy, or claims data?",
                    details={"pattern": pattern},
                )
        return OutputCheckResult(
            passed=True,
            reason="No system instruction leakage detected.",
            check_name="refusal_leak",
        )
