"""Print the full SQL to create all insurance tables, indexes, and RPC function.
Copy the output into the Supabase SQL Editor and run it."""
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

SCHEMA_SQL_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS policyholders (
        id BIGSERIAL PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        date_of_birth DATE,
        gender TEXT CHECK (gender IN ('Male','Female','Other')),
        address TEXT,
        city TEXT,
        state TEXT,
        zip_code TEXT,
        policy_start_date DATE NOT NULL DEFAULT CURRENT_DATE,
        policy_end_date DATE,
        premium_amount NUMERIC(10,2) DEFAULT 0.00,
        risk_score INTEGER CHECK (risk_score BETWEEN 1 AND 100),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS policies (
        id BIGSERIAL PRIMARY KEY,
        policy_number TEXT UNIQUE NOT NULL,
        policy_type TEXT NOT NULL CHECK (policy_type IN ('health','auto','life','property','travel')),
        provider_name TEXT NOT NULL,
        coverage_amount NUMERIC(12,2) NOT NULL,
        deductible NUMERIC(10,2) DEFAULT 0.00,
        premium_monthly NUMERIC(10,2) NOT NULL,
        tenure_months INTEGER NOT NULL DEFAULT 12,
        terms_summary TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS claims (
        id BIGSERIAL PRIMARY KEY,
        policyholder_id BIGINT REFERENCES policyholders(id),
        policy_id BIGINT REFERENCES policies(id),
        claim_number TEXT UNIQUE NOT NULL,
        claim_type TEXT NOT NULL CHECK (claim_type IN ('medical','collision','theft','property_damage','death_benefit','natural_disaster')),
        claim_amount NUMERIC(12,2) NOT NULL,
        approved_amount NUMERIC(12,2),
        status TEXT NOT NULL DEFAULT 'filed' CHECK (status IN ('filed','under_review','approved','denied','settled','fraud_flagged')),
        filed_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        resolved_date TIMESTAMPTZ,
        adjuster_name TEXT,
        fraud_flag BOOLEAN DEFAULT FALSE,
        denial_reason TEXT,
        notes TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS guardrail_logs (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT,
        timestamp TIMESTAMPTZ DEFAULT NOW(),
        user_input TEXT,
        sanitized_input TEXT,
        guardrail_layer TEXT NOT NULL,
        guardrail_name TEXT NOT NULL,
        action TEXT NOT NULL,
        details JSONB,
        tool_called TEXT,
        tool_allowed BOOLEAN,
        llm_raw_output TEXT,
        llm_final_output TEXT,
        hallucination_flag BOOLEAN DEFAULT FALSE,
        blocked BOOLEAN DEFAULT FALSE,
        execution_time_ms NUMERIC(10,2),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ph_email ON policyholders(email)",
    "CREATE INDEX IF NOT EXISTS idx_ph_state ON policyholders(state)",
    "CREATE INDEX IF NOT EXISTS idx_ph_active ON policyholders(is_active)",
    "CREATE INDEX IF NOT EXISTS idx_pol_number ON policies(policy_number)",
    "CREATE INDEX IF NOT EXISTS idx_pol_type ON policies(policy_type)",
    "CREATE INDEX IF NOT EXISTS idx_claims_ph ON claims(policyholder_id)",
    "CREATE INDEX IF NOT EXISTS idx_claims_pol ON claims(policy_id)",
    "CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status)",
    "CREATE INDEX IF NOT EXISTS idx_claims_type ON claims(claim_type)",
    "CREATE INDEX IF NOT EXISTS idx_claims_fraud ON claims(fraud_flag)",
    "CREATE INDEX IF NOT EXISTS idx_gl_session ON guardrail_logs(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_gl_layer ON guardrail_logs(guardrail_layer)",
    "CREATE INDEX IF NOT EXISTS idx_gl_ts ON guardrail_logs(timestamp)",
]

RPC_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION execute_readonly_query(query_text TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
BEGIN
    IF NOT (UPPER(TRIM(query_text)) LIKE 'SELECT%') THEN
        RAISE EXCEPTION 'Only SELECT queries are allowed';
    END IF;
    IF query_text ~* '\\b(DROP|ALTER|TRUNCATE|DELETE|UPDATE|INSERT|CREATE)\\b' THEN
        RAISE EXCEPTION 'Blocked SQL operation detected';
    END IF;
    EXECUTE 'SELECT COALESCE(jsonb_agg(row_to_json(t)), ''[]''::jsonb) FROM (' || query_text || ') t'
    INTO result;
    RETURN result;
END;
$$;
"""


def print_full_sql():
    print("=" * 70)
    print("  COPY ALL SQL BELOW INTO SUPABASE SQL EDITOR AND RUN IT")
    print("  (Dashboard -> SQL Editor -> New Query -> Paste -> Run)")
    print("=" * 70)
    print()
    for stmt in SCHEMA_SQL_STATEMENTS:
        print(stmt + ";")
        print()
    print(RPC_FUNCTION_SQL)
    print("=" * 70)


if __name__ == "__main__":
    print_full_sql()
