import streamlit as st
import os

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Summa", layout="wide")
st.logo("./frontend/img/Logo_main.png", size="large")

st.image("./frontend/img/Logo_main.png")

st.markdown("""
Welcome to **Summa**, your personal file and knowledge manager.

Use the sidebar on the left to navigate between different modules:

- **📂 Local Files**: Manage your local documents, generate AI summaries, and organize with tags.
- **📝 HedgeDoc**: Connect to your HedgeDoc instance to manage and download notes.
- **🐙 GitHub Stats**: Check GitHub contribution statistics.

### Status
""")

# Optional: Check backend status
import requests
try:
    response = requests.get(f"{API_URL}/health") # Assuming /health or just root
    # If root / is 404 but server is up, or whatever. Let's just try listing files or tags to see if up
    # actually files endpoint is better check
    response = requests.get(f"{API_URL}/files")
    st.success("Backend is CONNECTED ✅")
except:
    st.warning("Backend is NOT CONNECTED ❌. Please ensure the FastAPI server is running.")

st.sidebar.info("Microservice PoC\nBackend: FastAPI\nFrontend: Streamlit")
