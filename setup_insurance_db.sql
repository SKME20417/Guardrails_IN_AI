-- ============================================================
-- INSURANCE CLAIMS DATABASE SETUP
-- Run this entire script in Supabase SQL Editor
-- (Dashboard -> SQL Editor -> New Query -> Paste -> Run)
-- ============================================================

-- Step 1: Drop old university tables
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS students CASCADE;

-- Step 2: Drop existing insurance tables (clean slate)
DROP TABLE IF EXISTS claims CASCADE;
DROP TABLE IF EXISTS policies CASCADE;
DROP TABLE IF EXISTS policyholders CASCADE;
DROP TABLE IF EXISTS guardrail_logs CASCADE;

-- Step 3: Create insurance tables

CREATE TABLE policyholders (
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

CREATE TABLE policies (
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

CREATE TABLE claims (
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

CREATE TABLE guardrail_logs (
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

-- Step 4: Create indexes

CREATE INDEX idx_ph_email ON policyholders(email);
CREATE INDEX idx_ph_state ON policyholders(state);
CREATE INDEX idx_ph_active ON policyholders(is_active);
CREATE INDEX idx_pol_number ON policies(policy_number);
CREATE INDEX idx_pol_type ON policies(policy_type);
CREATE INDEX idx_claims_ph ON claims(policyholder_id);
CREATE INDEX idx_claims_pol ON claims(policy_id);
CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_claims_type ON claims(claim_type);
CREATE INDEX idx_claims_fraud ON claims(fraud_flag);
CREATE INDEX idx_gl_session ON guardrail_logs(session_id);
CREATE INDEX idx_gl_layer ON guardrail_logs(guardrail_layer);
CREATE INDEX idx_gl_ts ON guardrail_logs(timestamp);

-- Step 5: Create RPC function for custom queries

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
    IF query_text ~* '\b(DROP|ALTER|TRUNCATE|DELETE|UPDATE|INSERT|CREATE)\b' THEN
        RAISE EXCEPTION 'Blocked SQL operation detected';
    END IF;
    EXECUTE 'SELECT COALESCE(jsonb_agg(row_to_json(t)), ''[]''::jsonb) FROM (' || query_text || ') t'
    INTO result;
    RETURN result;
END;
$$;

-- Step 6: Verify
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('policyholders', 'policies', 'claims', 'guardrail_logs')
ORDER BY table_name;
