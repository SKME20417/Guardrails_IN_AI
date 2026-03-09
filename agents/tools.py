from __future__ import annotations

"""
LangChain tools for the insurance claims database agent.
Each tool queries Supabase and returns structured results.
"""

from langchain.tools import tool
from database.connection import get_client
import config


@tool
def query_policyholders(query_filter: str = "") -> str:
    """Query the policyholders table. Accepts a natural language filter description.
    Returns policyholder records matching the criteria.
    Examples: 'all active policyholders', 'policyholders in New York',
    'policyholders with high risk scores'."""
    client = get_client()
    q = client.table("policyholders").select("*")

    fl = query_filter.lower()
    if "active" in fl and "inactive" not in fl:
        q = q.eq("is_active", True)
    if "inactive" in fl:
        q = q.eq("is_active", False)

    states = [
        "New York", "California", "Texas", "Florida", "Illinois",
        "Pennsylvania", "Ohio", "Georgia", "Michigan", "North Carolina",
    ]
    for s in states:
        if s.lower() in fl:
            q = q.eq("state", s)
            break

    genders = ["Male", "Female", "Other"]
    for g in genders:
        if g.lower() in fl:
            q = q.eq("gender", g)
            break

    q = q.limit(config.MAX_QUERY_ROWS)
    result = q.execute()
    rows = result.data
    if not rows:
        return "No policyholders found matching the criteria."
    return f"Found {len(rows)} policyholder(s):\n" + "\n".join(
        f"- {r['first_name']} {r['last_name']} | City: {r['city']}, {r['state']} | "
        f"Premium: ${r['premium_amount']} | Risk Score: {r['risk_score']} | Active: {r['is_active']}"
        for r in rows
    )


@tool
def query_policies(query_filter: str = "") -> str:
    """Query the policies table. Accepts a natural language filter description.
    Returns insurance policy records matching the criteria.
    Examples: 'all health policies', 'active auto policies',
    'policies with coverage above 100000'."""
    client = get_client()
    q = client.table("policies").select("*")

    fl = query_filter.lower()
    if "active" in fl:
        q = q.eq("is_active", True)

    for ptype in ["health", "auto", "life", "property", "travel"]:
        if ptype in fl:
            q = q.eq("policy_type", ptype)
            break

    providers = [
        "SafeGuard", "National Shield", "TrustLife", "PrimeCover",
        "AllState", "Pinnacle", "Horizon", "Liberty", "BlueCross",
        "Evergreen", "Patriot", "Summit",
    ]
    for p in providers:
        if p.lower() in fl:
            q = q.ilike("provider_name", f"%{p}%")
            break

    q = q.limit(config.MAX_QUERY_ROWS)
    result = q.execute()
    rows = result.data
    if not rows:
        return "No policies found matching the criteria."
    return f"Found {len(rows)} policy(ies):\n" + "\n".join(
        f"- {r['policy_number']}: {r['policy_type'].upper()} | Provider: {r['provider_name']} | "
        f"Coverage: ${r['coverage_amount']} | Deductible: ${r['deductible']} | "
        f"Monthly: ${r['premium_monthly']} | Tenure: {r['tenure_months']}mo | Active: {r['is_active']}"
        for r in rows
    )


