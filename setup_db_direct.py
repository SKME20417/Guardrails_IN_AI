"""
Direct database setup using pg8000 (pure Python PostgreSQL driver).
Creates all insurance tables, indexes, and RPC function.
Tries multiple connection methods (pooler, direct, different regions).
"""
import sys
sys.path.insert(0, ".")
import pg8000

PROJECT_REF = "bpxtsjrenboigecjqopr"
DB_PASS = "iZNnuN9SOl4aq9fS"

CONNECTION_ATTEMPTS = [
    {"desc": "Pooler ap-south-1 session (5432)", "host": "aws-0-ap-south-1.pooler.supabase.com", "port": 5432, "user": f"postgres.{PROJECT_REF}"},
    {"desc": "Pooler ap-south-1 transaction (6543)", "host": "aws-0-ap-south-1.pooler.supabase.com", "port": 6543, "user": f"postgres.{PROJECT_REF}"},
    {"desc": "Direct DB host (5432)", "host": f"db.{PROJECT_REF}.supabase.co", "port": 5432, "user": "postgres"},
    {"desc": "Pooler us-east-1 session", "host": "aws-0-us-east-1.pooler.supabase.com", "port": 5432, "user": f"postgres.{PROJECT_REF}"},
    {"desc": "Pooler us-east-1 transaction", "host": "aws-0-us-east-1.pooler.supabase.com", "port": 6543, "user": f"postgres.{PROJECT_REF}"},
    {"desc": "Pooler us-west-1 session", "host": "aws-0-us-west-1.pooler.supabase.com", "port": 5432, "user": f"postgres.{PROJECT_REF}"},
    {"desc": "Pooler eu-central-1 session", "host": "aws-0-eu-central-1.pooler.supabase.com", "port": 5432, "user": f"postgres.{PROJECT_REF}"},
    {"desc": "Pooler eu-west-1 session", "host": "aws-0-eu-west-1.pooler.supabase.com", "port": 5432, "user": f"postgres.{PROJECT_REF}"},
    {"desc": "Pooler ap-southeast-1 session", "host": "aws-0-ap-southeast-1.pooler.supabase.com", "port": 5432, "user": f"postgres.{PROJECT_REF}"},
    {"desc": "Pooler ap-southeast-1 transaction", "host": "aws-0-ap-southeast-1.pooler.supabase.com", "port": 6543, "user": f"postgres.{PROJECT_REF}"},
]

STATEMENTS = [
    "DROP TABLE IF EXISTS transactions CASCADE",
    "DROP TABLE IF EXISTS courses CASCADE",
    "DROP TABLE IF EXISTS students CASCADE",
    "DROP TABLE IF EXISTS claims CASCADE",
    "DROP TABLE IF EXISTS policies CASCADE",
    "DROP TABLE IF EXISTS policyholders CASCADE",
    "DROP TABLE IF EXISTS guardrail_logs CASCADE",
    """CREATE TABLE policyholders (
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
    """CREATE TABLE policies (
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
    """CREATE TABLE claims (
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
    """CREATE TABLE guardrail_logs (
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

RPC_FUNCTION = """
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
        desc = attempt["desc"]
        print(f"  Trying: {desc}...", end=" ", flush=True)
        try:
            conn = pg8000.connect(
                host=attempt["host"],
                port=attempt["port"],
                user=attempt["user"],
                password=DB_PASS,
                database="postgres",
                ssl_context=True,
                timeout=10,
            )
            print("CONNECTED!")
            return conn
        except Exception as e:
            err = str(e).split('\n')[0][:80]
            print(f"failed ({err})")
    return None


def main():
    print("Connecting to Supabase PostgreSQL...\n")

    conn = try_connect()
    if conn is None:
        print("\nAll connection attempts failed.")
        print("Please run the SQL manually in the Supabase SQL Editor.")
        print("The SQL is in: setup_insurance_db.sql")
        sys.exit(1)

    conn.autocommit = True
    cursor = conn.cursor()

    print("\nCreating tables and indexes...")
    for i, stmt in enumerate(STATEMENTS):
        desc = stmt.strip().split("\n")[0][:60]
        try:
            cursor.execute(stmt)
            print(f"  [{i+1}/{len(STATEMENTS)}] OK: {desc}")
        except Exception as e:
            print(f"  [{i+1}/{len(STATEMENTS)}] FAIL: {desc} -> {e}")

    print("\nCreating RPC function...")
    try:
        cursor.execute(RPC_FUNCTION)
        print("  OK: execute_readonly_query function created.")
    except Exception as e:
        print(f"  FAIL: {e}")

    print("\nVerifying tables...")
    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('policyholders', 'policies', 'claims', 'guardrail_logs')
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    print(f"  Found tables: {tables}")

    cursor.close()
    conn.close()

    if len(tables) == 4:
        print("\nAll 4 tables created successfully! Ready to seed data.")
    else:
        print(f"\nWARNING: Expected 4 tables, found {len(tables)}.")


if __name__ == "__main__":
    main()
