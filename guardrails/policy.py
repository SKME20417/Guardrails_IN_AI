from __future__ import annotations

"""
Policy Layer Guardrail
Strict role-based access control for the insurance claims system:
  - Agent: basic policyholder/policy info only, no claims, no sensitive fields
  - Claims Adjuster: full claims data + policyholder details, no fraud flags or risk scores
  - Auditor: full access to everything including fraud, risk scores, custom SQL, monitoring
"""

import time
import re
from dataclasses import dataclass, field
import config


@dataclass
class PolicyResult:
    allowed: bool
    reason: str
    policy_name: str
    details: dict = field(default_factory=dict)


ROLE_PERMISSIONS = {
    "agent": {
        "allowed_tables": {"policyholders", "policies"},
        "allowed_ops": {"SELECT"},
        "allowed_tools": {"query_policyholders", "query_policies"},
        "blocked_tools": {"query_claims", "get_table_schema", "run_custom_query"},
        "can_view_schema": False,
        "can_view_emails": False,
        "can_view_phone": False,
        "can_view_dob": False,
        "can_view_address": False,
        "can_view_premium": False,
        "can_view_risk_score": False,
        "can_view_financial": False,
        "can_view_claims": False,
        "can_view_fraud": False,
        "can_access_monitoring": False,
        "description": "Agent: can view basic policyholder names, city/state, and policy types. No claims, no PII, no financials.",
    },
    "claims_adjuster": {
        "allowed_tables": {"policyholders", "policies", "claims"},
        "allowed_ops": {"SELECT"},
        "allowed_tools": {"query_policyholders", "query_policies", "query_claims"},
        "blocked_tools": {"get_table_schema", "run_custom_query"},
        "can_view_schema": False,
        "can_view_emails": True,
        "can_view_phone": True,
        "can_view_dob": True,
        "can_view_address": True,
        "can_view_premium": True,
        "can_view_risk_score": False,
        "can_view_financial": True,
        "can_view_claims": True,
        "can_view_fraud": False,
        "can_access_monitoring": False,
        "description": "Claims Adjuster: full claims and policyholder data. No fraud flags, no risk scores, no schema, no custom SQL.",
    },
    "auditor": {
        "allowed_tables": {"policyholders", "policies", "claims", "guardrail_logs"},
        "allowed_ops": {"SELECT"},
        "allowed_tools": {"query_policyholders", "query_policies", "query_claims", "get_table_schema", "run_custom_query"},
        "blocked_tools": set(),
        "can_view_schema": True,
        "can_view_emails": True,
        "can_view_phone": True,
        "can_view_dob": True,
        "can_view_address": True,
        "can_view_premium": True,
        "can_view_risk_score": True,
        "can_view_financial": True,
        "can_view_claims": True,
        "can_view_fraud": True,
        "can_access_monitoring": True,
        "description": "Auditor: full access to all data, fraud flags, risk scores, schema, custom SQL, and monitoring logs.",
    },
}

SCHEMA_KEYWORDS = [
    "schema", "column", "columns", "structure", "table structure",
    "describe table", "table definition", "field", "fields",
    "data type", "datatype", "primary key", "foreign key",
]

SENSITIVE_DATA_KEYWORDS = {
    "email": ["email", "e-mail", "mail address", "contact email"],
    "phone": ["phone", "telephone", "mobile", "cell number", "contact number"],
    "dob": ["date of birth", "dob", "birthday", "birth date", "age"],
    "address": ["address", "street", "zip code", "zip_code", "postal"],
    "risk_score": ["risk score", "risk_score", "risk rating", "risk level", "risk assessment"],
    "fraud": ["fraud", "fraud_flag", "fraud flag", "fraudulent", "suspicious", "investigation"],
    "financial": ["premium", "coverage amount", "deductible", "claim amount", "approved amount", "payout", "settlement"],
}


