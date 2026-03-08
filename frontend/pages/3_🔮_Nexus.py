import streamlit as st
import requests
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import API_URL

st.session_state["upload_status"] = 404

@st.cache_data
def get_models():
    try:
        response = requests.get(f"{API_URL}/llm/models")
        if response.status_code == 200:
            return [model['id'] for model in response.json()]
        else:
            st.error("Could not fetch models")
            return []
    except Exception as e:
        st.error(f"Error fetching models: {str(e)}")
        return []

def _get_source_details(source):
    try:
        response = requests.get(f"{API_URL}/files/content", params={"path": source['source']})
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Error fetching source details: {str(e)}")
        return None

def _get_source_summary(source):
    try:
        response = requests.get(f"{API_URL}/files/summary", params={"path": source['source']})
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Error fetching source summary: {str(e)}")
        return None

def _get_video_summary(source):
    try:
        response = requests.get(f"{API_URL}/video/summary", params={"video_id":source['video_id']})
        if response.status_code in [200, 201]:
            return response.json()
        else: 
            return None
    except Exception as e:
        st.error(f"Error fetching video summary: {e}")
        return None

@st.dialog("Source details", width="medium")
def source_details(source):
    content = _get_source_details(source)["content"]
    with st.expander("Content", expanded=False):
        st.write(content)
    try:
        summary = _get_source_summary(source)["summary_text"]
    except Exception as e:
        summary = None
    if summary:
        with st.expander("Summary", expanded=False):
            st.write(summary)
    else:
        st.write("No summary available")

@st.dialog("Source details", width="medium")
def source_video_details(source):
    st.title(source['title'])
    st.video(source['source'])

    summary = _get_video_summary(source)
    if summary:
        with st.expander("Summary"):
            st.write(summary['summary_text'])
    else:
        st.write("No summary available")


def get_base_url():
    return os.getenv("LLM_URL", "http://host.docker.internal:1234/v1")

def rag_query(prompt):
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.status("Thinking...") as status:
        try:
            response = requests.post(
                f"{API_URL}/rag/query", 
                json={
                    "query": prompt,
                    "multiquery":st.session_state.multi_query
                    }
            )
            if response.status_code == 200:
                answer = response.json()['result'].get('response', 'No response received')
                sources = response.json().get('sources', [])
                context = {"answer": answer, "sources": sources}
                st.session_state.chat_messages.append({"role": "assistant", "content": context})
                status.update(label="Done", state="complete")
                st.rerun()
            else:
                error_msg = f"❌ Error {response.status_code}: {response.text}"
                st.error(error_msg)
                st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
                status.update(label="Error", state="error")
        except Exception as e:
            error_msg = f"❌ Unexpected error: {str(e)}"
            st.error(error_msg)
            st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
            status.update(label="Error", state="error")

def print_chat_history():
    for i,message in enumerate(st.session_state.chat_messages):
        if message['role'] == "assistant":
            with st.chat_message(message['role']):
                st.markdown(message['content']['answer'])
                st.divider()
                with st.expander("Sources considered:", expanded=False):
                    for source in message['content']['sources']:
                        if "type" in source.keys():
                            # This is probably a video
                            # #TODO: Next we need to see if this is a local or youtube
                            if source["type"] == "video_transcript":
                                if st.button(source['title'], key=f"source_{source['title']}#{i}"):
                                    source_video_details(source)
                        elif st.button(source["source"], key=f"source_{source}#{i}"):
                            # Not a video!
                            source_details(source)
                # st.session_state.selected_source = st.pills("Sources considered", message['content']['sources'], key=f"sources_{message['content']['answer']}", default=None, selection_mode="single", on_change=source_details)
        else:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])



with st.expander("Settings", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        base_url = st.text_input("Nexus Base URL", value=get_base_url())
    with c2:
        models = get_models()
        st.session_state["model"] = st.selectbox("Model", options=models)
    with c3:
        rerank = os.getenv("ENABLE_RERANK", "false").lower() == "true"
        if not rerank:
            st.warning("Cross encoder is not in use. Results may wary")
        st.session_state.multi_query = st.toggle("Use multiquery", value=False, key="Multiquery")
        if st.button("Clear all chat history"):
            st.session_state["chat_messages"] = []
            st.session_state["conv_log"] = []
            st.rerun()

tab1, tab2 = st.tabs(["Chat with a database", "Chat with a file"])


with tab1:
    st.markdown("### 💬 Chat with Your Database")
    st.markdown("Ask questions about the ingested documents and get AI-powered answers.")
    
    # Initialize chat history in session state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    if "multi_query" not in st.session_state:
        session_state.multi_query = False
    
    
    # Chat messages container with fixed height for better scrolling
    
    if len(st.session_state.chat_messages) == 0:
        # First message
        prompt = st.chat_input("Ask a question about your documents...", key="question")
        if prompt: 
            rag_query(prompt)
    else:
        # Display chat history
        print_chat_history()
        
        prompt = st.chat_input("Ask a question about your documents...")
        if st.button("Clear chat history", help="Clear chat history"):
            st.session_state.chat_messages = []
            st.rerun()
        if prompt:
            rag_query(prompt)

with tab2:
    # Initialize session state for uploader reset
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    # Display success message from previous run if enabled
    if "upload_success_msg" in st.session_state:
        st.success(st.session_state["upload_success_msg"])
        del st.session_state["upload_success_msg"]
    
    if "conv_log" not in st.session_state:
        st.session_state["conv_log"] = []

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

        if len(st.session_state.conv_log) == 0:
            # No conversation yet
            prompt = st.chat_input(f"Ask a question about {st.session_state['filename']}...", accept_file=False)
            if prompt:
                st.session_state.conv_log.append({"role": "user", "content": prompt})
                with st.status("Thinking...") as status:
                    response = requests.post(
                        f"{API_URL}/rag/query",
                        json={"query": prompt, "inmemory": True}
                    )
                    if response.status_code in [200, 201]:
                        status.update(state="complete")
                        
                        answer = response.json().get('response', 'No response received')
                        st.markdown(answer)
                        st.session_state.conv_log.append({"role": "assistant", "content": answer})
                        st.rerun()
                    else:
                        st.error(response.text)
                        status.update(label=f"Error: {response.text}", state="error", expanded=True)
            
        else:
            # Conversation in progress
            # Print conversation log
            for message in st.session_state.conv_log:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            prompt = st.chat_input(f"Ask a question about {st.session_state['filename']}...", accept_file=False)
            if prompt:
                st.session_state.conv_log.append({"role": "user", "content": prompt})
                with st.status("Thinking...") as status:
                    response = requests.post(
                        f"{API_URL}/rag/query",
                        json={"query": prompt, "inmemory": True}
                    )
                    if response.status_code in [200, 201]:
                        status.update(state="complete")
                        answer = response.json().get('response', 'No response received')
                        st.markdown(answer)
                        st.session_state.conv_log.append({"role": "assistant", "content": answer})
                        st.rerun()
                    else:
                        st.error(response.text)
                        status.update(label=f"Error: {response.text}", state="error", expanded=True)
            
            # Clear chat log button
            if st.button("Clear chat log", key="clear_chat_log"):
                st.session_state.conv_log = []
                st.rerun()