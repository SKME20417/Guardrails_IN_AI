from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

EURI_API_KEY = os.getenv("EURI_API_KEY")
EURI_BASE_URL = os.getenv("EURI_BASE_URL")
EURI_MODEL = os.getenv("EURI_MODEL", "gpt-4.1-nano")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", 8000))
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", 8501))

ALLOWED_TABLES = {"policyholders", "policies", "claims"}

ALLOWED_OPERATIONS = {"SELECT"}
BLOCKED_OPERATIONS = {"DROP", "TRUNCATE", "ALTER", "CREATE", "DELETE", "UPDATE", "INSERT"}

MAX_QUERY_ROWS = 100
MAX_INPUT_LENGTH = 2000
