# ui/streamlit_app.py
import time
import json
import pandas as pd
import streamlit as st

from app.db.dal import (
    list_incidents,
    get_incident,
    list_steps,
    get_latest_report,
)

st.set_page_config(page_title="Incident Responder", layout="wide")
st.title("🔧 DevOps Incident Responder — MVP")

REFRESH_INTERVAL = 5  # seconds

# --- Load incidents ---
incidents = list_incidents(limit=50)

if not incidents:
    st.info("No incidents yet. Go back to code/coffee and chill!")
    st.stop()

# --- Cards view ---
st.subheader("Active Incidents")
cols = st.columns(3, gap="large")

selected_id = None
for i, inc in enumerate(incidents):
    with cols[i % 3]:
        card = st.container(border=True)
        with card:
            st.markdown(f"**Incident #{inc['id']}**")
            st.caption(
                f"Service: {inc['service']} • Env: {inc['environment']} • "
                f"Severity: {inc['severity']} • Status: {inc['status']}"
            )
            if st.button("Open", key=f"open-{inc['id']}"):
                selected_id = inc["id"]

# --- Inline detail view (no modal) ---
if selected_id:
    inc = get_incident(selected_id)

    st.subheader(f"Incident #{selected_id}")
    st.caption(
        f"Service: {inc['service']} • Env: {inc['environment']} • "
        f"Severity: {inc['severity']} • Created: {inc['created_at']} • Status: {inc['status']}"
    )

    # Placeholders we’ll update in a loop
    steps_placeholder = st.empty()
    report_placeholder = st.empty()

    while True:
        # ---- Steps ----
        steps = list_steps(selected_id)
        with steps_placeholder:
            st.markdown("### Agent Steps")
            if steps:
                for s in steps:
                    with st.expander(s["phase_title"], expanded=True):
                        st.caption(f"Started: {s['ts']}")
                        st.write(s["message"])
                        if s["phase"] == "in_progress":
                            st.info("In progress…")
                        elif s["phase"] == "complete":
                            st.success("Completed")
                        elif s["phase"] == "error":
                            st.error("Failed")
                        else:
                            st.warning(f"Unknown phase: {s['phase']}")
            else:
                st.info("No steps yet for this incident.")

        # ---- Final report (if available) ----
        rep = get_latest_report(selected_id)
        with report_placeholder:
            if rep:
                st.markdown("### Final Report")

                # Support both legacy ('report_json') and current ('report') keys.
                # If we get a dict (JSON), show it with st.json; if it's a string, render as HTML.
                raw = rep.get("report_json")
                if raw is None:
                    raw = rep.get("report", "")

                if isinstance(raw, dict):
                    st.json(raw)
                else:
                    # raw is expected to be HTML (string). Fallback: pretty-print if not str.
                    html = raw if isinstance(raw, str) else json.dumps(raw, indent=2)
                    st.markdown(html, unsafe_allow_html=True)

                # Stop polling once the report is shown
                break
            else:
                st.info("Awaiting final report...")

        time.sleep(REFRESH_INTERVAL)
