from __future__ import annotations

"""
Input Layer Guardrail
Validates and sanitizes user input: length limits, SQL injection patterns,
prompt injection detection, PII detection, and role-based query restrictions.
"""

import re
from typing import Optional
from dataclasses import dataclass, field
import config


@dataclass
class InputCheckResult:
    passed: bool
    reason: str
    check_name: str
    sanitized_input: Optional[str] = None
    details: dict = field(default_factory=dict)


SQL_INJECTION_PATTERNS = [
    r"(?i)\b(union\s+select)\b",
    r"(?i)(\b(or|and)\b\s+[\'\"]?\d+[\'\"]?\s*=\s*[\'\"]?\d+)",
    r"(?i)(;\s*(drop|alter|truncate|delete|update|insert)\b)",
    r"(?i)(--\s|/\*|\*/)",
    r"(?i)\b(exec|execute|xp_|sp_)\b",
    r"(?i)(\bhaving\b\s+\d+\s*=\s*\d+)",
    r"(?i)(sleep\s*\(\s*\d+\s*\))",
    r"(?i)(benchmark\s*\()",
    r"(?i)(load_file|into\s+outfile|into\s+dumpfile)",
]

PROMPT_INJECTION_PATTERNS = [
    r"(?i)(ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?))",
    r"(?i)(you\s+are\s+now\s+(a|an|in)\s+)",
    r"(?i)(forget\s+(all\s+)?(your\s+)?(instructions?|rules?|training))",
    r"(?i)(system\s*:\s*)",
    r"(?i)(do\s+not\s+follow\s+(the\s+)?(rules?|instructions?|guidelines?))",
    r"(?i)(override\s+(your\s+)?(instructions?|safety|rules?))",
    r"(?i)(jailbreak|bypass\s+(the\s+)?(filter|guardrail|safety))",
    r"(?i)(pretend\s+(you\s+)?(are|to\s+be)\s+)",
    r"(?i)(act\s+(as|like)\s+(if\s+)?(you\s+)?(are|were|a|an)\s+)",
    r"(?i)(reveal\s+(your\s+)?(system\s+)?(prompt|instructions?))",
    r"(?i)(act\s+like\s+a\s+\w+)",
    r"(?i)(behave\s+(like|as)\s+(a|an)\s+)",
    r"(?i)(roleplay|role\s*-?\s*play)",
    r"(?i)(you\s+are\s+(a|an)\s+(?!insurance|database|assistant)\w+)",
]

PII_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "phone_us": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
}

CUSTOM_SQL_PATTERNS = [
    r"(?i)\bselect\b.*\bfrom\b",
    r"(?i)\bwhere\b.*\b(=|>|<|like|in)\b",
    r"(?i)\bjoin\b",
    r"(?i)\bgroup\s+by\b",
    r"(?i)\border\s+by\b",
    r"(?i)\bhaving\b",
    r"(?i)\blimit\b\s+\d+",
]


class InputGuardrail:

    def check_all(self, user_input: str, role: str = "agent") -> list[InputCheckResult]:
        results = []
        results.append(self.check_length(user_input))
        results.append(self.check_empty(user_input))
        results.append(self.check_sql_injection(user_input))
        results.append(self.check_prompt_injection(user_input))
        results.append(self.check_pii(user_input))
        results.append(self.check_raw_sql_attempt(user_input, role))
        return results

    def is_blocked(self, results: list[InputCheckResult]) -> bool:
        return any(not r.passed for r in results)

    def get_sanitized(self, user_input: str) -> str:
        sanitized = user_input.strip()
        sanitized = re.sub(r"[;]", "", sanitized)
        sanitized = re.sub(r"--.*$", "", sanitized, flags=re.MULTILINE)
        sanitized = re.sub(r"/\*.*?\*/", "", sanitized, flags=re.DOTALL)
        for pattern_name, pattern in PII_PATTERNS.items():
            sanitized = re.sub(pattern, f"[REDACTED_{pattern_name.upper()}]", sanitized)
        return sanitized

    def check_length(self, user_input: str) -> InputCheckResult:
        if len(user_input) > config.MAX_INPUT_LENGTH:
            return InputCheckResult(
                passed=False,
                reason=f"Input exceeds maximum length of {config.MAX_INPUT_LENGTH} characters ({len(user_input)}).",
                check_name="input_length",
                details={"length": len(user_input), "max": config.MAX_INPUT_LENGTH},
            )
        return InputCheckResult(
            passed=True,
            reason="Input length is within limits.",
            check_name="input_length",
            details={"length": len(user_input)},
        )

    def check_sql_injection(self, user_input: str) -> InputCheckResult:
        for pattern in SQL_INJECTION_PATTERNS:
            match = re.search(pattern, user_input)
            if match:
                return InputCheckResult(
                    passed=False,
                    reason=f"Potential SQL injection detected: '{match.group()}'",
                    check_name="sql_injection",
                    details={"matched_pattern": pattern, "matched_text": match.group()},
                )
        return InputCheckResult(
            passed=True,
            reason="No SQL injection patterns detected.",
            check_name="sql_injection",
        )

    def check_prompt_injection(self, user_input: str) -> InputCheckResult:
        for pattern in PROMPT_INJECTION_PATTERNS:
            match = re.search(pattern, user_input)
            if match:
                return InputCheckResult(
                    passed=False,
                    reason=f"Potential prompt injection detected: '{match.group()}'",
                    check_name="prompt_injection",
                    details={"matched_pattern": pattern, "matched_text": match.group()},
                )
        return InputCheckResult(
            passed=True,
            reason="No prompt injection patterns detected.",
            check_name="prompt_injection",
        )

    def check_pii(self, user_input: str) -> InputCheckResult:
        found_pii = {}
        for name, pattern in PII_PATTERNS.items():
            matches = re.findall(pattern, user_input)
            if matches:
                found_pii[name] = len(matches)

        if found_pii:
            return InputCheckResult(
                passed=True,
                reason=f"PII detected and will be redacted: {found_pii}",
                check_name="pii_detection",
                sanitized_input=self.get_sanitized(user_input),
                details={"pii_found": found_pii},
            )
        return InputCheckResult(
            passed=True,
            reason="No PII detected.",
            check_name="pii_detection",
        )

    def check_empty(self, user_input: str) -> InputCheckResult:
        if not user_input or not user_input.strip():
            return InputCheckResult(
                passed=False,
                reason="Input is empty.",
                check_name="empty_input",
            )
        return InputCheckResult(
            passed=True,
            reason="Input is not empty.",
            check_name="empty_input",
        )

    def check_raw_sql_attempt(self, user_input: str, role: str) -> InputCheckResult:
        if role == "auditor":
            return InputCheckResult(
                passed=True,
                reason="Auditor role can use custom SQL.",
                check_name="raw_sql_attempt",
                details={"role": role},
            )

        sql_indicators = 0
        for pattern in CUSTOM_SQL_PATTERNS:
            if re.search(pattern, user_input):
                sql_indicators += 1

        if sql_indicators >= 2:
            return InputCheckResult(
                passed=False,
                reason=f"Raw SQL queries are not allowed for role '{role}'. Please ask your question in natural language.",
                check_name="raw_sql_attempt",
                details={"role": role, "sql_indicators": sql_indicators},
            )

        return InputCheckResult(
            passed=True,
            reason="No raw SQL attempt detected.",
            check_name="raw_sql_attempt",
            details={"role": role},
        )
