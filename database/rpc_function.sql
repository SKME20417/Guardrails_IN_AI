-- Run this in Supabase SQL Editor to create the readonly query RPC function.
-- This allows the agent to execute validated SELECT queries.

CREATE OR REPLACE FUNCTION execute_readonly_query(query_text TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
BEGIN
    -- Safety: only allow SELECT
    IF NOT (UPPER(TRIM(query_text)) LIKE 'SELECT%') THEN
        RAISE EXCEPTION 'Only SELECT queries are allowed';
    END IF;

    -- Block dangerous keywords at DB level too
    IF query_text ~* '\b(DROP|ALTER|TRUNCATE|DELETE|UPDATE|INSERT|CREATE)\b' THEN
        RAISE EXCEPTION 'Blocked SQL operation detected';
    END IF;

    EXECUTE 'SELECT COALESCE(jsonb_agg(row_to_json(t)), ''[]''::jsonb) FROM (' || query_text || ') t'
    INTO result;

    RETURN result;
END;
$$;
