from __future__ import annotations

"""
FastAPI backend serving the guarded LangChain agent.
"""

import os
import sys
import logging
import traceback
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("guardrails-api")

app = FastAPI(
    title="Insurance Claims Agent API",
    description="Agentic chat interface with 6-layer guardrails for insurance claims database queries.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        logger.info("Initializing GuardedAgent (first request)...")
        from agents.agent import GuardedAgent
        _agent = GuardedAgent()
        logger.info("GuardedAgent ready.")
    return _agent


def get_db_client():
    from database.connection import get_client
    return get_client()


@app.on_event("startup")
async def startup():
    logger.info("=== Backend Starting ===")
    logger.info(f"Python: {sys.version}")
    logger.info(f"CWD: {os.getcwd()}")
    try:
        import config
        logger.info(f"EURI_API_KEY set: {bool(config.EURI_API_KEY)}")
        logger.info(f"EURI_BASE_URL: {config.EURI_BASE_URL}")
        logger.info(f"EURI_MODEL: {config.EURI_MODEL}")
        logger.info(f"SUPABASE_URL set: {bool(config.SUPABASE_URL)}")
        logger.info(f"SUPABASE_SERVICE_KEY set: {bool(config.SUPABASE_SERVICE_KEY)}")
    except Exception as e:
        logger.error(f"Config load failed: {e}")
    logger.info("=== Startup complete ===")


# ─── Root (Render health check hits this) ────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "service": "guardrails-api"}


# ─── Chat Models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    chat_history: Optional[list] = Field(None, description="Previous messages for context")
    role: str = Field("agent", description="User role: agent, claims_adjuster, auditor")


class ChatResponse(BaseModel):
    session_id: str
    output: str
    blocked: bool
    block_reason: Optional[str] = None
    guardrail_results: dict
    tools_called: list
    execution_time_ms: float


# ─── Chat Endpoint ──────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        langchain_history = []
        if request.chat_history:
            from langchain_core.messages import HumanMessage, AIMessage
            for msg in request.chat_history:
                if msg.get("role") == "user":
                    langchain_history.append(HumanMessage(content=msg["content"]))
                elif msg.get("role") == "assistant":
                    langchain_history.append(AIMessage(content=msg["content"]))

        result = get_agent().process(
            user_input=request.message,
            session_id=request.session_id,
            chat_history=langchain_history,
            role=request.role,
        )
        return ChatResponse(**result)
    except Exception as e:
        logger.error(f"Chat error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Health ─────────────────────────────────────────────────────

@app.get("/health")
async def health():
    db_status = "unknown"
    try:
        client = get_db_client()
        client.table("policyholders").select("id").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)[:100]}"

    return {
        "status": "healthy",
        "service": "insurance-claims-agent",
        "database": db_status,
    }


# ─── Guardrails Info ────────────────────────────────────────────

@app.get("/guardrails/info")
async def guardrails_info():
    return {
        "layers": [
            {"name": "Policy Layer", "description": "Role-based access, rate limiting, operation policies, data scope enforcement"},
            {"name": "Input Layer", "description": "SQL injection detection, prompt injection detection, PII redaction, input length/empty validation"},
            {"name": "Instructional Layer", "description": "Topic relevance enforcement, role deviation detection, instruction extraction prevention"},
            {"name": "Execution Layer", "description": "Tool access control, SQL validation (type, keywords, tables, row limits, multi-statement)"},
            {"name": "Output Layer", "description": "Sensitive data filtering, hallucination detection, response length control, instruction leak prevention"},
            {"name": "Monitoring Layer", "description": "Full pipeline logging to guardrail_logs table: inputs, outputs, tools, blocks, hallucinations, timing"},
        ]
    }


# ─── Monitoring: Logs ───────────────────────────────────────────

@app.get("/monitoring/logs")
async def get_monitoring_logs(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    status: Optional[str] = Query(None, description="Filter by action (passed/blocked/completed)"),
    guardrail_layer: Optional[str] = Query(None, description="Filter by guardrail layer"),
    limit: int = Query(50, ge=1, le=500, description="Number of records"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    try:
        client = get_db_client()
        q = client.table("guardrail_logs").select("*", count="exact")

        if session_id:
            q = q.eq("session_id", session_id)
        if status:
            q = q.eq("action", status)
        if guardrail_layer:
            q = q.eq("guardrail_layer", guardrail_layer)

        q = q.order("timestamp", desc=True).range(offset, offset + limit - 1)
        result = q.execute()

        return {
            "total": result.count,
            "limit": limit,
            "offset": offset,
            "logs": result.data,
        }
    except Exception as e:
        logger.error(f"Logs error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")


# ─── Monitoring: Stats ──────────────────────────────────────────

@app.get("/monitoring/stats")
async def get_monitoring_stats():
    try:
        client = get_db_client()

        all_logs = client.table("guardrail_logs").select("guardrail_layer, action, blocked, hallucination_flag, tool_called, tool_allowed, execution_time_ms", count="exact").execute()
        total = all_logs.count or 0
        logs = all_logs.data or []

        pipeline_logs = [l for l in logs if l.get("guardrail_layer") == "monitoring"]
        blocked_count = sum(1 for l in pipeline_logs if l.get("blocked"))
        error_count = sum(1 for l in pipeline_logs if l.get("action") == "error")

        timings = [l["execution_time_ms"] for l in pipeline_logs if l.get("execution_time_ms") is not None]
        avg_latency = round(sum(float(t) for t in timings) / len(timings), 2) if timings else 0

        layer_counts = {}
        for l in logs:
            layer = l.get("guardrail_layer", "unknown")
            if l.get("blocked"):
                layer_counts[layer] = layer_counts.get(layer, 0) + 1

        tool_logs = [l for l in logs if l.get("tool_called")]
        tool_usage = {}
        for l in tool_logs:
            tool_name = l["tool_called"]
            if tool_name not in tool_usage:
                tool_usage[tool_name] = {"allowed": 0, "blocked": 0}
            if l.get("tool_allowed"):
                tool_usage[tool_name]["allowed"] += 1
            else:
                tool_usage[tool_name]["blocked"] += 1

        hallucination_count = sum(1 for l in logs if l.get("hallucination_flag"))

        return {
            "total_log_entries": total,
            "total_pipelines": len(pipeline_logs),
            "blocked_count": blocked_count,
            "error_count": error_count,
            "avg_latency_ms": avg_latency,
            "guardrail_block_counts": layer_counts,
            "tool_usage": tool_usage,
            "hallucination_detected_count": hallucination_count,
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compute stats: {str(e)}")


# ─── Monitoring: Sessions ───────────────────────────────────────

@app.get("/monitoring/sessions")
async def get_sessions(limit: int = Query(20, ge=1, le=100)):
    try:
        client = get_db_client()
        result = client.table("guardrail_logs").select(
            "session_id"
        ).eq("guardrail_layer", "monitoring").order(
            "timestamp", desc=True
        ).limit(limit * 5).execute()

        seen = set()
        sessions = []
        for row in result.data:
            sid = row["session_id"]
            if sid and sid not in seen:
                seen.add(sid)
                sessions.append(sid)
            if len(sessions) >= limit:
                break

        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Sessions error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import config
    uvicorn.run(app, host="0.0.0.0", port=config.FASTAPI_PORT)
