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
    
    # Initialize session state for local video
    if "local_video_info" not in st.session_state:
        st.session_state.local_video_info = None
    if "local_transcript" not in st.session_state:
        st.session_state.local_transcript = None
    if "local_summary" not in st.session_state:
        st.session_state.local_summary = None
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload a video file",
        type=["mp4", "avi", "mkv", "mov", "webm", "mpeg", "mpg"],
        help="Supported formats: MP4, AVI, MKV, MOV, WEBM, MPEG"
    )
    
    if uploaded_file is not None:
        # Check if this is a new file
        if (st.session_state.local_video_info is None or 
            st.session_state.local_video_info.get("filename") != uploaded_file.name):
            
            with st.status("Uploading video...", expanded=True) as status:
                try:
                    # Upload the file
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    response = requests.post(f"{API_URL}/video/local/upload", files=files)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if result.get("duplicate"):
                            st.warning(result["message"])
                            st.session_state.local_video_info = result["existing_video"]
                            status.update(label="Duplicate video detected", state="complete")
                        else:
                            st.session_state.local_video_info = result
                            st.session_state.local_transcript = None
                            st.session_state.local_summary = None
                            status.update(label="Upload complete!", state="complete")
                    else:
                        st.error(f"Upload failed: {response.text}")
                        status.update(label="Upload failed", state="error")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    status.update(label="Upload failed", state="error")
    
    # Display video if uploaded
    if st.session_state.local_video_info:
        video_info = st.session_state.local_video_info
        video_id = video_info.get("id")
        
        st.subheader(video_info.get("filename", "Unknown"))
        
        # Display video metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            file_size_mb = video_info.get("file_size", 0) / (1024 * 1024)
            st.metric("File Size", f"{file_size_mb:.2f} MB")
        with col2:
            duration = video_info.get("duration")
            if duration:
                st.metric("Duration", f"{int(duration)}s")
        with col3:
            resolution = f"{video_info.get('width')}x{video_info.get('height')}" if video_info.get('width') else "N/A"
            st.metric("Resolution", resolution)
        
        # Video player - fetch video data and display
        try:
            video_url = f"{API_URL}/video/local/stream/{video_id}"
            response = requests.get(video_url, stream=True)
            if response.status_code == 200:
                video_bytes = response.content
                st.video(video_bytes)
            else:
                st.error(f"Failed to load video: {response.status_code}")
        except Exception as e:
            st.error(f"Error loading video: {str(e)}")
        
        # Transcription section
        if st.session_state.local_transcript:
            with st.expander("Transcript", expanded=False):
                st.write(st.session_state.local_transcript)
        else:
            # Check if transcript exists in database
            transcript_text = video_info.get("transcript_text")
            if transcript_text:
                st.session_state.local_transcript = transcript_text
                with st.expander("Transcript", expanded=False):
                    st.write(transcript_text)
            else:
                st.caption("Video not yet transcribed")
                if st.button("Transcribe video", key="transcribe_local"):
                    with st.status("Transcribing...", expanded=True) as status:
                        try:
                            response = requests.post(f"{API_URL}/video/local/transcribe/{video_id}")
                            if response.status_code == 200:
                                result = response.json()
                                st.session_state.local_transcript = result["transcript"]
                                st.write(st.session_state.local_transcript)
                                status.update(label="Transcription complete!", state="complete")
                            else:
                                st.error(f"Transcription failed: {response.text}")
                                status.update(label="Transcription failed", state="error")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            status.update(label="Transcription failed", state="error")
        
        # Summary section
        if st.session_state.local_transcript:
            if st.session_state.local_summary:
                with st.expander("Summary", expanded=False):
                    st.write(st.session_state.local_summary)
            else:
                if st.button("Generate Summary", key="summarize_local"):
                    with st.status("Generating summary...", expanded=True) as status:
                        try:
                            response = requests.get(
                                f"{API_URL}/llm/video_summary",
                                params={
                                    "content": st.session_state.local_transcript,
                                    "filename": video_info.get("filename", "video")
                                }
                            )
                            if response.status_code == 200:
                                st.session_state.local_summary = response.text
                                st.write(st.session_state.local_summary)
                                status.update(label="Summary complete!", state="complete")
                            else:
                                st.error(f"Summary failed: {response.text}")
                                status.update(label="Summary failed", state="error")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            status.update(label="Summary failed", state="error")
        
        # Delete button
        if st.button("Delete video", key="delete_local", type="secondary"):
            if st.confirm("Are you sure you want to delete this video?"):
                try:
                    response = requests.delete(f"{API_URL}/video/local/delete/{video_id}")
                    if response.status_code == 200:
                        st.success("Video deleted successfully")
                        st.session_state.local_video_info = None
                        st.session_state.local_transcript = None
                        st.session_state.local_summary = None
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
with t3:
    st.header("Library")