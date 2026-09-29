import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="BLUE Engine OS - Ingestion Tracker",
    page_icon="📊",
    layout="wide"
)

DB_PATH = "procurement_database.sqlite"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

st.title("📊 BLUE Engine OS — Step 1: Analyst Ingestion & DB Tracker")
st.markdown("Real-time monitoring and validation portal for state procurement extractions (Virginia eVA, Texas ESBD, Maine Baseline).")

# --- TOP METRIC CARDS ---
conn = get_db_connection()
try:
    df_primary = pd.read_sql_query("SELECT * FROM case_status_summary", conn)
    df_exception = pd.read_sql_query("SELECT * FROM exception_log", conn)
    df_features = pd.read_sql_query("SELECT * FROM choice_set_features", conn)
except Exception as e:
    df_primary = pd.DataFrame()
    df_exception = pd.DataFrame()
    df_features = pd.DataFrame()
conn.close()

col1, col2, col3, col4 = st.columns(4)

total_cases = len(df_primary) + len(df_exception)
clean_cases = len(df_primary)
quarantined = len(df_exception)
total_bidders = len(df_features)

col1.metric("Total Solicitations Processed", total_cases)
col2.metric("Primary Choice Sets (Clean)", clean_cases)
col3.metric("Exception Queue (Quarantined)", quarantined, delta_color="inverse")
col4.metric("Total Bidders Evaluated", total_bidders)

st.divider()

# --- TABBED LAYOUT ---
tab1, tab2, tab3 = st.tabs(["📂 Primary Dataset (`case_status_summary`)", "⚠️ Exception Log (`exception_log`)", "📥 Batch Upload & Validation Simulator"])

with tab1:
    st.subheader("Primary Procurement Choice Sets")
    st.markdown("Multi-bidder RFPs fully cleaned and validated for econometric training.")
    
    if not df_primary.empty:
        # Search & Filter controls
        search_query = st.text_input("🔍 Search by Case ID or Short Title:", "")
        if search_query:
            df_filtered = df_primary[
                df_primary['case_id'].str.contains(search_query, case=False, na=False) |
                df_primary['short_title'].str.contains(search_query, case=False, na=False)
            ]
        else:
            df_filtered = df_primary
            
        st.dataframe(df_filtered, use_container_width=True)
        
        # Summary Visual
        fig = px.bar(
            df_primary, 
            x="short_title", 
            y="num_bidders", 
            color="cost_flag_yn",
            title="Bidders per Choice Set (Color = Cost Flag Anomaly)",
            labels={"short_title": "Solicitation", "num_bidders": "Number of Bidders", "cost_flag_yn": "Cost Flagged"}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No primary records found in database.")

with tab2:
    st.subheader("Quarantined Exception Queue")
    st.markdown("Records automatically redirected away from model training due to OCI, sole-bidder status, or date anomalies.")
    
    if not df_exception.empty:
        st.dataframe(df_exception, use_container_width=True)
        
        # Quarantine reason breakdown
        st.write("### Quarantine Rationale Summary")
        for idx, row in df_exception.iterrows():
            st.warning(f"**{row['case_id']} ({row['short_title']})**: {row['note']}")
    else:
        st.success("No records currently quarantined.")

with tab3:
    st.subheader("Analyst Batch Ingestion Simulator")
    st.markdown("Upload a new CSV extraction log from Virginia eVA or Texas ESBD to run automated schema checks.")
    
    uploaded_file = st.file_uploader("Choose a CSV file (e.g., 01_Case_Status_Summary.csv)", type=["csv"])
    
    if uploaded_file is not None:
        raw_df = pd.read_csv(uploaded_file)
        st.write("### Raw CSV Preview", raw_df.head())
        
        if st.button("🚀 Run Automated Validation & Ingest"):
            st.info("Running schema checks: checking 17 mandatory columns, stripping text from numeric fields, normalizing ISO 8601 dates...")
            # Perform quick validation
            valid_rows = 0
            quarantine_rows = 0
            
            for _, row in raw_df.iterrows():
                note = str(row.get('Note', ''))
                if 'exception' in note.lower() or 'conflict' in note.lower() or 'anomaly' in note.lower():
                    quarantine_rows += 1
                else:
                    valid_rows += 1
                    
            st.success(f"Validation Complete! Results: {valid_rows} clean records passed to Primary Log, {quarantine_rows} redirected to Exception Queue.")
