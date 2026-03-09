from __future__ import annotations

"""
LangChain Agent with Euri (OpenAI-compatible) LLM and guardrail pipeline.
Uses ReAct prompting (text-based) for broad API compatibility.
"""

import time
import uuid
import re
from typing import Optional, List, Dict
from langchain_openai import ChatOpenAI

import config
from agents.tools import ALL_TOOLS
from guardrails.policy import PolicyGuardrail
from guardrails.input_guard import InputGuardrail
from guardrails.instruction import InstructionalGuardrail
from guardrails.execution import ExecutionGuardrail
from guardrails.output_guard import OutputGuardrail
from guardrails.monitoring import MonitoringGuardrail, MonitoringRecord

TOOL_DESCRIPTIONS = "\n".join(
    f"- {t.name}: {t.description}" for t in ALL_TOOLS
)
TOOL_NAMES = ", ".join(t.name for t in ALL_TOOLS)

REACT_TEMPLATE = """{role_instructions}

You have access to the following tools:
{tools}

To use a tool, respond with EXACTLY this format:
Thought: I need to figure out what the user is asking and which tool to use.
Action: tool_name
Action Input: the input to the tool

After the tool returns, you will see:
Observation: the tool output

You can repeat Thought/Action/Action Input/Observation as many times as needed.

When you have enough information to answer the user, respond with:
Thought: I now have the information to answer.
Final Answer: your complete answer to the user

IMPORTANT: You MUST use one of these tool names: {tool_names}
IMPORTANT: Always end with "Final Answer:" when you are ready to respond to the user.

Begin!

Question: {input}
{agent_scratchpad}"""


class ReActAgent:
    """A ReAct agent that validates tool calls through the execution guardrail
    BEFORE executing them."""

    def __init__(self, llm, tools, execution_guard: ExecutionGuardrail, role: str = "agent"):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.execution_guard = execution_guard
        self.role = role
        self.max_iterations = 5

    def invoke(self, inputs: dict) -> dict:
        question = inputs.get("input", "")
        role_instructions = inputs.get("role_instructions", "")
        scratchpad = ""
        intermediate_steps = []
        execution_checks = []

        for i in range(self.max_iterations):
            prompt_text = REACT_TEMPLATE.format(
                role_instructions=role_instructions,
                tools=TOOL_DESCRIPTIONS,
                tool_names=TOOL_NAMES,
                input=question,
                agent_scratchpad=scratchpad,
            )

            response = self.llm.invoke(prompt_text)
            text = response.content if hasattr(response, "content") else str(response)

            final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
            if final_match:
                return {
                    "output": final_match.group(1).strip(),
                    "intermediate_steps": intermediate_steps,
                    "execution_checks": execution_checks,
                }

            action_match = re.search(r"Action:\s*(.+?)[\n\r]", text)
            input_match = re.search(r"Action Input:\s*(.+?)(?:\n|$)", text, re.DOTALL)

            if action_match and input_match:
                tool_name = action_match.group(1).strip()
                tool_input = input_match.group(1).strip()

                tool_access_check = self.execution_guard.check_tool_access(tool_name, role=self.role)
                execution_checks.append({
                    "tool": tool_name,
                    "input": tool_input[:500],
                    "access_allowed": tool_access_check.passed,
                    "reason": tool_access_check.reason,
                })

                if not tool_access_check.passed:
                    observation = f"BLOCKED: {tool_access_check.reason}"
                    intermediate_steps.append((
                        type("Action", (), {"tool": tool_name, "tool_input": tool_input})(),
                        observation,
                    ))
                    scratchpad += f"\nAction: {tool_name}\n"
                    scratchpad += f"Action Input: {tool_input}\n"
                    scratchpad += f"Observation: {observation}\n"
                    scratchpad += "Thought: That tool is not available for this role. I should answer based on what I can access.\n"
                    continue

                if tool_name == "run_custom_query":
                    sql_checks = self.execution_guard.validate_sql(tool_input)
                    sql_blocked = self.execution_guard.is_sql_blocked(sql_checks)
                    execution_checks[-1]["sql_validated"] = True
                    execution_checks[-1]["sql_passed"] = not sql_blocked
                    if sql_blocked:
                        reasons = [c.reason for c in sql_checks if not c.passed]
                        observation = f"BLOCKED: SQL validation failed — {'; '.join(reasons)}"
                        intermediate_steps.append((
                            type("Action", (), {"tool": tool_name, "tool_input": tool_input})(),
                            observation,
                        ))
                        scratchpad += f"\nAction: {tool_name}\n"
                        scratchpad += f"Action Input: {tool_input}\n"
                        scratchpad += f"Observation: {observation}\n"
                        continue

                if tool_name in self.tools:
                    try:
                        observation = self.tools[tool_name].invoke(tool_input)
                    except Exception as e:
                        observation = f"Error running tool: {str(e)[:200]}"

                    intermediate_steps.append((
                        type("Action", (), {"tool": tool_name, "tool_input": tool_input})(),
                        observation,
                    ))

                    scratchpad += f"\nThought: {text.split('Action:')[0].replace('Thought:', '').strip()}\n"
                    scratchpad += f"Action: {tool_name}\n"
                    scratchpad += f"Action Input: {tool_input}\n"
                    scratchpad += f"Observation: {observation}\n"
                else:
                    scratchpad += f"\nObservation: Tool '{tool_name}' not found. Available: {TOOL_NAMES}\n"
            else:
                return {
                    "output": text.strip(),
                    "intermediate_steps": intermediate_steps,
                    "execution_checks": execution_checks,
                }

        return {
            "output": "I wasn't able to complete my analysis within the allowed steps. Please try a simpler question.",
            "intermediate_steps": intermediate_steps,
            "execution_checks": execution_checks,
        }


