import streamlit as st
from sqlalchemy import create_engine, text
from app.config import DB_URL
import pandas as pd

st.set_page_config(page_title='Incident Responder', layout='wide')
st.title('🔧 DevOps Incident Responder — MVP')

engine = create_engine(DB_URL, future=True)

def load_df(sql, params=None):
    with engine.begin() as conn:
        res = conn.execute(text(sql), params or {})
        rows = [dict(r._mapping) for r in res]
        return pd.DataFrame(rows)

tabs = st.tabs(['Incidents','Agent Steps','Reports'])

with tabs[0]:
    st.header('Incidents')
    st.caption('Auto-refresh every ~5s (use Streamlit rerun)')
    if st.button('Refresh incidents'):
        st.experimental_rerun()
    df = load_df('SELECT * FROM incidents ORDER BY id DESC')
    st.dataframe(df, use_container_width=True)

with tabs[1]:
    st.header('Agent Steps')
    if st.button('Refresh steps'):
        st.experimental_rerun()
    df = load_df('SELECT * FROM agent_steps ORDER BY ts DESC, id DESC')
    st.dataframe(df, use_container_width=True)

with tabs[2]:
    st.header('Reports')
    if st.button('Refresh reports'):
        st.experimental_rerun()
    df = load_df('SELECT id, incident_id, substr(report_md,1,120) AS preview, created_at FROM reports ORDER BY id DESC')
    st.dataframe(df, use_container_width=True)
    rid = st.text_input('Open report by incident_id')
    if rid:
        rdf = load_df('SELECT report_md FROM reports WHERE incident_id = :i', {'i': rid})
        if not rdf.empty:
            st.markdown(rdf.iloc[0]['report_md'])
        else:
            st.info('No report found.')
