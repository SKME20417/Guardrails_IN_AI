# API Specification

## Base URL
`http://localhost:8000/api/v1`

---

## Chat / Agent

### POST /api/v1/chat
Send a user message to the agentic system and receive a guardrail-protected response.

**Request Body:**
```json
{
  "session_id": "string",
  "message": "string"
}
```

**Response:**
```json
{
  "session_id": "string",
  "response": "string",
  "guardrails_triggered": ["string"],
  "status": "success | blocked | error",
  "metadata": {
    "tools_used": ["string"],
    "latency_ms": 0,
    "token_usage": {
      "prompt_tokens": 0,
      "completion_tokens": 0,
      "total_tokens": 0
    }
  }
}
```

---

## Chat History

### GET /api/v1/chat/history/{session_id}
Retrieve the chat history for a given session.

**Response:**
```json
{
  "session_id": "string",
  "messages": [
    {
      "role": "user | assistant",
      "content": "string",
      "timestamp": "ISO 8601"
    }
  ]
}
```

---

## Monitoring / Logs

### GET /api/v1/monitoring/logs
Retrieve guardrail logs with optional filters.

**Query Parameters:**
| Param       | Type   | Description                          |
|-------------|--------|--------------------------------------|
| session_id  | string | Filter by session ID                 |
| status      | string | Filter by status (success/blocked/error) |
| start_date  | string | Filter logs from this date (ISO 8601)|
| end_date    | string | Filter logs until this date          |
| limit       | int    | Number of records (default 50)       |
| offset      | int    | Pagination offset                    |

**Response:**
```json
{
  "total": 0,
  "logs": [
    {
      "id": "uuid",
      "session_id": "string",
      "timestamp": "ISO 8601",
      "user_input": "string",
      "status": "string",
      "guardrails_triggered": [],
      "tools_allowed": [],
      "tools_blocked": [],
      "generated_sql": "string",
      "hallucination_check": {},
      "latency_ms": 0
    }
  ]
}
```

### GET /api/v1/monitoring/stats
Retrieve aggregate statistics on guardrail activity.

**Response:**
```json
{
  "total_interactions": 0,
  "blocked_count": 0,
  "error_count": 0,
  "avg_latency_ms": 0,
  "guardrail_trigger_counts": {
    "policy": 0,
    "input": 0,
    "instructional": 0,
    "execution": 0,
    "output": 0
  },
  "tool_usage_counts": {},
  "hallucination_detected_count": 0
}
```

---

## Health

### GET /api/v1/health
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "database": "connected",
  "llm_provider": "connected"
}
```

---

## Database Schema Info (Internal — used by agent tools)

### GET /api/v1/schema/tables
Returns the list of queryable tables and their columns (used by the agent for schema-aware querying).

**Response:**
```json
{
  "tables": [
    {
      "name": "students",
      "columns": ["id", "first_name", "last_name", "email", "..."]
    }
  ]
}
```
