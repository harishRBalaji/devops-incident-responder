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

# --- Modal-like detail view ---
if selected_id:
    inc = get_incident(selected_id)

    # Create a dialog-like overlay
    st.markdown(
        """
        <style>
        .overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: rgba(0,0,0,0.5);
            z-index: 1000;
        }
        .dialog {
            background: white;
            margin: 5% auto;
            padding: 2rem;
            width: 80%;
            border-radius: 12px;
            max-height: 90vh;
            overflow-y: auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="overlay">', unsafe_allow_html=True)
    st.markdown('<div class="dialog">', unsafe_allow_html=True)

    st.header(f"Incident #{selected_id}")
    st.caption(
        f"Service: {inc['service']} • Env: {inc['environment']} • "
        f"Severity: {inc['severity']} • Created: {inc['created_at']}"
    )

    # Poll steps every 5s
    steps_placeholder = st.empty()
    report_placeholder = st.empty()

    while True:
        steps = list_steps(selected_id)
        with steps_placeholder:
            st.markdown("### Agent Steps")
            if steps:
                for s in steps:
                    with st.expander(s["phase_title"], expanded=True):
                        st.caption(f"Started: {s['ts']}")
                        st.write(s["message"])
                        if s["phase"] == "in_progress":
                            st.spinner("In progress...")
                        elif s["phase"] == "complete":
                            st.success("Completed")
                        elif s["phase"] == "error":
                            st.error("Failed")
            else:
                st.info("No steps yet for this incident.")

        # Report (if available)
        rep = get_latest_report(selected_id)
        with report_placeholder:
            if rep:
                st.markdown("### Final Report")
                st.markdown(rep["report_json"])  # full text report blob
                st.download_button(
                    "Download report.txt",
                    data=rep["report_json"],
                    file_name=f"incident_{selected_id}_report.txt",
                    mime="text/plain",
                )
                break  # stop polling once report is ready
            else:
                st.info("Awaiting final report...")

        time.sleep(REFRESH_INTERVAL)

    st.markdown("</div></div>", unsafe_allow_html=True)