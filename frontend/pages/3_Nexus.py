import streamlit as st
import requests
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import API_URL

st.session_state["upload_status"] = 404

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

    st.markdown("### 💬 Chat with Your Database")
    st.markdown("Ask questions about the ingested documents and get AI-powered answers.")
    
    # Initialize chat history in session state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # Clear chat button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🗑️ Clear", help="Clear chat history"):
            st.session_state.chat_messages = []
            st.rerun()
    
    # Chat input - placing it after the container helps with positioning
    prompt = st.chat_input("Ask a question about your documents...", key="question")
    
    # Chat messages container with fixed height for better scrolling
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt:
        # Add user message to chat history
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Display assistant response with loading state
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{API_URL}/rag/query", 
                        json={"query": prompt},
                        timeout=30  # 30 second timeout
                    )
                    
                    if response.status_code == 200:
                        answer = response.json().get('response', 'No response received')
                        st.markdown(answer)
                        # Add assistant response to chat history
                        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
                    else:
                        error_msg = f"❌ Error {response.status_code}: {response.text}"
                        st.error(error_msg)
                        st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
                        
                except requests.exceptions.Timeout:
                    error_msg = "⏱️ Request timed out. The query took too long to process."
                    st.error(error_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
                    
                except requests.exceptions.ConnectionError:
                    error_msg = "🔌 Connection error. Could not reach the API server."
                    st.error(error_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
                    
                except Exception as e:
                    error_msg = f"❌ Unexpected error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})


with tab3:
    # Initialize session state for uploader reset
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    # Display success message from previous run if enabled
    if "upload_success_msg" in st.session_state:
        st.success(st.session_state["upload_success_msg"])
        del st.session_state["upload_success_msg"]

    # Use dynamic key to allow resetting
    uploaded_file = st.file_uploader(
        "Choose files or drag a folder", 
        type=['md', 'txt', 'pdf', 'docx', 'pptx'], 
        accept_multiple_files=False,
        key=f"uploader_{st.session_state['uploader_key']}",
    )

    if uploaded_file:
        upload_status = st.status("Uploading files...")
        try:
            response = requests.post(
                f"{API_URL}/rag/ingest_uploaded_file",
                params={"inmemory": True},
                files={"file": uploaded_file}
            )
            if response.status_code in [200, 201]:
                st.write(response.json())
                upload_status.update(label="File uploaded", state="complete")
                st.session_state["uploader_key"] += 1
                st.session_state["content"] = response.json().get("content")
                st.session_state["filename"] = response.json().get("filename")
                st.session_state["upload_status"] = response.status_code
            else:
                upload_status.update(label=f"Error: {response.text}", state="error")
                st.session_state["uploader_key"] += 1
        except Exception as e:
            upload_status.update(label=f"Error: {e}", state="error")
            st.session_state["uploader_key"] += 1
    if "content" in st.session_state:
        st.divider()
        st.markdown(f"## Chatting about file {st.session_state['filename']}")

        if st.button("Summarize file", key="summarize_file"):
            summary_status_widget = st.status("Summarizing file...", state="running")
            summary_resp = requests.get(f"{API_URL}/llm/summary", params={"content": st.session_state["content"], "filename": st.session_state["filename"]})
            if summary_resp.status_code in [200, 201]:
                summary_status_widget.write_stream(summary_resp.iter_content(chunk_size=1024, decode_unicode=True))
                summary_status_widget.update(label="File summarized", state="complete", expanded=True)
            else:
                st.error(summary_resp.text)
                summary_status_widget.update(label=f"Error: {summary_resp.text}", state="error", expanded=True)
            
        st.divider()
        st.session_state.summary_question = ""
        st.write(st.session_state.summary_question)

        chat_row = st.container(
            horizontal=True,
            vertical_alignment="bottom",
        )
        with chat_row:
            st.chat_input(f"Ask a question about {st.session_state['filename']}...")
        
        
        # Initialize chat history
        if "summary_chat_messages" not in st.session_state:
            st.session_state.summary_chat_messages = []
        
        # Clear chat button
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("🗑️ Clear", help="Clear chat history", key="clear_summary_chat"):
                st.session_state.summary_chat_messages = []
                st.rerun()
        
        # --- 1. DISPLAY EXISTING CHAT HISTORY FIRST ---
        # Writing directly to the main flow allows Streamlit to handle the
        # bottom padding automatically so the input doesn't cover the last message.
        for message in st.session_state.summary_chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # --- 3. HANDLE NEW INTERACTION ---
        if len(st.session_state.summary_question) > 0:
            # A. Display user message immediately (visual update)
            with st.chat_message("user"):
                st.markdown(st.session_state.summary_question)
            
            # B. Add user message to history (data update)
            st.session_state.summary_chat_messages.append({"role": "user", "content": st.session_state.summary_question})
            
            # C. Generate and display assistant response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/rag/query", 
                            json={"query": st.session_state.summary_question, "inmemory":True},
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            answer = response.json().get('response', 'No response received')
                            st.markdown(answer)
                            # Add assistant response to history
                            st.session_state.summary_chat_messages.append({"role": "assistant", "content": answer})
                        else:
                            error_msg = f"❌ Error {response.status_code}: {response.text}"
                            st.error(error_msg)
                            st.session_state.summary_chat_messages.append({"role": "assistant", "content": error_msg})
                            
                    except Exception as e:
                        error_msg = f"❌ Error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.summary_chat_messages.append({"role": "assistant", "content": error_msg})
                
    # --- 2. CHAT INPUT (Pinned to Bottom) ---
    # This is placed AFTER the history loops in the code.
    if "content" in st.session_state:
        st.session_state.summary_question = st.chat_input(f"Ask a question about {st.session_state['filename']}...", key="summary_question_prompt")