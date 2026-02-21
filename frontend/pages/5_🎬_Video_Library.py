import streamlit as st
import requests
from utils import API_URL

if "videos" not in st.session_state:
    st.session_state.videos = []

if "local_videos" not in st.session_state:
    st.session_state.local_videos = []

if "youtube_url" not in st.session_state:
    st.session_state.youtube_url = None

if "video_filter" not in st.session_state:
    st.session_state.video_filter = "All"

@st.cache_data
def get_video_info(url):
    response = requests.post(API_URL + "/video/info", json={"url": url})
    if response.status_code in [200, 201]:
        data = response.json()
        return data
    else:
        return None

@st.dialog("Confirm Deletion")
def confirm_delete_youtube(youtube_url, video_title):
    st.write(f"Are you sure you want to delete **{video_title}**?")
    st.warning("This action cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel"):
            st.rerun()
    with col2:
        if st.button("Delete", type="primary"):
            try:
                resp = requests.delete(f"{API_URL}/video/delete", json={"url": youtube_url})
                if resp.status_code == 200:
                    st.success("Deleted successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to delete: {resp.text}")
            except Exception as e:
                st.error(f"Error: {e}")

@st.dialog("Confirm Deletion")
def confirm_delete_local(video_id, video_title):
    st.write(f"Are you sure you want to delete **{video_title}**?")
    st.warning("This action cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel"):
            st.rerun()
    with col2:
        if st.button("Delete", type="primary"):
            try:
                resp = requests.delete(f"{API_URL}/video/local/delete/{video_id}")
                if resp.status_code == 200:
                    st.success("Deleted successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to delete: {resp.text}")
            except Exception as e:
                st.error(f"Error: {e}")

st.title("Video Library")

# Filter options
col1, col2 = st.columns([3, 1])
with col1:
    st.session_state.video_filter = st.radio(
        "Filter by type:",
        ["All", "YouTube", "Local"],
        horizontal=True
    )

with st.expander("Add YouTube Video", expanded=False):
    st.session_state.youtube_url = st.text_input("YouTube URL", value=st.session_state.youtube_url)
    if st.session_state.youtube_url:
        response = requests.post(API_URL + "/video/info", json={"url": st.session_state.youtube_url})
        if response.status_code in [200, 201]:
            data = response.json()
            st.subheader(data["title"])
            st.caption(data["author"])
            st.video(st.session_state.youtube_url)
            if st.button("Transcribe and cache"):
                with st.status("Caching....") as status:    
                    response = requests.post(API_URL + "/video/transcribe", json={"url": st.session_state.youtube_url})
                    if response.status_code == 200:
                        status.update(label="Video added successfully!", state="complete")
                        st.rerun()
                    else:
                        status.update(label=f"Failed to add video: {response.text}", state="error")
        else:
            st.error("Invalid YouTube URL")
        if st.button("Clear"):
            st.session_state.youtube_url = None
            st.rerun()

# Fetch videos
try:
    # Fetch YouTube videos
    if st.session_state.video_filter in ["All", "YouTube"]:
        response = requests.get(API_URL + "/video/list")
        if response.status_code == 200:
            st.session_state.videos = response.json()["videos"]
        else:
            st.error("Failed to fetch YouTube videos")
    
    # Fetch local videos
    if st.session_state.video_filter in ["All", "Local"]:
        response = requests.get(API_URL + "/video/local/list")
        if response.status_code == 200:
            st.session_state.local_videos = response.json()["videos"]
        else:
            st.error("Failed to fetch local videos")
except Exception as e:
    st.error(f"Error: {e}")

# Display statistics
total_youtube = len(st.session_state.videos) if st.session_state.video_filter in ["All", "YouTube"] else 0
total_local = len(st.session_state.local_videos) if st.session_state.video_filter in ["All", "Local"] else 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Videos", total_youtube + total_local)
with col2:
    if st.session_state.video_filter in ["All", "YouTube"]:
        st.metric("YouTube Videos", total_youtube)
