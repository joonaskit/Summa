import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Settings – Summa", page_icon="⚙️")
st.title("⚙️ Settings")
st.caption("Edit and save backend configuration. Changes are written to `settings.json`.")

st.info(
    "**Note:** Settings that affect services initialised at startup (LLM model, embedding model, "
    "reranker, Whisper) require a **backend restart** to take full effect. "
    "Settings like log level take effect immediately.",
    icon="ℹ️",
)

# ---------------------------------------------------------------------------
# Load settings from backend
# ---------------------------------------------------------------------------
@st.cache_data(ttl=5)
def fetch_settings():
    resp = requests.get(f"{API_URL}/settings", timeout=5)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=30)
def fetch_all_models():
    try:
        resp = requests.get(f"{API_URL}/llm/models", timeout=5)
        resp.raise_for_status()
        return [m["id"] for m in resp.json()]
    except Exception:
        return []

@st.cache_data(ttl=30)
def fetch_embedding_models():
    try:
        resp = requests.get(f"{API_URL}/llm/embedding_models", timeout=5)
        resp.raise_for_status()
        return [m["id"] for m in resp.json()]
    except Exception:
        return []

try:
    settings = fetch_settings()
except Exception as e:
    st.error(f"Could not load settings from backend: {e}")
    st.stop()

# ---------------------------------------------------------------------------
# Build tabs
# ---------------------------------------------------------------------------
tab_llm, tab_api, tab_locations, tab_rerank, tab_rag, tab_whisper, tab_logging = st.tabs(
    ["🤖 LLM", "🔗 API", "📁 Locations", "🔀 Rerank", "📚 RAG", "🎙️ Whisper", "📋 Logging"]
)

with tab_llm:
    st.subheader("LLM Configuration")
    llm_url = st.text_input("LLM URL", value=settings["llm"]["LLM_URL"],
                             help="OpenAI-compatible LLM endpoint (e.g. LM Studio)")

    all_models = fetch_all_models()
    current_llm_model = settings["llm"]["LLM_MODEL"]
    if all_models:
        # Ensure current value appears even if not in the list
        options = all_models if current_llm_model in all_models else [current_llm_model] + all_models
        llm_model = st.selectbox("LLM Model", options=options,
                                  index=options.index(current_llm_model),
                                  help="Model name passed to the LLM API")
    else:
        st.warning("⚠️ Could not reach LLM server — enter model name manually.")
        llm_model = st.text_input("LLM Model", value=current_llm_model,
                                   help="Model name passed to the LLM API")

    embed_models = fetch_embedding_models()
    current_embed_model = settings["llm"]["EMBED_MODEL"]
    if embed_models:
        options = embed_models if current_embed_model in embed_models else [current_embed_model] + embed_models
        embed_model = st.selectbox("Embedding Model", options=options,
                                    index=options.index(current_embed_model),
                                    help="Embedding model name")
    else:
        st.warning("⚠️ Could not reach LLM server — enter embedding model name manually.")
        embed_model = st.text_input("Embedding Model", value=current_embed_model,
                                     help="Embedding model name")

    llm_temperature = st.slider("Temperature", min_value=0.0, max_value=2.0,
                                 value=float(settings["llm"]["LLM_TEMPERATURE"]),
                                 step=0.05, help="LLM sampling temperature")

with tab_api:
    st.subheader("API Configuration")
    api_url = st.text_input("API URL", value=settings["api"]["API_URL"],
                             help="Internal backend URL used for intra-service calls")

with tab_locations:
    st.subheader("Storage Locations")
    data_dir = st.text_input("Data Directory", value=settings["locations"]["DATA_DIR"],
                              help="Root directory for persistent data")
    chroma_dir = st.text_input("ChromaDB Directory", value=settings["locations"]["CHROMA_DIR"],
                                help="Directory for ChromaDB vector store")

