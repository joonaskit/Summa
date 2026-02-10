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

- **📂 Library**: Manage your local documents, generate AI summaries, organize with tags, and suggest tags using AI.
- **📝 HedgeDoc**: Connect to your HedgeDoc instance to view, fetch, and download notes to your library.
- **🔮 Nexus**: Chat with your documents using RAG (Retrieval Augmented Generation) - ingest files into a vector database and ask questions about them, or chat directly with individual files.

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
