from __future__ import annotations

"""
Execution Layer Guardrail
Role-based tool access control and SQL validation.
Each role has a specific set of tools they can use.
"""

import re
from dataclasses import dataclass, field
import config
from guardrails.policy import ROLE_PERMISSIONS


@dataclass
class ExecutionCheckResult:
    passed: bool
    reason: str
    check_name: str
    details: dict = field(default_factory=dict)


class ExecutionGuardrail:

    def check_tool_access(self, tool_name: str, role: str = "agent") -> ExecutionCheckResult:
        perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["agent"])
        allowed_tools = perms.get("allowed_tools", set())
        blocked_tools = perms.get("blocked_tools", set())

        if tool_name in blocked_tools:
            return ExecutionCheckResult(
                passed=False,
                reason=f"Tool '{tool_name}' is blocked for role '{role}'. Allowed tools: {', '.join(sorted(allowed_tools))}.",
                check_name="tool_access",
                details={"tool": tool_name, "role": role, "blocked": True},
            )

        if tool_name not in allowed_tools:
            return ExecutionCheckResult(
                passed=False,
                reason=f"Tool '{tool_name}' is not permitted for role '{role}'. Allowed tools: {', '.join(sorted(allowed_tools))}.",
                check_name="tool_access",
                details={"tool": tool_name, "role": role, "allowed_tools": list(allowed_tools)},
            )

        return ExecutionCheckResult(
            passed=True,
            reason=f"Tool '{tool_name}' is allowed for role '{role}'.",
            check_name="tool_access",
            details={"tool": tool_name, "role": role},
        )

    def validate_sql(self, sql: str) -> list[ExecutionCheckResult]:
        results = []
        results.append(self._check_sql_type(sql))
        results.append(self._check_blocked_keywords(sql))
        results.append(self._check_table_access(sql))
        results.append(self._check_row_limit(sql))
        results.append(self._check_multiple_statements(sql))
        return results

    def is_sql_blocked(self, results: list[ExecutionCheckResult]) -> bool:
        return any(not r.passed for r in results)

    def _check_sql_type(self, sql: str) -> ExecutionCheckResult:
        stripped = sql.strip().upper()
        if not stripped.startswith("SELECT"):
            return ExecutionCheckResult(
                passed=False,
                reason="Only SELECT queries are allowed.",
                check_name="sql_type",
                details={"sql_start": stripped[:30]},
            )
        return ExecutionCheckResult(
            passed=True,
            reason="Query is a SELECT statement.",
            check_name="sql_type",
        )

    def _check_blocked_keywords(self, sql: str) -> ExecutionCheckResult:
        sql_upper = sql.upper()
        for op in config.BLOCKED_OPERATIONS:
            pattern = rf"\b{op}\b"
            if re.search(pattern, sql_upper):
                return ExecutionCheckResult(
                    passed=False,
                    reason=f"Blocked SQL operation detected: {op}",
                    check_name="blocked_keywords",
                    details={"operation": op},
                )
        return ExecutionCheckResult(
            passed=True,
            reason="No blocked SQL keywords found.",
            check_name="blocked_keywords",
        )

    def _check_table_access(self, sql: str) -> ExecutionCheckResult:
        sql_lower = sql.lower()
        from_match = re.findall(r"\bfrom\s+(\w+)", sql_lower)
        join_match = re.findall(r"\bjoin\s+(\w+)", sql_lower)
        referenced_tables = set(from_match + join_match)

        all_allowed = config.ALLOWED_TABLES | {"guardrail_logs"}
        unauthorized = referenced_tables - all_allowed
        if unauthorized:
            return ExecutionCheckResult(
                passed=False,
                reason=f"Unauthorized table access: {unauthorized}",
                check_name="table_access",
                details={"unauthorized_tables": list(unauthorized), "allowed": list(all_allowed)},
            )
        return ExecutionCheckResult(
            passed=True,
            reason="All referenced tables are allowed.",
            check_name="table_access",
            details={"tables": list(referenced_tables)},
        )

    def _check_row_limit(self, sql: str) -> ExecutionCheckResult:
        if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
            return ExecutionCheckResult(
                passed=False,
                reason=f"Query must include a LIMIT clause (max {config.MAX_QUERY_ROWS}).",
                check_name="row_limit",
                details={"max_rows": config.MAX_QUERY_ROWS},
            )

        limit_match = re.search(r"\bLIMIT\s+(\d+)", sql, re.IGNORECASE)
        if limit_match:
            limit_val = int(limit_match.group(1))
            if limit_val > config.MAX_QUERY_ROWS:
                return ExecutionCheckResult(
                    passed=False,
                    reason=f"LIMIT {limit_val} exceeds maximum of {config.MAX_QUERY_ROWS}.",
                    check_name="row_limit",
                    details={"requested": limit_val, "max": config.MAX_QUERY_ROWS},
                )

        return ExecutionCheckResult(
            passed=True,
            reason="Row limit is within bounds.",
            check_name="row_limit",
        )

    def _check_multiple_statements(self, sql: str) -> ExecutionCheckResult:
        cleaned = re.sub(r"'[^']*'", "", sql)
        if ";" in cleaned.rstrip(";").rstrip():
            return ExecutionCheckResult(
                passed=False,
                reason="Multiple SQL statements detected. Only single statements allowed.",
                check_name="multiple_statements",
            )
        return ExecutionCheckResult(
            passed=True,
            reason="Single statement validated.",
            check_name="multiple_statements",
        )
