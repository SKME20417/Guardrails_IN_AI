"""
Side-by-Side Role Comparison — send one query to all 3 roles simultaneously.
"""

import os
import streamlit as st
import requests
import time
import pandas as pd

API_URL = os.environ.get("API_URL", "http://localhost:8000")
EXL_LOGO_URL = "https://images.seeklogo.com/logo-png/45/1/exl-logo-png_seeklogo-452218.png"

st.set_page_config(page_title="Role Comparison", page_icon="⚖️", layout="wide")

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

DARK_CSS = """
<style>
    .stApp { background-color: #0E1117 !important; color: #FAFAFA !important; }
    [data-testid="stSidebar"] { background-color: #161B22 !important; }
    [data-testid="stSidebar"] * { color: #C9D1D9 !important; }
    .stMarkdown, .stText, p, span, label { color: #C9D1D9 !important; }
    h1, h2, h3, h4, h5, h6 { color: #E6EDF3 !important; }
    .stExpander { background-color: #161B22 !important; border: 1px solid #30363D !important; }
    .stDataFrame { background-color: #161B22 !important; }
    .main-header { background: linear-gradient(135deg,#58A6FF,#BC8CFF) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; }
    .sub-header { color: #8B949E !important; }
    .pipeline-step.skipped { background: #21262D !important; color: #484F58 !important; border-color: #30363D !important; }
    .pipeline-step.passed { background: #0D1117 !important; color: #3FB950 !important; border-color: #238636 !important; }
    .pipeline-step.blocked { background: #0D1117 !important; color: #F85149 !important; border-color: #DA3633 !important; }
    .guardrail-badge-blocked { background: #2D1117 !important; color: #F85149 !important; }
    code { background: #21262D !important; color: #C9D1D9 !important; }
    .stSelectbox > div > div { background-color: #21262D !important; color: #C9D1D9 !important; }
    .stTextInput > div > div > input { background-color: #21262D !important; color: #C9D1D9 !important; }
</style>
"""

st.markdown("""
<style>
    .main-header { font-size:2.2rem; font-weight:700; background:linear-gradient(135deg,#1E3A5F,#4F46E5); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:0; }
    .sub-header { font-size:1rem; color:#6B7280; margin-top:0; margin-bottom:1.5rem; }
    .pipeline-container { display:flex; align-items:center; gap:4px; padding:10px 0; margin:8px 0; flex-wrap:wrap; }
    .pipeline-step { display:flex; align-items:center; gap:6px; padding:6px 14px; border-radius:8px; font-size:0.8rem; font-weight:600; white-space:nowrap; }
    .pipeline-step.passed { background:#D1FAE5; color:#065F46; border:1px solid #A7F3D0; }
    .pipeline-step.blocked { background:#FEE2E2; color:#991B1B; border:1px solid #FECACA; }
    .pipeline-step.skipped { background:#F3F4F6; color:#9CA3AF; border:1px solid #E5E7EB; }
    .guardrail-badge-blocked { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; background:#FEE2E2; color:#991B1B; margin:2px 4px; }
</style>
""", unsafe_allow_html=True)
if st.session_state.dark_mode:
    st.markdown(DARK_CSS, unsafe_allow_html=True)


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


h1, h2 = st.columns([1, 8])
with h1:
    st.image(EXL_LOGO_URL, width=80)
with h2:
    st.markdown('<p class="main-header">Role Comparison</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Send one query to all 3 roles — see how guardrails enforce different access levels</p>', unsafe_allow_html=True)

PRESET_QUERIES = [
    "Show me all claims with fraud flags",
    "What are the risk scores of policyholders?",
    "Show me policyholder email addresses",
    "Show the schema of the claims table",
    "List all denied claims with reasons",
    "Show me all active policyholders",
    "SELECT claim_type, COUNT(*) as cnt FROM claims GROUP BY claim_type LIMIT 10",
    "Show me premium amounts for all policyholders",
]

st.markdown("### Choose a query")
col_p, col_c = st.columns([1, 1])
with col_p:
    preset = st.selectbox("Preset queries (best for demo)", ["(custom)"] + PRESET_QUERIES)
with col_c:
    custom = st.text_input("Or type your own query")

