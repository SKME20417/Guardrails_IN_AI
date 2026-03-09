"""Verify seed data was inserted correctly into insurance tables."""
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from database.connection import get_client

client = get_client()

for table in ["policyholders", "policies", "claims", "guardrail_logs"]:
    r = client.table(table).select("id", count="exact").execute()
    print(f"{table}: {r.count} rows")

ph = client.table("policyholders").select("first_name, last_name, city, state, premium_amount, risk_score").limit(3).execute()
print("\nSample policyholders:")
for row in ph.data:
    print(f"  {row['first_name']} {row['last_name']} | {row['city']}, {row['state']} | Premium: ${row['premium_amount']} | Risk: {row['risk_score']}")

pol = client.table("policies").select("policy_number, policy_type, provider_name, coverage_amount, premium_monthly").limit(3).execute()
print("\nSample policies:")
for row in pol.data:
    print(f"  {row['policy_number']}: {row['policy_type']} | {row['provider_name']} | Coverage: ${row['coverage_amount']} | Monthly: ${row['premium_monthly']}")

cl = client.table("claims").select("claim_number, claim_type, claim_amount, status, fraud_flag, adjuster_name").limit(3).execute()
print("\nSample claims:")
for row in cl.data:
    print(f"  {row['claim_number']}: {row['claim_type']} | ${row['claim_amount']} | {row['status']} | Fraud: {row['fraud_flag']} | Adjuster: {row['adjuster_name']}")
