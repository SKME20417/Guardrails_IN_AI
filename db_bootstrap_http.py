"""
Bootstrap tables via Supabase HTTP SQL endpoints.
Tries multiple API paths that Supabase may expose for SQL execution.
"""
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import httpx
import config

PROJECT_REF = config.SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")
BASE = config.SUPABASE_URL
SERVICE_KEY = config.SUPABASE_SERVICE_KEY
ANON_KEY = config.SUPABASE_KEY

SCHEMA_SQL = """
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS students CASCADE;

CREATE TABLE IF NOT EXISTS policyholders (
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
);

CREATE TABLE IF NOT EXISTS policies (
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
);

CREATE TABLE IF NOT EXISTS claims (
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
);

CREATE TABLE IF NOT EXISTS guardrail_logs (
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
);

CREATE INDEX IF NOT EXISTS idx_ph_email ON policyholders(email);
CREATE INDEX IF NOT EXISTS idx_ph_state ON policyholders(state);
CREATE INDEX IF NOT EXISTS idx_ph_active ON policyholders(is_active);
CREATE INDEX IF NOT EXISTS idx_pol_number ON policies(policy_number);
CREATE INDEX IF NOT EXISTS idx_pol_type ON policies(policy_type);
CREATE INDEX IF NOT EXISTS idx_claims_ph ON claims(policyholder_id);
CREATE INDEX IF NOT EXISTS idx_claims_pol ON claims(policy_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_type ON claims(claim_type);
CREATE INDEX IF NOT EXISTS idx_claims_fraud ON claims(fraud_flag);
CREATE INDEX IF NOT EXISTS idx_gl_session ON guardrail_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_gl_layer ON guardrail_logs(guardrail_layer);
CREATE INDEX IF NOT EXISTS idx_gl_ts ON guardrail_logs(timestamp);
"""

RPC_SQL = """
CREATE OR REPLACE FUNCTION execute_readonly_query(query_text TEXT)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE result JSONB;
BEGIN
    IF NOT (UPPER(TRIM(query_text)) LIKE 'SELECT%%') THEN
        RAISE EXCEPTION 'Only SELECT queries are allowed';
    END IF;
    EXECUTE 'SELECT COALESCE(jsonb_agg(row_to_json(t)), ''[]''::jsonb) FROM (' || query_text || ') t' INTO result;
    RETURN result;
END; $$;
"""


def try_endpoint(client, url, payload, desc):
    print(f"  [{desc}] POST {url[:80]}...", end=" ")
    try:
        r = client.post(url, json=payload, timeout=15)
        print(f"Status: {r.status_code}")
        if r.status_code < 300:
            print(f"    Response: {r.text[:200]}")
            return True
        else:
            print(f"    Error: {r.text[:150]}")
    except Exception as e:
        print(f"Exception: {str(e)[:80]}")
    return False


def main():
    print(f"Project: {PROJECT_REF}")
    print(f"Base URL: {BASE}\n")

    headers_service = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    client = httpx.Client(headers=headers_service, follow_redirects=True)

    endpoints = [
        (f"{BASE}/pg/query", {"query": "SELECT 1 as test"}, "pg/query with query key"),
        (f"{BASE}/pg/query", {"sql": "SELECT 1 as test"}, "pg/query with sql key"),
        (f"{BASE}/pg", {"query": "SELECT 1 as test"}, "pg root"),
        (f"{BASE}/rest/v1/rpc/exec_sql", {"sql": "SELECT 1 as test"}, "rpc/exec_sql"),
        (f"{BASE}/sql", {"query": "SELECT 1 as test"}, "sql endpoint"),
        (f"{BASE}/database/query", {"query": "SELECT 1 as test"}, "database/query"),
        (f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query", {"query": "SELECT 1 as test"}, "management API"),
    ]

    working_endpoint = None
    for url, payload, desc in endpoints:
        if try_endpoint(client, url, payload, desc):
            working_endpoint = (url, desc)
            break

    if working_endpoint:
        url, desc = working_endpoint
        print(f"\nWorking endpoint found: {desc}")
        print("Creating tables...")
        key = "query" if "query" in endpoints[0][1] else "sql"
        try_endpoint(client, url, {key: SCHEMA_SQL}, "CREATE TABLES")
        try_endpoint(client, url, {key: RPC_SQL}, "CREATE RPC FUNCTION")
        try_endpoint(client, url, {key: "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"}, "VERIFY")
    else:
        print("\nNo working SQL endpoint found via HTTP.")
        print("Please run the SQL manually in the Supabase SQL Editor.")
        print("Use: python create_tables.py  to print the SQL.")

    client.close()


if __name__ == "__main__":
    main()