@tool
def query_claims(query_filter: str = "") -> str:
    """Query the claims table. Accepts a natural language filter description.
    Returns insurance claims matching the criteria.
    Examples: 'all approved claims', 'medical claims', 'fraud flagged claims',
    'denied claims', 'claims under review'."""
    client = get_client()
    q = client.table("claims").select(
        "*, policyholders(first_name, last_name), policies(policy_number, policy_type)"
    )

    fl = query_filter.lower()

    for ctype in ["medical", "collision", "theft", "property_damage", "death_benefit", "natural_disaster"]:
        if ctype.replace("_", " ") in fl or ctype in fl:
            q = q.eq("claim_type", ctype)
            break

    for status in ["filed", "under_review", "approved", "denied", "settled", "fraud_flagged"]:
        if status.replace("_", " ") in fl or status in fl:
            q = q.eq("status", status)
            break

    if "fraud" in fl:
        q = q.eq("fraud_flag", True)

    q = q.limit(config.MAX_QUERY_ROWS)
    result = q.execute()
    rows = result.data
    if not rows:
        return "No claims found matching the criteria."
    return f"Found {len(rows)} claim(s):\n" + "\n".join(
        f"- {r['claim_number']}: {r['claim_type']} | "
        f"Policyholder: {r.get('policyholders', {}).get('first_name', 'N/A')} {r.get('policyholders', {}).get('last_name', '')} | "
        f"Policy: {r.get('policies', {}).get('policy_number', 'N/A')} ({r.get('policies', {}).get('policy_type', '')}) | "
        f"Amount: ${r['claim_amount']} | Approved: ${r['approved_amount'] or 'N/A'} | "
        f"Status: {r['status']} | Fraud: {r['fraud_flag']} | Adjuster: {r['adjuster_name']}"
        for r in rows
    )


@tool
def get_table_schema(table_name: str) -> str:
    """Get the schema/column info for a given table.
    Allowed tables: policyholders, policies, claims."""
    schemas = {
        "policyholders": (
            "Table: policyholders\n"
            "Columns: id (bigint PK), first_name (text), last_name (text), "
            "email (text unique), phone (text), date_of_birth (date), gender (text), "
            "address (text), city (text), state (text), zip_code (text), "
            "policy_start_date (date), policy_end_date (date), premium_amount (numeric 10,2), "
            "risk_score (integer 1-100), is_active (boolean), created_at (timestamptz)"
        ),
        "policies": (
            "Table: policies\n"
            "Columns: id (bigint PK), policy_number (text unique), policy_type (text: health/auto/life/property/travel), "
            "provider_name (text), coverage_amount (numeric 12,2), deductible (numeric 10,2), "
            "premium_monthly (numeric 10,2), tenure_months (integer), terms_summary (text), "
            "is_active (boolean), created_at (timestamptz)"
        ),
        "claims": (
            "Table: claims\n"
            "Columns: id (bigint PK), policyholder_id (bigint FK->policyholders), "
            "policy_id (bigint FK->policies), claim_number (text unique), "
            "claim_type (text: medical/collision/theft/property_damage/death_benefit/natural_disaster), "
            "claim_amount (numeric 12,2), approved_amount (numeric 12,2), "
            "status (text: filed/under_review/approved/denied/settled/fraud_flagged), "
            "filed_date (timestamptz), resolved_date (timestamptz), adjuster_name (text), "
            "fraud_flag (boolean), denial_reason (text), notes (text), created_at (timestamptz)"
        ),
    }
    if table_name.lower() not in schemas:
        return f"Table '{table_name}' not found. Available tables: policyholders, policies, claims."
    return schemas[table_name.lower()]


@tool
def run_custom_query(sql: str) -> str:
    """Execute a custom SELECT SQL query against the database.
    ONLY SELECT queries with LIMIT are allowed. Maximum LIMIT is 100.
    The query must only reference tables: policyholders, policies, claims.
    Example: SELECT policy_type, COUNT(*) as count FROM policies GROUP BY policy_type LIMIT 20"""
    from guardrails.execution import ExecutionGuardrail

    exec_guard = ExecutionGuardrail()
    checks = exec_guard.validate_sql(sql)
    if exec_guard.is_sql_blocked(checks):
        reasons = [c.reason for c in checks if not c.passed]
        return f"Query blocked by execution guardrail: {'; '.join(reasons)}"

    try:
        client = get_client()
        result = client.rpc("execute_readonly_query", {"query_text": sql}).execute()
        rows = result.data
        if not rows:
            return "Query returned no results."
        header = " | ".join(rows[0].keys())
        lines = [header, "-" * len(header)]
        for r in rows:
            lines.append(" | ".join(str(v) for v in r.values()))
        return f"Query returned {len(rows)} row(s):\n" + "\n".join(lines)
    except Exception as e:
        return f"Query execution error: {str(e)}"


ALL_TOOLS = [query_policyholders, query_policies, query_claims, get_table_schema, run_custom_query]
