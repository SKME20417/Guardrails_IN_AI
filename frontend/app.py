"""
Streamlit chat frontend for the Insurance Claims Database Agent.
"""

import os
import streamlit as st
import requests
import uuid

API_URL = os.environ.get("API_URL", "http://localhost:8000")
EXL_LOGO_URL = "https://images.seeklogo.com/logo-png/45/1/exl-logo-png_seeklogo-452218.png"

st.set_page_config(
    page_title="Insurance Claims Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

DARK_CSS = """
<style>
    .stApp { background-color: #0E1117 !important; color: #FAFAFA !important; }
    [data-testid="stSidebar"] { background-color: #161B22 !important; }
    [data-testid="stSidebar"] * { color: #C9D1D9 !important; }
    .stMarkdown, .stText, p, span, label, .stCaption { color: #C9D1D9 !important; }
    h1, h2, h3, h4, h5, h6 { color: #E6EDF3 !important; }
    .stChatMessage { background-color: #161B22 !important; border: 1px solid #30363D !important; }
    [data-testid="stChatMessageContent"] p { color: #C9D1D9 !important; }
    .stExpander { background-color: #161B22 !important; border: 1px solid #30363D !important; }
    .stDataFrame { background-color: #161B22 !important; }
    .stat-card { background: #161B22 !important; border: 1px solid #30363D !important; }
    .stat-card h3 { color: #58A6FF !important; }
    .stat-card p { color: #8B949E !important; }
    .main-header { background: linear-gradient(135deg,#58A6FF,#BC8CFF) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; }
    .sub-header { color: #8B949E !important; }
    .pipeline-step.skipped { background: #21262D !important; color: #484F58 !important; border-color: #30363D !important; }
    .pipeline-step.passed { background: #0D1117 !important; color: #3FB950 !important; border-color: #238636 !important; }
    .pipeline-step.blocked { background: #0D1117 !important; color: #F85149 !important; border-color: #DA3633 !important; }
    .guardrail-badge-passed { background: #0D2818 !important; color: #3FB950 !important; }
    .guardrail-badge-blocked { background: #2D1117 !important; color: #F85149 !important; }
    .attack-card.blocked { background: #0D2818 !important; border-left-color: #3FB950 !important; }
    .attack-card.failed { background: #2D1117 !important; border-left-color: #F85149 !important; }
    .attack-card * { color: #C9D1D9 !important; }
    code { background: #21262D !important; color: #C9D1D9 !important; }
    .stSelectbox > div > div { background-color: #21262D !important; color: #C9D1D9 !important; }
    .stTextInput > div > div > input { background-color: #21262D !important; color: #C9D1D9 !important; }
    [data-testid="stMetric"] { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 8px !important; padding: 8px !important; }
    [data-testid="stMetricValue"] { color: #58A6FF !important; }
    [data-testid="stMetricLabel"] { color: #8B949E !important; }
</style>
"""

LIGHT_CSS = """
<style>
    .main-header { font-size:2.2rem; font-weight:700; background:linear-gradient(135deg,#1E3A5F,#4F46E5); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:0; line-height:1.2; }
    .sub-header { font-size:1rem; color:#6B7280; margin-top:0; margin-bottom:1.5rem; }
    .guardrail-badge-passed { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; background:#D1FAE5; color:#065F46; margin:2px 4px; }
    .guardrail-badge-blocked { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; background:#FEE2E2; color:#991B1B; margin:2px 4px; }
    .pipeline-container { display:flex; align-items:center; gap:4px; padding:10px 0; margin:8px 0; flex-wrap:wrap; }
    .pipeline-step { display:flex; align-items:center; gap:6px; padding:6px 14px; border-radius:8px; font-size:0.8rem; font-weight:600; white-space:nowrap; }
    .pipeline-step.passed { background:#D1FAE5; color:#065F46; border:1px solid #A7F3D0; }
    .pipeline-step.blocked { background:#FEE2E2; color:#991B1B; border:1px solid #FECACA; }
    .pipeline-step.skipped { background:#F3F4F6; color:#9CA3AF; border:1px solid #E5E7EB; }
</style>
"""

COMMON_CSS = """
<style>
    .main-header { font-size:2.2rem; font-weight:700; margin-bottom:0; line-height:1.2; }
    .sub-header { font-size:1rem; margin-top:0; margin-bottom:1.5rem; }
    .guardrail-badge-passed { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; margin:2px 4px; }
    .guardrail-badge-blocked { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; margin:2px 4px; }
    .pipeline-container { display:flex; align-items:center; gap:4px; padding:10px 0; margin:8px 0; flex-wrap:wrap; }
    .pipeline-step { display:flex; align-items:center; gap:6px; padding:6px 14px; border-radius:8px; font-size:0.8rem; font-weight:600; white-space:nowrap; }
    .stat-card { border-radius:12px; padding:20px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
    .stat-card h3 { margin:0; font-size:2rem; }
    .stat-card p { margin:4px 0 0 0; font-size:0.85rem; }
</style>
"""

st.markdown(COMMON_CSS, unsafe_allow_html=True)
if st.session_state.dark_mode:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)