query = custom.strip() if custom.strip() else (preset if preset != "(custom)" else "")

if st.button("Compare Across All Roles", type="primary", use_container_width=True, disabled=not query):
    roles = [
        ("agent", "Agent", "🔵", "#3B82F6", "#EFF6FF"),
        ("claims_adjuster", "Claims Adjuster", "🟡", "#F59E0B", "#FFFBEB"),
        ("auditor", "Auditor", "🟢", "#10B981", "#ECFDF5"),
    ]
    cols = st.columns(3)
    results = {}

    for i, (role_id, role_name, emoji, color, bg) in enumerate(roles):
        with cols[i]:
            st.markdown(
                f'<div style="background:{bg};border:2px solid {color};border-radius:12px;padding:12px 16px;margin-bottom:12px;">'
                f'<h3 style="margin:0;color:{color};">{emoji} {role_name}</h3></div>',
                unsafe_allow_html=True,
            )
            with st.spinner(f"Querying as {role_name}..."):
                try:
                    resp = requests.post(f"{API_URL}/chat", json={"message": query, "role": role_id, "session_id": f"compare-{role_id}-{int(time.time())}"}, timeout=60)
                    data = resp.json()
                    results[role_id] = data
                except Exception as e:
                    st.error(f"Error: {e}")
                    continue

            blocked = data.get("blocked", False)
            output = data.get("output", "")
            gr = data.get("guardrail_results", {})

            if blocked:
                st.markdown(f'<div style="background:#FEE2E2;border:1px solid #FECACA;border-radius:8px;padding:10px;margin:8px 0;"><strong style="color:#991B1B;">🚫 BLOCKED</strong></div>', unsafe_allow_html=True)
                st.caption(data.get("block_reason", ""))
            else:
                st.markdown(f'<div style="background:#D1FAE5;border:1px solid #A7F3D0;border-radius:8px;padding:10px;margin:8px 0;"><strong style="color:#065F46;">✅ ALLOWED</strong></div>', unsafe_allow_html=True)

            render_pipeline(gr, blocked)

            with st.expander("Response", expanded=not blocked):
                st.text(output[:500] + ("..." if len(output) > 500 else ""))

            with st.expander("Guardrail Details"):
                for layer_name, checks in gr.items():
                    for check in (checks or []):
                        passed = check.get("passed", check.get("allowed", True))
                        if not passed:
                            st.markdown(f'<span class="guardrail-badge-blocked">BLOCKED</span> **{layer_name}** / {check.get("name","")}: {check.get("reason","")}', unsafe_allow_html=True)
                tools = data.get("tools_called", [])
                if tools:
                    for t in tools:
                        st.caption(f"{'✅' if t.get('allowed') else '❌'} {t['tool']}")

            st.caption(f"⏱️ {data.get('execution_time_ms', 0):.0f}ms")

    if results:
        st.markdown("---")
        st.markdown("### Summary")
        summary_cols = st.columns(3)
        for i, (role_id, role_name, emoji, color, bg) in enumerate(roles):
            if role_id in results:
                d = results[role_id]
                with summary_cols[i]:
                    if d.get("blocked"):
                        st.markdown(f"**{emoji} {role_name}**: 🚫 Blocked")
                    else:
                        st.markdown(f"**{emoji} {role_name}**: ✅ Allowed ({len(d.get('tools_called', []))} tools)")

elif not query:
    st.info("Select a preset query or type your own above, then click **Compare Across All Roles**.")

st.markdown("---")
st.markdown("### Role Permission Matrix")
matrix_data = {
    "Feature": ["Policyholder names/city", "Email / Phone / DOB", "Address details", "Premium & coverage amounts", "Claims data", "Fraud flags", "Risk scores", "Database schema", "Custom SQL queries", "Monitoring logs"],
    "🔵 Agent": ["✅","❌","❌","❌","❌","❌","❌","❌","❌","❌"],
    "🟡 Claims Adjuster": ["✅","✅","✅","✅","✅","❌","❌","❌","❌","❌"],
    "🟢 Auditor": ["✅","✅","✅","✅","✅","✅","✅","✅","✅","✅"],
}
st.dataframe(pd.DataFrame(matrix_data), use_container_width=True, hide_index=True, height=400)