class PolicyGuardrail:

    def __init__(self):
        self._request_timestamps: dict[str, list[float]] = {}
        self.rate_limit_window = 60
        self.rate_limit_max = 30

    def get_permissions(self, role: str) -> dict:
        return ROLE_PERMISSIONS.get(role, {})

    def check_all(self, user_input: str, role: str = "agent", session_id: str = "") -> list[PolicyResult]:
        results = []
        results.append(self.check_role_permission(role))
        results.append(self.check_rate_limit(session_id))
        results.append(self.check_schema_access(user_input, role))
        results.append(self.check_sensitive_data_access(user_input, role))
        results.append(self.check_table_access(user_input, role))
        results.append(self.check_operation_policy(user_input))
        return results

    def is_blocked(self, results: list[PolicyResult]) -> bool:
        return any(not r.allowed for r in results)

    def check_role_permission(self, role: str) -> PolicyResult:
        if role not in ROLE_PERMISSIONS:
            return PolicyResult(
                allowed=False,
                reason=f"Unknown role '{role}'. Access denied.",
                policy_name="role_permission",
                details={"role": role},
            )
        perms = ROLE_PERMISSIONS[role]
        return PolicyResult(
            allowed=True,
            reason=f"Role '{role}' recognized. {perms['description']}",
            policy_name="role_permission",
            details={"role": role},
        )

    def check_rate_limit(self, session_id: str) -> PolicyResult:
        now = time.time()
        if session_id not in self._request_timestamps:
            self._request_timestamps[session_id] = []

        self._request_timestamps[session_id] = [
            t for t in self._request_timestamps[session_id]
            if now - t < self.rate_limit_window
        ]

        if len(self._request_timestamps[session_id]) >= self.rate_limit_max:
            return PolicyResult(
                allowed=False,
                reason=f"Rate limit exceeded: {self.rate_limit_max} requests per {self.rate_limit_window}s.",
                policy_name="rate_limit",
                details={"count": len(self._request_timestamps[session_id])},
            )

        self._request_timestamps[session_id].append(now)
        return PolicyResult(
            allowed=True,
            reason="Within rate limit.",
            policy_name="rate_limit",
            details={"count": len(self._request_timestamps[session_id])},
        )

    def check_schema_access(self, user_input: str, role: str) -> PolicyResult:
        perms = ROLE_PERMISSIONS.get(role, {})
        if perms.get("can_view_schema", False):
            return PolicyResult(
                allowed=True,
                reason="Schema access permitted for this role.",
                policy_name="schema_access",
                details={"role": role},
            )

        input_lower = user_input.lower()
        for keyword in SCHEMA_KEYWORDS:
            if keyword in input_lower:
                return PolicyResult(
                    allowed=False,
                    reason=f"Schema/structure access denied for role '{role}'. Only auditors can view database schema details.",
                    policy_name="schema_access",
                    details={"role": role, "matched_keyword": keyword},
                )

        return PolicyResult(
            allowed=True,
            reason="No schema access attempted.",
            policy_name="schema_access",
            details={"role": role},
        )

    def check_sensitive_data_access(self, user_input: str, role: str) -> PolicyResult:
        perms = ROLE_PERMISSIONS.get(role, {})
        input_lower = user_input.lower()
        violations = []

        field_perm_map = {
            "email": "can_view_emails",
            "phone": "can_view_phone",
            "dob": "can_view_dob",
            "address": "can_view_address",
            "risk_score": "can_view_risk_score",
            "fraud": "can_view_fraud",
            "financial": "can_view_financial",
        }

        for field_name, perm_key in field_perm_map.items():
            if not perms.get(perm_key, False):
                for kw in SENSITIVE_DATA_KEYWORDS[field_name]:
                    if kw in input_lower:
                        violations.append(f"{field_name} data (matched: '{kw}')")
                        break

        if violations:
            return PolicyResult(
                allowed=False,
                reason=f"Access denied for role '{role}': cannot view {', '.join(violations)}. This data is restricted to authorized roles only.",
                policy_name="sensitive_data_access",
                details={"role": role, "violations": violations},
            )

        return PolicyResult(
            allowed=True,
            reason="No restricted sensitive data requested.",
            policy_name="sensitive_data_access",
            details={"role": role},
        )

    def check_table_access(self, user_input: str, role: str) -> PolicyResult:
        perms = ROLE_PERMISSIONS.get(role, {})
        allowed_tables = perms.get("allowed_tables", set())
        input_lower = user_input.lower()

        if ("guardrail_logs" in input_lower or "monitoring" in input_lower or "audit log" in input_lower) and not perms.get("can_access_monitoring", False):
            return PolicyResult(
                allowed=False,
                reason=f"Access to monitoring/audit data denied for role '{role}'. Only auditors can view system logs.",
                policy_name="table_access",
                details={"role": role, "attempted_table": "guardrail_logs"},
            )

        claim_keywords = ["claim", "claims", "filed", "adjuster", "denied", "approved amount", "settled"]
        if any(kw in input_lower for kw in claim_keywords) and "claims" not in allowed_tables:
            return PolicyResult(
                allowed=False,
                reason=f"Access to claims data denied for role '{role}'. You can only view policyholder and policy information.",
                policy_name="table_access",
                details={"role": role, "attempted_table": "claims"},
            )

        return PolicyResult(
            allowed=True,
            reason="Table access check passed.",
            policy_name="table_access",
            details={"role": role, "allowed_tables": list(allowed_tables)},
        )

    def check_operation_policy(self, user_input: str) -> PolicyResult:
        input_upper = user_input.upper()
        for op in config.BLOCKED_OPERATIONS:
            if re.search(rf"\b{op}\b", input_upper):
                return PolicyResult(
                    allowed=False,
                    reason=f"Operation '{op}' is blocked by policy. Only read operations are allowed.",
                    policy_name="operation_policy",
                    details={"blocked_operation": op},
                )
        return PolicyResult(
            allowed=True,
            reason="No blocked operations detected.",
            policy_name="operation_policy",
            details={},
        )
