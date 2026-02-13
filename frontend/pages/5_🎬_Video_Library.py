import streamlit as st
import requests
from utils import API_URL


video_url = st.text_input("Video URL", key="video_url")
if st.button("Fetch Video Info"):
    response = requests.post(f"{API_URL}/video/info", json={"url": video_url})
    if response.status_code == 200:
        video_info = response.json()
        st.write(video_info)
    else:
        st.error("Failed to fetch video info")
