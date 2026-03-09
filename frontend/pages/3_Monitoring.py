"""
Monitoring Dashboard — charts, stats, and audit log explorer.
"""

import os
import streamlit as st
import requests
import pandas as pd

API_URL = os.environ.get("API_URL", "http://localhost:8000")
EXL_LOGO_URL = "https://images.seeklogo.com/logo-png/45/1/exl-logo-png_seeklogo-452218.png"

st.set_page_config(page_title="Monitoring Dashboard", page_icon="📊", layout="wide")

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
    .stat-card { background: #161B22 !important; border: 1px solid #30363D !important; }
    .stat-card h3 { color: #58A6FF !important; }
    .stat-card p { color: #8B949E !important; }
    code { background: #21262D !important; color: #C9D1D9 !important; }
    .stSelectbox > div > div { background-color: #21262D !important; color: #C9D1D9 !important; }
    [data-testid="stMetric"] { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 8px !important; padding: 8px !important; }
    [data-testid="stMetricValue"] { color: #58A6FF !important; }
    [data-testid="stMetricLabel"] { color: #8B949E !important; }
</style>
"""

st.markdown("""
<style>
    .main-header { font-size:2.2rem; font-weight:700; background:linear-gradient(135deg,#1E3A5F,#4F46E5); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:0; }
    .sub-header { font-size:1rem; color:#6B7280; margin-top:0; margin-bottom:1.5rem; }
    .stat-card { background:white; border:1px solid #E5E7EB; border-radius:12px; padding:20px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
    .stat-card h3 { color:#1E3A5F; margin:0; font-size:2rem; }
    .stat-card p { color:#6B7280; margin:4px 0 0 0; font-size:0.85rem; }
</style>
""", unsafe_allow_html=True)
if st.session_state.dark_mode:
    st.markdown(DARK_CSS, unsafe_allow_html=True)

h1, h2 = st.columns([1, 8])
with h1:
    st.image(EXL_LOGO_URL, width=80)
with h2:
    st.markdown('<p class="main-header">Monitoring Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Guardrail activity, tool usage, block distribution, and full interaction audit trail</p>', unsafe_allow_html=True)


def fetch_stats():
    try:
        r = requests.get(f"{API_URL}/monitoring/stats", timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def fetch_logs(session_id=None, status=None, layer=None, limit=50, offset=0):
    try:
        params = {"limit": limit, "offset": offset}
        if session_id:
            params["session_id"] = session_id
        if status:
            params["status"] = status
        if layer:
            params["guardrail_layer"] = layer
        r = requests.get(f"{API_URL}/monitoring/logs", params=params, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def fetch_sessions():
    try:
        r = requests.get(f"{API_URL}/monitoring/sessions", timeout=10)
        return r.json().get("sessions", []) if r.status_code == 200 else []
    except Exception:
        return []


stats = fetch_stats()

if stats:
    st.markdown("### System Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="stat-card"><h3>{stats.get("total_pipelines",0)}</h3><p>Total Pipelines</p></div>', unsafe_allow_html=True)
    with c2:
        blocked = stats.get("blocked_count", 0)
        st.markdown(f'<div class="stat-card"><h3 style="color:#DC2626;">{blocked}</h3><p>Blocked Requests</p></div>', unsafe_allow_html=True)
    with c3:
        total_p = max(stats.get("total_pipelines", 1), 1)
        block_rate = blocked / total_p * 100
        st.markdown(f'<div class="stat-card"><h3>{block_rate:.1f}%</h3><p>Block Rate</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><h3>{stats.get("avg_latency_ms",0):.0f}ms</h3><p>Avg Latency</p></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="stat-card"><h3 style="color:#D97706;">{stats.get("hallucination_detected_count",0)}</h3><p>Hallucinations</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Pipeline success/block ratio bar
    if total_p > 0:
        allowed_count = total_p - blocked
        success_pct = allowed_count / total_p * 100
        block_pct = blocked / total_p * 100
        st.markdown("### Pipeline Success Rate")
        st.markdown(
            f'<div style="display:flex;height:28px;border-radius:8px;overflow:hidden;margin:8px 0;">'
            f'<div style="background:#059669;width:{success_pct}%;display:flex;align-items:center;justify-content:center;">'
            f'<span style="color:white;font-size:0.8rem;font-weight:600;">{success_pct:.0f}% Allowed ({allowed_count})</span></div>'
            f'<div style="background:#DC2626;width:{block_pct}%;display:flex;align-items:center;justify-content:center;">'
            f'<span style="color:white;font-size:0.8rem;font-weight:600;">{block_pct:.0f}% Blocked ({blocked})</span></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("")

    chart_c1, chart_c2 = st.columns(2)

    with chart_c1:
        st.markdown("### Guardrail Block Distribution")
        block_counts = stats.get("guardrail_block_counts", {})
        if block_counts:
            layers_order = ["policy", "input", "instructional", "execution", "output", "monitoring"]
            chart_data = [{"Layer": l.title(), "Blocks": block_counts.get(l, 0)} for l in layers_order if block_counts.get(l, 0) > 0]
            if chart_data:
                df_blocks = pd.DataFrame(chart_data)
                st.bar_chart(df_blocks.set_index("Layer"), color="#DC2626")
                total_blocks = sum(d["Blocks"] for d in chart_data)
                for d in chart_data:
                    pct = d["Blocks"] / total_blocks * 100 if total_blocks > 0 else 0
                    bar_w = max(5, int(pct * 2.5))
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
                        f'<span style="width:100px;font-size:0.85rem;">{d["Layer"]}</span>'
                        f'<div style="background:#DC2626;border-radius:4px;height:18px;width:{bar_w}%;min-width:30px;display:flex;align-items:center;justify-content:center;">'
                        f'<span style="color:white;font-size:0.7rem;font-weight:600;">{d["Blocks"]}</span></div>'
                        f'<span style="font-size:0.8rem;color:#6B7280;">{pct:.0f}%</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No guardrail blocks recorded yet.")
        else:
            st.info("No guardrail blocks recorded yet.")

    with chart_c2:
        st.markdown("### Tool Usage")
        tool_usage = stats.get("tool_usage", {})
        if tool_usage:
            for tool_name, counts in sorted(tool_usage.items(), key=lambda x: x[1].get("allowed",0)+x[1].get("blocked",0), reverse=True):
                allowed = counts.get("allowed", 0)
                tool_blocked = counts.get("blocked", 0)
                total_t = allowed + tool_blocked
                allowed_pct = (allowed / total_t * 100) if total_t > 0 else 0
                st.markdown(
                    f'<div style="margin:10px 0;">'
                    f'<div style="display:flex;justify-content:space-between;"><code>{tool_name}</code><span style="font-size:0.85rem;">{total_t} calls</span></div>'
                    f'<div style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin-top:4px;">'
                    f'<div style="background:#059669;width:{allowed_pct}%;"></div>'
                    f'<div style="background:#DC2626;width:{100-allowed_pct}%;"></div></div>'
                    f'<div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#6B7280;">'
                    f'<span>✅ {allowed} allowed</span><span>❌ {tool_blocked} blocked</span></div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No tool usage recorded yet.")
else:
    st.warning("Could not connect to the backend API. Make sure FastAPI is running on http://localhost:8000")

st.markdown("---")
st.markdown("### Guardrail Logs")

with st.expander("Filters", expanded=True):
    fc = st.columns(4)
    with fc[0]:
        sessions = fetch_sessions()
        selected_session = st.selectbox("Session ID", ["All"] + sessions)
    with fc[1]:
        selected_status = st.selectbox("Action", ["All", "passed", "blocked", "completed"])
    with fc[2]:
        selected_layer = st.selectbox("Guardrail Layer", ["All", "policy", "input", "instructional", "execution", "output", "monitoring"])
    with fc[3]:
        page_size = st.selectbox("Rows per page", [25, 50, 100], index=1)

if "log_page" not in st.session_state:
    st.session_state.log_page = 0

nc = st.columns([1, 1, 6])
with nc[0]:
    if st.button("← Previous") and st.session_state.log_page > 0:
        st.session_state.log_page -= 1
with nc[1]:
    if st.button("Next →"):
        st.session_state.log_page += 1

offset = st.session_state.log_page * page_size
logs_data = fetch_logs(
    session_id=selected_session if selected_session != "All" else None,
    status=selected_status if selected_status != "All" else None,
    layer=selected_layer if selected_layer != "All" else None,
    limit=page_size, offset=offset,
)

if logs_data and logs_data.get("logs"):
    total = logs_data.get("total", 0)
    st.caption(f"Showing {offset+1}–{min(offset+page_size, total)} of {total} entries (Page {st.session_state.log_page+1})")
    logs = logs_data["logs"]
    display_data = []
    for log in logs:
        display_data.append({
            "Timestamp": log.get("timestamp", "")[:19],
            "Session": (log.get("session_id") or "")[:12] + "...",
            "Layer": log.get("guardrail_layer", ""),
            "Check": log.get("guardrail_name", ""),
            "Action": log.get("action", ""),
            "Blocked": "Yes" if log.get("blocked") else "No",
            "Hallucination": "Yes" if log.get("hallucination_flag") else "",
            "Tool": log.get("tool_called") or "",
            "Time (ms)": log.get("execution_time_ms") or "",
        })
    df = pd.DataFrame(display_data)

    def color_action(val):
        if val == "blocked":
            return "background-color:#FEE2E2;color:#991B1B"
        elif val == "passed":
            return "background-color:#D1FAE5;color:#065F46"
        elif val == "completed":
            return "background-color:#DBEAFE;color:#1E40AF"
        return ""

    style_func = getattr(df.style, "map", None) or df.style.applymap
    styled = style_func(color_action, subset=["Action"])
    st.dataframe(styled, use_container_width=True, hide_index=True, height=500)

    st.markdown("#### Log Detail View")
    row_idx = st.number_input("Row number", min_value=0, max_value=len(logs)-1, value=0, step=1)
    if 0 <= row_idx < len(logs):
        log = logs[row_idx]
        dc = st.columns(2)
        with dc[0]:
            st.markdown("**Input**")
            st.text(log.get("user_input") or "(none)")
            if log.get("sanitized_input"):
                st.markdown("**Sanitized Input**")
                st.text(log["sanitized_input"])
            if log.get("tool_called"):
                st.markdown("**Tool Called**")
                st.text(f"{'✅' if log.get('tool_allowed') else '❌'} {log['tool_called']} (allowed: {log.get('tool_allowed')})")
        with dc[1]:
            if log.get("llm_raw_output"):
                st.markdown("**LLM Raw Output**")
                st.text(log["llm_raw_output"][:500])
            if log.get("llm_final_output"):
                st.markdown("**Final Output**")
                st.text(log["llm_final_output"][:500])
            if log.get("details"):
                st.markdown("**Details (JSON)**")
                st.json(log["details"])
elif logs_data:
    st.info("No log entries found for the selected filters.")
else:
    st.warning("Could not fetch logs. Make sure the backend is running.")
