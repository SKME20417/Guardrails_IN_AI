# Architecture

## High-Level Components
- **Streamlit Frontend** — Chat interface for user interaction
- **FastAPI Backend** — API layer serving agent requests and guardrail orchestration
- **LangChain Agent** — LLM-powered agent with tool access for database querying
- **OpenAI LLM (via Euron-Euri)** — Language model for natural language understanding and generation
- **Supabase (PostgreSQL)** — Database for domain data and monitoring logs
- **Guardrail Engine** — Multi-layered guardrail system (policy, input, instructional, execution, output, monitoring)

## System Flow
```
User (Streamlit Chat UI)
    │
    ▼
FastAPI Backend
    │
    ├─► Input Layer Guardrail (validate/sanitize user input)
    │
    ├─► Policy Layer Guardrail (check allowed operations)
    │
    ├─► Instructional Layer Guardrail (enforce system prompt boundaries)
    │
    ├─► LangChain Agent
    │       │
    │       ├─► Execution Layer Guardrail (validate tool calls / SQL)
    │       │
    │       ├─► Tools (Supabase DB query tools)
    │       │
    │       └─► Agent Response
    │
    ├─► Output Layer Guardrail (validate response, check hallucination)
    │
    ├─► Monitoring Layer Guardrail (log everything to guardrail_logs table)
    │
    └─► Response returned to Streamlit UI
```

## Layering
| Layer              | Responsibility                                                     |
|--------------------|--------------------------------------------------------------------|
| Presentation       | Streamlit chat UI, message rendering, monitoring dashboard         |
| API                | FastAPI routes, request/response handling                          |
| Guardrails         | Six-layer guardrail engine (policy, input, instructional, execution, output, monitoring) |
| Agent Orchestration| LangChain agent setup, tool binding, prompt management             |
| Tools              | Database query tools, schema introspection tools                   |
| Data Access        | Supabase client, query execution, connection management            |
| Logging/Monitoring | Structured logging to guardrail_logs table in Supabase             |

## Directory Structure (Planned)
```
├── frontend/
│   ├── app.py                  # Streamlit main app (chat UI)
│   ├── pages/
│   │   └── monitoring.py       # Monitoring dashboard page
│   └── components/             # Reusable Streamlit components
│
├── backend/
│   ├── main.py                 # FastAPI app entrypoint
│   ├── api/
│   │   └── routes/             # API route definitions
│   ├── agent/
│   │   ├── agent.py            # LangChain agent setup
│   │   ├── tools/              # Agent tools (DB query, schema, etc.)
│   │   └── prompts/            # System prompts and templates
│   ├── guardrails/
│   │   ├── policy.py           # Policy layer guardrail
│   │   ├── input.py            # Input layer guardrail
│   │   ├── instructional.py    # Instructional layer guardrail
│   │   ├── execution.py        # Execution layer guardrail
│   │   ├── output.py           # Output layer guardrail
│   │   └── monitoring.py       # Monitoring layer guardrail (logging)
│   ├── services/               # Business logic services
│   ├── models/                 # Pydantic models and schemas
│   ├── db/
│   │   ├── supabase_client.py  # Supabase connection and client
│   │   └── seed.py             # Data seeding script (1000+ records)
│   ├── core/
│   │   └── config.py           # Centralized configuration
│   └── utils/                  # Shared utilities
│
├── docs/                       # Project documentation
├── .cursor/rules/              # Cursor AI rules
├── .env.example                # Environment variable template
└── requirements.txt            # Python dependencies
```

## Principles
- Clean separation between frontend, backend, agent, guardrails, and database layers.
- Every interaction passes through the full guardrail pipeline.
- All guardrail decisions and system events are logged for auditability.
- Agent tools are explicitly defined with strict input/output contracts.
- No direct database mutation (read-only access through the chat interface).
- Fail-safe: if any guardrail layer fails, the request is blocked rather than allowed.
