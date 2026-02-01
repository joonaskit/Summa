import streamlit as st
import requests
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import API_URL

with st.expander("Settings", expanded=True):
    base_url = st.text_input("Nexus Base URL", value="https://demo.hedgedoc.org")

tab1, tab2, tab3 = st.tabs(["Ingest", "Chat with a database", "Chat with a file"])

with tab1:
    with st.expander("Ignest files", expanded=True):
        files = requests.get(f"{API_URL}/files")
        if files.status_code == 200:
            files = [node['path'] for node in files.json()]
        else:
            st.error("Could not fetch files")
        selected_files = list(st.multiselect("Files", options=files, key="files"))
        if selected_files:
            st.write(len(selected_files)) #DEBUG
            if st.button("Ingest"):
                response = requests.post(f"{API_URL}/rag/ingest", json={"paths": selected_files})
                if response.status_code in [200, 201]:
                    st.success("Ingestion done!")
                else:
                    st.error("Could not start ingestion")
                    st.write(response.json())

with tab2:
    prompt = st.chat_input("Ask a question", key="question", accept_file=False)
    if prompt:
        with st.container(border=True):
            response = requests.post(f"{API_URL}/rag/query", json={"query": prompt})
            if response.status_code == 200:
                st.write(response.json()['response'])
            else:
                st.error("Could not query")
                st.write(response.json())