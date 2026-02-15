import streamlit as st
import requests
from utils import API_URL
import io

st.title("Video Analyst")

if "video_info" not in st.session_state:
    st.session_state.video_info = {}

if "transcript" not in st.session_state:
    st.session_state.transcript = None

if "summary" not in st.session_state:
    st.session_state.summary = None

if "youtube_chat" not in st.session_state:
    st.session_state.youtube_chat = []

if "uploaded" not in st.session_state:
    st.session_state.uploaded = False

@st.cache_data
def get_video_transcription(url, filename):
    response = requests.post(f"{API_URL}/video/transcribe", json={"url": url})
    if response.status_code == 200:
        return {"status":response.status_code, "transcript":response.json()["transcript"]}
    else:
        raise Exception(f"Transcription failed {response.status_code}: {response.text}")

t1, t2, t3 = st.tabs(["Youtube", "Local Video", "Library"])

with t1:
    st.header("Youtube")
    url = st.text_input("Youtube URL")
    if url != st.session_state.video_info.get("url"):
        st.session_state.transcript = None
        st.session_state.summary = None
        st.session_state.video_info = {}
    if url:
        response = requests.post(f"{API_URL}/video/info", json={"url": url})
        if response.status_code == 200:
            data = response.json()
            st.subheader(data["title"])
            st.caption(data["author"])
            st.video(url)
            data['url'] = url
            st.session_state.video_info = data
            
            if st.session_state.transcript:
                with st.expander("Transcript", expanded=False):
                    st.write(st.session_state.transcript)
            else:
                st.caption("Transcriptions will be cached in the database for faster access")
                if st.button("Transcribe and cache"):
                    with st.status("Transcribing...") as status:
                        try:
                            result = get_video_transcription(url, data["title"])
                            st.session_state.transcript  = result["transcript"]
                            st.write(st.session_state.transcript)
                            status.update(label="Transcription completed", state="complete", expanded=True)
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            status.update(label="Transcription failed", state="error")
            
            if st.session_state.transcript:
                if st.session_state.summary:
                    with st.expander("Summary", expanded=False):
                        st.write(st.session_state.summary)
                else: 
                    if st.button("Summarize"):
                        with st.status("Summarizing...") as summary_status:
                            response = requests.get(f"{API_URL}/llm/video_summary", params={"content": str(st.session_state.transcript), "filename": st.session_state.video_info["title"]})
                            if response.status_code == 200:
                                st.session_state.summary = response.text
                                st.write(st.session_state.summary)
                                summary_status.update(label="Summary completed", state="complete", expanded=True)
                            else:
                                st.error(f"Error: {response.status_code}: {response.text}")
                                summary_status.update(label="Summary failed", state="error")
                
                ## Chat with video
                with st.expander("Chat with video", expanded=False):
                    if not st.session_state.uploaded:
                        if st.button("Upload file"):
                            with st.status("Uploading transcript...") as upload_status:
                                file = io.StringIO(st.session_state.transcript)
                                file.name = st.session_state.video_info["title"] + ".txt"
                                response = requests.post(f"{API_URL}/rag/ingest_uploaded_file", files={"file": file}, params={"inmemory": True})
                                if response.status_code in [200, 201]:
                                    st.session_state.uploaded = True
                                    upload_status.update(label="Upload completed", state="complete", expanded=True)
                                    st.rerun()
                                else:
                                    st.error(f"Error: {response.status_code}: {response.text}")
                                    upload_status.update(label="Upload failed", state="error")
                    else:
                        if len(st.session_state.youtube_chat) == 0:
                            prompt = st.chat_input("Ask a question about your video...")
                            if prompt:
                                st.session_state.youtube_chat.append({"role": "user", "content": prompt})  
                                with st.status("Thinking...") as status:
                                    response = requests.post(f"{API_URL}/rag/query", json={"query": prompt, "inmemory": True})
                                    if response.status_code == 200:
                                        st.session_state.youtube_chat.append({"role": "assistant", "content": response.json()["response"]})
                                        status.update(label="Done", state="complete", expanded=True)
                                        st.rerun()
                                    else:
                                        st.error(f"Error: {response.status_code}: {response.text}")
                                        status.update(label="Error", state="error")
                            
                        else:
                            for message in st.session_state.youtube_chat:
                                with st.chat_message(message["role"]):
                                    st.markdown(message["content"])
                            prompt = st.chat_input("Ask a question about your video...")
                            if prompt:
                                st.session_state.youtube_chat.append({"role": "user", "content": prompt})  
                                with st.status("Thinking...") as status:
                                    response = requests.post(f"{API_URL}/rag/query", json={"query": prompt, "inmemory": True})
                                    if response.status_code == 200:
                                        st.session_state.youtube_chat.append({"role": "assistant", "content": response.json()["response"]})
                                        status.update(label="Done", state="complete", expanded=True)
                                        st.rerun()
                                    else:
                                        st.error(f"Error: {response.status_code}: {response.text}")
                                        status.update(label="Error", state="error")
                    if st.button("Clear chat history"):
                        st.session_state.youtube_chat = []
                        st.rerun()
                        
                
        else:
            st.error(f"Error: {response.status_code}: {response.text}")

    
with t2:
    st.header("Local Video")
    
with t3:
    st.header("Library")