def render_pipeline(guardrail_results, blocked=False):
    layers = [("Policy","policy"),("Input","input"),("Instructional","instructional"),("Execution","execution"),("Output","output"),("Monitoring","monitoring")]
    found_block = False
    steps = []
    for display_name, key in layers:
        checks = guardrail_results.get(key, [])
        if found_block and key != "monitoring":
            steps.append(f'<span class="pipeline-step skipped">⊘ {display_name}</span>')
        elif key == "monitoring":
            steps.append(f'<span class="pipeline-step passed">📋 {display_name}</span>')
        elif checks:
            all_passed = all(c.get("passed", c.get("allowed", True)) for c in checks)
            if all_passed:
                steps.append(f'<span class="pipeline-step passed">✓ {display_name}</span>')
            else:
                found_block = True
                steps.append(f'<span class="pipeline-step blocked">✗ {display_name}</span>')
        else:
            steps.append(f'<span class="pipeline-step passed">✓ {display_name}</span>')
    arrow = '<span style="color:#9CA3AF;font-weight:bold;"> &rarr; </span>'
    st.markdown('<div class="pipeline-container">' + arrow.join(steps) + '</div>', unsafe_allow_html=True)


if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_blocked" not in st.session_state:
    st.session_state.total_blocked = 0
if "total_queries" not in st.session_state:
    st.session_state.total_queries = 0

with st.sidebar:
    st.markdown("### User Role")
    role = st.selectbox(
        "Select Role", ["agent", "claims_adjuster", "auditor"], index=0,
        format_func=lambda x: {"agent": "🔵 Agent", "claims_adjuster": "🟡 Claims Adjuster", "auditor": "🟢 Auditor"}[x],
    )
    role_desc = {"agent": "Basic: names, city/state, policy types only.", "claims_adjuster": "Mid: full claims + PII. No fraud/risk.", "auditor": "Full: all data, fraud, risk, custom SQL."}
    st.caption(role_desc[role])

    st.markdown("---")
    dark_toggle = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, key="dark_toggle")
    if dark_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggle
        st.rerun()

    st.markdown("---")
    st.markdown("### Guardrail Layers")
    for name, desc in [("🔒 Policy","Role access, rate limits"),("🧹 Input","Injection, PII detection"),("📐 Instructional","Topic scope, role deviation"),("⚙️ Execution","Tool access, SQL validation"),("📤 Output","Data filtering, hallucination"),("📋 Monitoring","Full audit logging")]:
        st.markdown(f"**{name}** — {desc}")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Queries", st.session_state.total_queries)
    with c2:
        st.metric("Blocked", st.session_state.total_blocked)

    st.markdown("---")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.total_blocked = 0
        st.session_state.total_queries = 0
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.markdown("---")
    st.markdown("### Example Queries")
    if role == "agent":
        examples = ["Show me all active policyholders", "How many policyholders are in New York?", "List all auto insurance policies", "How many policies does each provider have?"]
    elif role == "claims_adjuster":
        examples = ["Show me all claims under review", "List all denied claims with reasons", "What is the total approved amount for medical claims?", "Show me policyholders with their email and phone"]
    else:
        examples = ["Show me all fraud-flagged claims", "What is the average risk score by state?", "Show the schema of the claims table", "SELECT claim_type, COUNT(*) as cnt FROM claims GROUP BY claim_type LIMIT 10"]

    for ex in examples:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state.pending_example = ex
            st.rerun()

header_c1, header_c2 = st.columns([1, 8])
with header_c1:
    st.image(EXL_LOGO_URL, width=80)
