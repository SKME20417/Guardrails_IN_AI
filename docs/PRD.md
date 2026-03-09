# Product Requirements Document

## Product Name
Guardrails in AI — Agentic Database Chat System

## Vision
A chat-based interface where users interact with a relational database (Students, Courses, Transactions) through natural language. An LLM-powered agent translates user intent into database queries, executes them via tools, and returns grounded answers — all governed by a multi-layered guardrail system that ensures safety, accuracy, and auditability.

## Core Users
- End User: Interacts with the chat interface to query and explore database information using natural language.
- Administrator/Monitor: Reviews monitoring logs, guardrail activity, blocked queries, and system health.

## Tech Stack
| Layer        | Technology                              |
|--------------|-----------------------------------------|
| Frontend     | Streamlit (Python)                      |
| Backend      | Python, FastAPI                         |
| LLM Provider | OpenAI model via Euron-Euri             |
| Agent Framework | LangChain                            |
| Database     | Supabase (PostgreSQL)                   |

## Core Domain — Database Tables
1. **students** — Student records (name, email, enrollment date, department, etc.)
2. **courses** — Course catalog (title, department, credits, instructor, etc.)
3. **transactions** — Enrollment/payment transactions linking students to courses (amount, date, status, etc.)
4. **guardrail_logs** — Monitoring table for logging all guardrail activity, tool usage, hallucination checks, and system events.

## Data Seeding
- Minimum 1,000 data points across the three domain tables (students, courses, transactions).
- Data must be realistic and diverse enough to support meaningful natural language queries.

## Core Features

### 1. Chat Interface (Streamlit)
- Clean chat UI with message history.
- User types natural language queries about students, courses, and transactions.
- System responds with grounded, data-backed answers.
- Chat history displayed in a conversational format.

### 2. Agentic Backend (LangChain + FastAPI)
- LangChain agent with tool access to query the Supabase database.
- Agent receives user input, reasons about intent, selects appropriate tools, executes queries, and returns results.
- Tools are explicitly defined with input/output schemas.
- FastAPI serves as the API layer between Streamlit and the agent.

### 3. Multi-Layered Guardrail System
Six guardrail layers protect every interaction:

#### 3a. Policy Layer Guardrail
- Defines what the system is allowed and not allowed to do.
- Enforces organizational rules (e.g., no DELETE/UPDATE operations, read-only access, restricted tables).
- Configurable policy rules.

#### 3b. Input Layer Guardrail
- Validates and sanitizes user input before it reaches the agent.
- Detects prompt injection, SQL injection attempts, toxic/abusive content, off-topic queries.
- Rejects or rewrites unsafe inputs.

#### 3c. Instructional Layer Guardrail
- Controls the system prompt and instructions sent to the LLM.
- Ensures the agent stays within its defined role and scope.
- Prevents jailbreak attempts that try to override system instructions.
- Enforces response boundaries (e.g., only answer database-related questions).

#### 3d. Execution Layer Guardrail
- Validates tool calls before execution.
- Checks that generated SQL is safe (no destructive operations, no unauthorized table access).
- Enforces query complexity limits (e.g., no unbounded SELECT *).
- Validates that the agent is calling allowed tools only.

#### 3e. Output Layer Guardrail
- Validates the agent's response before returning it to the user.
- Checks for hallucinated data (data not present in query results).
- Ensures response relevance and factual grounding.
- Filters sensitive information from responses.
- Enforces response format and length constraints.

#### 3f. Monitoring Layer Guardrail
- Logs every interaction end-to-end into the `guardrail_logs` table.
- Captures:
  - Raw user input
  - Input guardrail decisions (what was filtered/modified)
  - Which guardrail layers were triggered
  - Which tools were allowed and which were blocked
  - Generated SQL queries
  - Query results summary
  - Output guardrail decisions
  - Hallucination detection results
  - Final response delivered to user
  - Timestamps, latency, token usage
  - Error details if any layer failed

### 4. Monitoring Dashboard
- A dedicated section/page in the Streamlit app (or accessible view) where administrators can review:
  - All logged interactions
  - Guardrail trigger frequency
  - Blocked queries and reasons
  - Tool usage patterns
  - Hallucination detection events

## Success Criteria
- User can ask natural language questions and receive accurate, data-grounded answers.
- All six guardrail layers are functional and enforce their respective policies.
- Every interaction is fully logged in the monitoring table with granular detail.
- No destructive database operations are possible through the chat interface.
- The system gracefully handles edge cases: off-topic queries, injection attempts, ambiguous questions.
- Minimum 1,000 seeded data points across domain tables.
- Clean separation of concerns across frontend, backend, agent, guardrails, and database layers.