class GuardedAgent:

    def __init__(self):
        self.llm = ChatOpenAI(
            model=config.EURI_MODEL,
            api_key=config.EURI_API_KEY,
            base_url=config.EURI_BASE_URL,
            temperature=0.1,
            max_tokens=2048,
        )

        self.policy_guard = PolicyGuardrail()
        self.input_guard = InputGuardrail()
        self.instruction_guard = InstructionalGuardrail()
        self.execution_guard = ExecutionGuardrail()
        self.output_guard = OutputGuardrail()
        self.monitoring = MonitoringGuardrail()

    def process(self, user_input: str, session_id: Optional[str] = None,
                chat_history: Optional[List] = None, role: str = "agent") -> dict:
        if session_id is None:
            session_id = str(uuid.uuid4())
        start_time = time.time()

        response = {
            "session_id": session_id,
            "user_input": user_input,
            "output": "",
            "blocked": False,
            "block_reason": None,
            "guardrail_results": {
                "policy": [],
                "input": [],
                "instructional": [],
                "execution": [],
                "output": [],
            },
            "tools_called": [],
            "execution_time_ms": 0,
        }

        # --- 1. Policy Layer ---
        policy_results = self.policy_guard.check_all(user_input, role=role, session_id=session_id)
        response["guardrail_results"]["policy"] = [
            {"name": r.policy_name, "allowed": r.allowed, "reason": r.reason}
            for r in policy_results
        ]
        self.monitoring.log_policy_check(session_id, user_input, policy_results, self.policy_guard.is_blocked(policy_results))

        if self.policy_guard.is_blocked(policy_results):
            blocked_reasons = [r.reason for r in policy_results if not r.allowed]
            response["blocked"] = True
            response["block_reason"] = f"Policy violation: {'; '.join(blocked_reasons)}"
            response["output"] = f"I'm sorry, your request was blocked by our policy guardrail: {blocked_reasons[0]}"
            self._finalize(response, start_time, session_id, user_input)
            return response

        # --- 2. Input Layer ---
        input_results = self.input_guard.check_all(user_input, role=role)
        sanitized = self.input_guard.get_sanitized(user_input)
        response["guardrail_results"]["input"] = [
            {"name": r.check_name, "passed": r.passed, "reason": r.reason}
            for r in input_results
        ]
        self.monitoring.log_input_check(session_id, user_input, sanitized, input_results, self.input_guard.is_blocked(input_results))

        if self.input_guard.is_blocked(input_results):
            blocked_reasons = [r.reason for r in input_results if not r.passed]
            response["blocked"] = True
            response["block_reason"] = f"Input validation failed: {'; '.join(blocked_reasons)}"
            response["output"] = f"I'm sorry, your input was blocked: {blocked_reasons[0]}"
            self._finalize(response, start_time, session_id, user_input)
            return response

        # --- 3. Instructional Layer ---
        instruction_results = self.instruction_guard.check_all(sanitized, role=role)
        response["guardrail_results"]["instructional"] = [
            {"name": r.check_name, "passed": r.passed, "reason": r.reason}
            for r in instruction_results
        ]
        self.monitoring.log_instruction_check(session_id, user_input, instruction_results, self.instruction_guard.is_blocked(instruction_results))

        if self.instruction_guard.is_blocked(instruction_results):
            blocked_reasons = [r.reason for r in instruction_results if not r.passed]
            response["blocked"] = True
            response["block_reason"] = f"Instructional guardrail: {'; '.join(blocked_reasons)}"
            response["output"] = f"I'm sorry, I can't help with that: {blocked_reasons[0]}"
            self._finalize(response, start_time, session_id, user_input)
            return response

        # --- 4. Execute Agent (Execution Layer checks happen INSIDE the ReAct loop) ---
        intermediate_steps = []
        try:
            executor = ReActAgent(self.llm, ALL_TOOLS, self.execution_guard, role=role)
            role_instructions = self.instruction_guard.get_system_prompt(role)
            agent_result = executor.invoke({
                "input": sanitized,
                "role_instructions": role_instructions,
                "chat_history": chat_history or [],
            })
            raw_output = agent_result.get("output", "")
            intermediate_steps = agent_result.get("intermediate_steps", [])
            execution_checks = agent_result.get("execution_checks", [])

            for check in execution_checks:
                tool_name = check["tool"]
                tool_input = check.get("input", "")
                allowed = check["access_allowed"]

                response["tools_called"].append({
                    "tool": tool_name,
                    "input": str(tool_input)[:200],
                    "allowed": allowed,
                })

                response["guardrail_results"]["execution"].append({
                    "name": "tool_access",
                    "passed": allowed,
                    "reason": check["reason"],
                })

                self.monitoring.log_execution_check(
                    session_id, user_input, tool_name,
                    allowed, str(tool_input)[:500], None
                )

        except Exception as e:
            raw_output = f"I encountered an error processing your request: {str(e)[:150]}"
            response["guardrail_results"]["execution"] = [{"name": "agent_error", "passed": False, "reason": str(e)[:200]}]

        # --- 5. Output Layer ---
        query_data = []
        for step in intermediate_steps:
            if len(step) >= 2 and isinstance(step[1], str) and not step[1].startswith("BLOCKED"):
                query_data.append(step[1])

        output_results = self.output_guard.check_all(raw_output, role=role, query_data=query_data if query_data else None)
        final_output = raw_output

        hallucination_detected = any(
            not r.passed and r.check_name == "hallucination_detection"
            for r in output_results
        )

        for r in output_results:
            if not r.passed and r.filtered_output:
                final_output = r.filtered_output

        response["guardrail_results"]["output"] = [
            {"name": r.check_name, "passed": r.passed, "reason": r.reason}
            for r in output_results
        ]
        self.monitoring.log_output_check(
            session_id, user_input, raw_output, final_output,
            output_results, hallucination_detected
        )

        if hallucination_detected:
            final_output += "\n\n⚠️ Note: Some parts of this response may not be fully grounded in the database data. Please verify critical information."

        response["output"] = final_output
        self._finalize(response, start_time, session_id, user_input)
        return response

    def _finalize(self, response: dict, start_time: float, session_id: str, user_input: str):
        elapsed = (time.time() - start_time) * 1000
        response["execution_time_ms"] = round(elapsed, 2)
        self.monitoring.log_full_pipeline(
            session_id, user_input, elapsed,
            response["blocked"], response.get("block_reason")
        )