with header_c2:
    st.markdown('<p class="main-header">Insurance Claims Assistant</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Ask questions about policyholders, policies, and claims — protected by 6 guardrail layers</p>', unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("blocked"):
            st.error(msg["content"])
        else:
            st.markdown(msg["content"])
        if msg["role"] == "assistant" and "guardrails" in msg:
            render_pipeline(msg["guardrails"], msg.get("blocked", False))
            with st.expander("Guardrail Details", expanded=False):
                for layer_name, checks in msg["guardrails"].items():
                    if not checks:
                        continue
                    st.markdown(f"**{layer_name.title()} Layer:**")
                    for check in checks:
                        passed = check.get("passed", check.get("allowed", True))
                        badge = "guardrail-badge-passed" if passed else "guardrail-badge-blocked"
                        st.markdown(f'<span class="{badge}">{"PASSED" if passed else "BLOCKED"}</span> **{check.get("name","")}**: {check.get("reason","")}', unsafe_allow_html=True)
                if msg.get("tools_called"):
                    st.markdown("**Tools Called:**")
                    for tool in msg["tools_called"]:
                        badge = "guardrail-badge-passed" if tool.get("allowed") else "guardrail-badge-blocked"
                        st.markdown(f'<span class="{badge}">{"ALLOWED" if tool.get("allowed") else "DENIED"}</span> `{tool["tool"]}`', unsafe_allow_html=True)
                if "execution_time_ms" in msg:
                    st.caption(f"Execution time: {msg['execution_time_ms']:.0f}ms")

pending = st.session_state.pop("pending_example", None)
user_input = st.chat_input("Ask about policyholders, policies, or claims...")
if pending:
    user_input = pending

import time as _time


def call_api_with_retry(payload, max_retries=3):
    """Call backend API with automatic retry for 502/503 (Render cold starts)."""
    for attempt in range(max_retries):
        try:
            resp = requests.post(f"{API_URL}/chat", json=payload, timeout=90)
            if resp.status_code in (502, 503) and attempt < max_retries - 1:
                _time.sleep(3)
                continue
            return resp
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                _time.sleep(3)
                continue
            raise
    return resp


if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.total_queries += 1
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Processing through guardrail pipeline..."):
            try:
                chat_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
                resp = call_api_with_retry({"message": user_input, "session_id": st.session_state.session_id, "chat_history": chat_history[-10:], "role": role})
                if resp.status_code == 200:
                    data = resp.json()
                    output = data["output"]
                    blocked = data.get("blocked", False)
                    gr = data.get("guardrail_results", {})
                    if blocked:
                        st.session_state.total_blocked += 1
                        st.error(output)
                    else:
                        st.markdown(output)
                    render_pipeline(gr, blocked)
                    with st.expander("Guardrail Details", expanded=blocked):
                        for layer_name, checks in gr.items():
                            if not checks:
                                continue
                            st.markdown(f"**{layer_name.title()} Layer:**")
                            for check in checks:
                                passed = check.get("passed", check.get("allowed", True))
                                badge = "guardrail-badge-passed" if passed else "guardrail-badge-blocked"
                                st.markdown(f'<span class="{badge}">{"PASSED" if passed else "BLOCKED"}</span> **{check.get("name","")}**: {check.get("reason","")}', unsafe_allow_html=True)
                        if data.get("tools_called"):
                            st.markdown("**Tools Called:**")
                            for tool in data["tools_called"]:
                                badge = "guardrail-badge-passed" if tool.get("allowed") else "guardrail-badge-blocked"
                                st.markdown(f'<span class="{badge}">{"ALLOWED" if tool.get("allowed") else "DENIED"}</span> `{tool["tool"]}`', unsafe_allow_html=True)
                        st.caption(f"Execution time: {data.get('execution_time_ms', 0):.0f}ms")
                    st.session_state.messages.append({"role": "assistant", "content": output, "guardrails": gr, "tools_called": data.get("tools_called", []), "execution_time_ms": data.get("execution_time_ms", 0), "blocked": blocked})
                else:
                    err = f"Backend returned status {resp.status_code}. The server may be waking up — please try again in a few seconds."
                    st.warning(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})
            except requests.exceptions.ConnectionError:
                err = "Cannot connect to backend. Make sure FastAPI is running."
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
            except Exception as e:
                err = f"Error: {str(e)}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
