"""
Bootstrap: create all insurance tables and RPC function via direct PostgreSQL connection.
Tries multiple Supabase connection methods automatically.
"""
import sys, os
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import psycopg2
import config

PROJECT_REF = config.SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")

CONNECTION_ATTEMPTS = [
    {
        "desc": "Direct connection (session mode via pooler, port 5432)",
        "host": f"aws-0-ap-south-1.pooler.supabase.com",
        "port": 5432,
        "user": f"postgres.{PROJECT_REF}",
        "password": config.SUPABASE_SERVICE_KEY,
        "dbname": "postgres",
    },
    {
        "desc": "Transaction mode pooler (port 6543)",
        "host": f"aws-0-ap-south-1.pooler.supabase.com",
        "port": 6543,
        "user": f"postgres.{PROJECT_REF}",
        "password": config.SUPABASE_SERVICE_KEY,
        "dbname": "postgres",
    },
    {
        "desc": "Direct DB host",
        "host": f"db.{PROJECT_REF}.supabase.co",
        "port": 5432,
        "user": "postgres",
        "password": config.SUPABASE_SERVICE_KEY,
        "dbname": "postgres",
    },
    {
        "desc": "Pooler us-east-1 session",
        "host": f"aws-0-us-east-1.pooler.supabase.com",
        "port": 5432,
        "user": f"postgres.{PROJECT_REF}",
        "password": config.SUPABASE_SERVICE_KEY,
        "dbname": "postgres",
    },
    {
        "desc": "Pooler us-east-1 transaction",
        "host": f"aws-0-us-east-1.pooler.supabase.com",
        "port": 6543,
        "user": f"postgres.{PROJECT_REF}",
        "password": config.SUPABASE_SERVICE_KEY,
        "dbname": "postgres",
    },
    {
        "desc": "Pooler us-west-1 session",
        "host": f"aws-0-us-west-1.pooler.supabase.com",
        "port": 5432,
        "user": f"postgres.{PROJECT_REF}",
        "password": config.SUPABASE_SERVICE_KEY,
        "dbname": "postgres",
    },
    {
        "desc": "Pooler eu-west-1 session",
        "host": f"aws-0-eu-west-1.pooler.supabase.com",
        "port": 5432,
        "user": f"postgres.{PROJECT_REF}",
        "password": config.SUPABASE_SERVICE_KEY,
        "dbname": "postgres",
    },
    {
        "desc": "Pooler eu-central-1 session",
        "host": f"aws-0-eu-central-1.pooler.supabase.com",
        "port": 5432,
        "user": f"postgres.{PROJECT_REF}",
        "password": config.SUPABASE_SERVICE_KEY,
        "dbname": "postgres",
    },
    {
        "desc": "Pooler ap-southeast-1 session",
        "host": f"aws-0-ap-southeast-1.pooler.supabase.com",
        "port": 5432,
        "user": f"postgres.{PROJECT_REF}",
        "password": config.SUPABASE_SERVICE_KEY,
        "dbname": "postgres",
    },
]

if config.SUPABASE_KEY and not config.SUPABASE_KEY.startswith("ey"):
    for region in ["ap-south-1", "us-east-1"]:
        CONNECTION_ATTEMPTS.append({
            "desc": f"Pooler {region} with publishable key as password",
            "host": f"aws-0-{region}.pooler.supabase.com",
            "port": 5432,
            "user": f"postgres.{PROJECT_REF}",
            "password": config.SUPABASE_KEY,
            "dbname": "postgres",
        })


SCHEMA_SQL = """
-- Drop old university tables if they exist
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS students CASCADE;

-- Insurance tables
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

CREATE OR REPLACE FUNCTION execute_readonly_query(query_text TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
BEGIN
    IF NOT (UPPER(TRIM(query_text)) LIKE 'SELECT%%') THEN
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


def try_connect():
    for attempt in CONNECTION_ATTEMPTS:
        desc = attempt.pop("desc")
        print(f"  Trying: {desc} ({attempt['host']}:{attempt['port']})...", end=" ")
        try:
            conn = psycopg2.connect(**attempt, connect_timeout=8, sslmode="require")
            print("CONNECTED!")
            return conn
        except Exception as e:
            err_msg = str(e).strip().split('\n')[0][:80]
            print(f"failed ({err_msg})")
        finally:
            attempt["desc"] = desc
    return None


def create_tables(conn):
    print("\nCreating insurance tables...")
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    conn.commit()
    print("  All tables, indexes, and RPC function created successfully.")


def verify_tables(conn):
    print("\nVerifying tables...")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('policyholders', 'policies', 'claims', 'guardrail_logs')
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]
    print(f"  Found tables: {tables}")
    return tables


if __name__ == "__main__":
    print(f"Project ref: {PROJECT_REF}")
    print(f"Trying to connect to Supabase PostgreSQL...\n")

    conn = try_connect()
    if conn is None:
        print("\nAll connection attempts failed.")
        print("Please provide your Supabase database password, or run the SQL manually.")
        print("Use: python create_tables.py  to print the SQL you can paste into the SQL Editor.")
        sys.exit(1)

    try:
        create_tables(conn)
        tables = verify_tables(conn)
        if len(tables) == 4:
            print("\nAll 4 tables created. Ready to seed data!")
            print("Run: python -m database.seed")
        else:
            print(f"\nWARNING: Expected 4 tables, found {len(tables)}.")
    finally:
        conn.close()
