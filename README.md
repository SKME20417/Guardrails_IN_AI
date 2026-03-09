# Insurance Claims Database Agent — Guardrails in AI

An agentic LLM-powered chat system for querying insurance claims data, built with **6 layers of AI guardrails** to demonstrate responsible AI practices for enterprise use.

## Tech Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| Frontend       | Streamlit                           |
| Backend        | FastAPI + Python                    |
| Agent          | LangChain (ReAct) + OpenAI (Euri)  |
| Database       | Supabase (PostgreSQL)               |
| Guardrails     | 6-layer custom pipeline             |

## Database Schema

| Table            | Records | Description                                    |
|------------------|---------|------------------------------------------------|
| `policyholders`  | 400     | Personal info, risk scores, premium amounts    |
| `policies`       | 100     | Insurance products (health/auto/life/property/travel) |
| `claims`         | 600     | Filed claims with fraud flags, amounts, statuses |
| `guardrail_logs` | auto    | Full audit trail of every interaction          |

## Roles & Access Control

| Feature              | Agent | Claims Adjuster | Auditor |
|----------------------|:-----:|:---------------:|:-------:|
| Policyholder names   |  Yes  |      Yes        |   Yes   |
| City/State           |  Yes  |      Yes        |   Yes   |
| Email/Phone/DOB      |  No   |      Yes        |   Yes   |
| Address              |  No   |      Yes        |   Yes   |
| Premiums/Coverage    |  No   |      Yes        |   Yes   |
| Claims data          |  No   |      Yes        |   Yes   |
| Fraud flags          |  No   |      No         |   Yes   |
| Risk scores          |  No   |      No         |   Yes   |
| Schema access        |  No   |      No         |   Yes   |
| Custom SQL           |  No   |      No         |   Yes   |
| Monitoring logs      |  No   |      No         |   Yes   |

## 6 Guardrail Layers

1. **Policy Layer** — Role-based access control, rate limiting, table/operation restrictions
2. **Input Layer** — SQL injection detection, prompt injection prevention, PII redaction
3. **Instructional Layer** — Topic relevance, role deviation, privilege escalation prevention
4. **Execution Layer** — Tool access control, SQL validation (SELECT-only, LIMIT enforced)
5. **Output Layer** — Sensitive data filtering by role, hallucination detection, response limits
6. **Monitoring Layer** — Full pipeline audit logging to `guardrail_logs` table

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `EURI_API_KEY` — Your Euri/OpenAI API key
- `EURI_BASE_URL` — API base URL
- `SUPABASE_URL` — Your Supabase project URL
- `SUPABASE_KEY` — Supabase anon/public key
- `SUPABASE_SERVICE_KEY` — Supabase service role key

### 3. Create database tables

**Option A: SQL Editor (recommended)**
```bash
python create_tables.py
```
Copy the printed SQL into Supabase Dashboard > SQL Editor > Run.

**Option B: Direct connection**
```bash
python db_bootstrap.py
```

### 4. Seed data (1,100 records)

```bash
python -m database.seed
```

### 5. Verify seed

```bash
python verify_seed.py
```

### 6. Start the backend

```bash
python -m backend.api
```

### 7. Start the frontend

```bash
streamlit run frontend/app.py
```

## Testing Guardrails

```bash
python test_guardrails.py
```

This runs comprehensive tests across all roles and guardrail bypass scenarios.

## Project Structure

```
├── agents/
│   ├── agent.py          # ReAct agent with guardrail pipeline
│   └── tools.py          # LangChain tools for insurance queries
├── backend/
│   └── api.py            # FastAPI endpoints
├── database/
│   ├── connection.py     # Supabase client singleton
│   ├── seed.py           # Data seeding (400 + 100 + 600 records)
│   └── setup.py          # Schema SQL reference
├── frontend/
│   ├── app.py            # Streamlit chat interface
│   └── pages/
│       └── monitoring.py # Monitoring dashboard
├── guardrails/
│   ├── policy.py         # Policy layer (RBAC, rate limits)
│   ├── input_guard.py    # Input layer (injection, PII)
│   ├── instruction.py    # Instructional layer (topic, roles)
│   ├── execution.py      # Execution layer (tools, SQL)
│   ├── output_guard.py   # Output layer (filtering, hallucination)
│   └── monitoring.py     # Monitoring layer (audit logging)
├── config.py             # Environment config
├── create_tables.py      # Print SQL for manual setup
├── db_bootstrap.py       # Auto-create tables via psycopg2
├── test_guardrails.py    # Comprehensive test suite
├── verify_seed.py        # Verify seeded data
└── requirements.txt      # Python dependencies
```