with col3:
    if st.session_state.video_filter in ["All", "Local"]:
        st.metric("Local Videos", total_local)

st.divider()

# Display YouTube videos
if st.session_state.video_filter in ["All", "YouTube"] and st.session_state.videos:
    if st.session_state.video_filter == "All":
        st.subheader("YouTube Videos")
    
    for video in st.session_state.videos:
        with st.expander(f"▶️ {video['title']}", expanded=False):
            data = get_video_info(video["youtube_url"])
            if data:
                st.caption(f"Author: {data['author']}")
            st.video(video["youtube_url"])
            with st.expander("Transcript", expanded=False):
                st.write(video["transcript_text"])
            st.caption(f"Cached: {video['created_at']}")
            if st.button("Delete", key=video["id"] + "_delete"):
                confirm_delete_youtube(video["youtube_url"], video["title"])

# Display local videos
if st.session_state.video_filter in ["All", "Local"] and st.session_state.local_videos:
    if st.session_state.video_filter == "All":
        st.subheader("Local Videos")
    
    for video in st.session_state.local_videos:
        with st.expander(f"🎬 {video['filename']}", expanded=False):
            # Display metadata
            col1, col2, col3 = st.columns(3)
            with col1:
                file_size_mb = video.get("file_size", 0) / (1024 * 1024)
                st.caption(f"Size: {file_size_mb:.2f} MB")
            with col2:
                duration = video.get("duration")
                if duration:
                    st.caption(f"Duration: {int(duration)}s")
            with col3:
                resolution = f"{video.get('width')}x{video.get('height')}" if video.get('width') else "N/A"
                st.caption(f"Resolution: {resolution}")
            
            # Video player - fetch video data and display
            try:
                video_url = f"{API_URL}/video/local/stream/{video['id']}"
                response = requests.get(video_url, stream=True)
                if response.status_code == 200:
                    # Get the video bytes
                    video_bytes = response.content
                    st.video(video_bytes)
                else:
                    st.error(f"Failed to load video: {response.status_code}")
            except Exception as e:
                st.error(f"Error loading video: {str(e)}")
            
            # Transcript
            if video.get("transcript_text"):
                with st.expander("Transcript", expanded=False):
                    st.write(video["transcript_text"])
                if st.button("Summarize", key=video["id"] + "_summarize"):
                    with st.status("Summarizing....") as status:
                        response = requests.get(API_URL + "/llm/video_summary", params={"content": video["transcript_text"], "filename": video["filename"]})
                        if response.status_code == 200:
                            status.update(label="Video summarized successfully!", state="complete")
                            st.write(response.text)
                        else:
                            status.update(label=f"Failed to summarize video: {response.text}", state="error")
            else:
                st.caption("Not transcribed")
                if st.button("Transcribe", key=video["id"] + "_transcribe"):
                    with st.status("Transcribing....") as status:
                        response = requests.post(API_URL + "/video/local/transcribe/" + video["id"])
                        if response.status_code == 200:
                            status.update(label="Video transcribed successfully!", state="complete")
                            st.rerun()
                        else:
                            status.update(label=f"Failed to transcribe video: {response.text}", state="error")
            
            st.caption(f"Uploaded: {video['created_at']}")
            
            # Delete button
            if st.button("Delete", key=video["id"] + "_delete"):
                confirm_delete_local(video["id"], video["filename"])

# Show message if no videos
if (st.session_state.video_filter == "All" and 
    not st.session_state.videos and not st.session_state.local_videos):
    st.info("No videos in library. Upload a local video or add a YouTube video to get started!")
elif (st.session_state.video_filter == "YouTube" and not st.session_state.videos):
    st.info("No YouTube videos in library.")
elif (st.session_state.video_filter == "Local" and not st.session_state.local_videos):
    st.info("No local videos in library.")