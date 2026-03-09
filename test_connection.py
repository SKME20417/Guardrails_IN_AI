"""Quick test: verify Supabase connection works with insurance tables."""
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import config

print(f"Supabase URL: {config.SUPABASE_URL}")
print(f"Supabase Key: {config.SUPABASE_KEY[:20]}...")
print(f"Service Key:  {config.SUPABASE_SERVICE_KEY[:20]}...")
print()

try:
    from database.connection import get_client
    client = get_client()
    print("Client created successfully.")

    result = client.table("policyholders").select("id").limit(1).execute()
    print(f"Query test: OK (returned {len(result.data)} rows — table may be empty if not yet seeded)")
    print("\nConnection test PASSED.")
except Exception as e:
    print(f"Connection test FAILED: {e}")
    sys.exit(1)
