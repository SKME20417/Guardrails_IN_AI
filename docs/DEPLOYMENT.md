# Deployment

## Local Development

### Prerequisites
- Python 3.10+
- Supabase account and project (with connection string / API keys)
- OpenAI API key (via Euron-Euri)

### Environment Variables
Copy `.env.example` to `.env` and configure:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_DB_URL=postgresql://...
OPENAI_API_KEY=your-openai-api-key
OPENAI_API_BASE=https://api.euron.one/api/v1  # Euron-Euri endpoint (adjust as needed)
OPENAI_MODEL_NAME=gpt-4o  # or whichever model is configured
```

### Setup Steps
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
3. Install dependencies: `pip install -r requirements.txt`
4. Create tables in Supabase (run migration SQL or use the Supabase dashboard).
5. Seed the database: `python backend/db/seed.py`
6. Start the FastAPI backend: `uvicorn backend.main:app --reload --port 8000`
7. Start the Streamlit frontend: `streamlit run frontend/app.py`

### Running Both Services
- Backend runs on `http://localhost:8000`
- Streamlit runs on `http://localhost:8501`
- Streamlit communicates with FastAPI via HTTP calls.

## Database Setup (Supabase)
- Create a new Supabase project.
- Use the SQL editor or migration scripts to create the four tables: `students`, `courses`, `transactions`, `guardrail_logs`.
- Run the seed script to populate domain tables with 1,000+ records.
- Supabase provides built-in PostgreSQL, auth, and REST API capabilities.

## Non-Functional Goals
- Responsive chat experience with reasonable latency.
- All interactions auditable via the monitoring/logs table.
- Guardrails enforce safety without degrading user experience.
- Clean error messages when requests are blocked.
- Environment-driven configuration (no hardcoded secrets).