with tab_rerank:
    st.subheader("Cross-Encoder Reranking")
    enable_rerank = st.toggle("Enable Reranking", value=settings["rerank"]["ENABLE_RERANK"].lower() == "true",
                               help="Enable HuggingFace cross-encoder reranking for RAG")
    rerank_model = st.text_input("Rerank Model", value=settings["rerank"]["RERANK_MODEL"],
                                  help="HuggingFace cross-encoder model name",
                                  disabled=not enable_rerank)
    rerank_fetch_k = st.number_input("Fetch K (candidate pool)", min_value=1, max_value=200,
                                      value=int(settings["rerank"]["RERANK_FETCH_K"]),
                                      help="Number of candidates retrieved before reranking",
                                      disabled=not enable_rerank)
    rerank_top_n = st.number_input("Top N (results after rerank)", min_value=1, max_value=50,
                                    value=int(settings["rerank"]["RERANK_TOP_N"]),
                                    help="Number of results returned after reranking",
                                    disabled=not enable_rerank)

with tab_rag:
    st.subheader("RAG / Chunking")
    chunk_size = st.number_input("Chunk Size (characters)", min_value=100, max_value=10000,
                                  value=int(settings["rag"]["CHUNK_SIZE"]),
                                  step=100, help="Number of characters per document chunk")
    chunk_overlap = st.number_input("Chunk Overlap (characters)", min_value=0, max_value=2000,
                                     value=int(settings["rag"]["CHUNK_OVERLAP"]),
                                     step=50, help="Overlap between adjacent chunks")

with tab_whisper:
    st.subheader("Whisper Transcription")
    whisper_model = st.selectbox(
        "Whisper Model",
        options=["tiny", "base", "small", "medium", "large"],
        index=["tiny", "base", "small", "medium", "large"].index(
            settings["whisper"]["WHISPER_MODEL"]
        ),
        help="Larger models are more accurate but slower and use more memory"
    )

with tab_logging:
    st.subheader("Logging")
    log_level = st.selectbox(
        "Log Level",
        options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        index=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].index(
            settings["logging"]["LOG_LEVEL"].upper()
        ),
    )
    log_format = st.selectbox(
        "Log Format",
        options=["console", "json"],
        index=["console", "json"].index(settings["logging"]["LOG_FORMAT"].lower()),
        help="`console` = human-readable with colours, `json` = structured for log aggregators"
    )
    log_file_raw = settings["logging"]["LOG_FILE"]
    log_file = st.text_input(
        "Log File Path (optional)",
        value=log_file_raw if log_file_raw else "",
        help="Leave blank to log to stdout only"
    )

# ---------------------------------------------------------------------------
# Save button
# ---------------------------------------------------------------------------
st.divider()
if st.button("💾 Save Settings", type="primary", use_container_width=True):
    new_settings = {
        "llm": {
            "LLM_URL": llm_url,
            "LLM_MODEL": llm_model,
            "EMBED_MODEL": embed_model,
            "LLM_TEMPERATURE": llm_temperature,
        },
        "api": {
            "API_URL": api_url,
        },
        "locations": {
            "DATA_DIR": data_dir,
            "CHROMA_DIR": chroma_dir,
        },
        "rerank": {
            "RERANK_MODEL": rerank_model,
            "RERANK_FETCH_K": rerank_fetch_k,
            "RERANK_TOP_N": rerank_top_n,
            "ENABLE_RERANK": "true" if enable_rerank else "false",
        },
        "rag": {
            "CHUNK_SIZE": chunk_size,
            "CHUNK_OVERLAP": chunk_overlap,
        },
        "whisper": {
            "WHISPER_MODEL": whisper_model,
        },
        "logging": {
            "LOG_LEVEL": log_level,
            "LOG_FORMAT": log_format,
            "LOG_FILE": log_file if log_file.strip() else None,
        },
    }
    try:
        resp = requests.put(f"{API_URL}/settings", json=new_settings, timeout=10)
        resp.raise_for_status()
        st.success("✅ Settings saved successfully!")
        st.caption(resp.json().get("message", ""))
        fetch_settings.clear()
    except requests.HTTPError as e:
        st.error(f"Failed to save settings: {e.response.text}")
    except Exception as e:
        st.error(f"Failed to save settings: {e}")
