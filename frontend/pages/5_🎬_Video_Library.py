import streamlit as st
import requests
from utils import API_URL

if "videos" not in st.session_state:
    st.session_state.videos = []

if "youtube_url" not in st.session_state:
    st.session_state.youtube_url = None

@st.cache_data
def get_video_info(url):
    response = requests.post(API_URL + "/video/info", json={"url": url})
    if response.status_code in [200, 201]:
        data = response.json()
        return data
    else:
        return None

@st.dialog("Confirm Deletion")
def confirm_delete(youtube_url, video_title):
    st.write(f"Are you sure you want to delete **{video_title}**?")
    st.warning("This action cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel"):
            st.rerun()
    with col2:
        if st.button("Delete", type="primary"):
            try:
                # Use query param for consistency with backend
                resp = requests.delete(f"{API_URL}/video/delete", json={"url": youtube_url})
                if resp.status_code == 200:
                    st.success("Deleted successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to delete: {resp.text}")
            except Exception as e:
                st.error(f"Error: {e}")

st.title("Video Library")

with st.expander("Add Video", expanded=False):
    st.session_state.youtube_url = st.text_input("YouTube URL", value=st.session_state.youtube_url)
    if st.session_state.youtube_url:
        reponse = requests.post(API_URL + "/video/info", json={"url": st.session_state.youtube_url})
        if reponse.status_code in [200, 201]:
            data = reponse.json()
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
            st.error("Please enter a YouTube URL")
        if st.button("Clear"):
            st.session_state.youtube_url = None
            st.rerun()
    

try:
    response = requests.get(API_URL + "/video/list")
    if response.status_code == 200:
        st.session_state.videos = response.json()["videos"]
    else:
        st.error("Failed to fetch videos")
except Exception as e:
    st.error(f"Error: {e}")


for video in st.session_state.videos:
    with st.expander(video["title"], expanded=False):
        data = get_video_info(video["youtube_url"])
        if data:
            st.caption(f"Author: {data['author']}")
        st.video(video["youtube_url"])
        with st.expander("Transcript", expanded=False):
            st.write(video["transcript_text"])
        st.caption(f"Cached: {video['created_at']}")
        if st.button("Delete", key=video["id"] + "delete"):
            confirm_delete(video["youtube_url"], video["title"])