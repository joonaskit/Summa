# 📚 Summa

A document knowledge base and AI assistant. **Summa** helps you consolidate information from local files, HedgeDoc notes, YouTube videos, and local video files — with AI-powered summaries, RAG-based chat, and cross-encoder reranking for high-quality retrieval.

## ✨ Features

### 📂 Library
- Manage and view local `.md`, `.txt`, `.pdf`, `.docx`, and `.pptx` files
- Upload files individually or in bulk
- Generate AI-powered summaries for documents using a local LLM
- Organize files with custom tags and AI-powered tag suggestions
- Filter files by tags, document type, and summary status
- View file content directly in the browser
- Ingest files into the vector database for RAG chat

### 📝 HedgeDoc Integration
- Connect to any HedgeDoc instance using session cookies
- View your note history and preview note content
- Download individual notes or bulk download multiple notes to your library
- Quick fetch by URL for public or private notes

### 🔮 Nexus (RAG Chat)
- **Chat with a database**: Ask questions across all ingested documents
- **Chat with a file**: Upload a file and have a conversation about its content without persisting to the database
- **Multi-query search**: The LLM generates multiple sub-queries to improve recall across the vector database
- **Cross-encoder reranking**: A HuggingFace cross-encoder rescores the candidate pool against the original query before sending context to the LLM, significantly improving answer quality
- Cross-encoder status indicator in the settings panel — warns if reranking is disabled
- **Source previews**: Clickable source references after each answer, showing file content/summary or video information
- File summarization on demand
- Powered by local LLM with OpenAI-compatible API (e.g., LM Studio)
- Conversation history management

### 📽️ Video Analyst
- Analyse YouTube videos: fetch metadata, transcribe, summarize, and chat about content
- Analyse local video files: upload, transcribe, and summarize (MP4, AVI, MKV, MOV, WEBM, MPEG)
- Transcriptions are cached in the database for instant re-access
- Chat with any video transcript using RAG (in-memory, without polluting the main database)

### 🎬 Video Library
- Browse all cached YouTube and local videos in one view
- Filter by type (YouTube / Local)
- Ingest video transcripts into the vector database for inclusion in Nexus RAG chat (shown as ✅ In Vector DB)
- Generate and manage AI summaries per video
- Delete videos and their associated data

### 🗄️ Infrastructure
- **DuckDB**: Persistent storage for file metadata, tags, summaries, and video records
- **ChromaDB**: Vector database for document embeddings
- **LangChain + LangChain-Community**: RAG pipeline, multi-query generation, and cross-encoder reranking
- **faster-whisper**: Local speech-to-text transcription
- **Streaming responses**: Real-time AI responses for better UX

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- (Optional) [LM Studio](https://lmstudio.ai/) or any OpenAI-compatible local LLM server

### Running the App

1. Clone the repository:
    ```bash
    git clone git@github.com:joonaskit/Summa.git
    cd Summa
    ```

2. Start the services:
    ```bash
    docker compose up --build
    ```

3. Access the applications:
    - **Frontend (Streamlit)**: [http://localhost:8501](http://localhost:8501)
    - **Backend (FastAPI / API docs)**: [http://localhost:8000/docs](http://localhost:8000/docs)

## ⚙️ Configuration

All configuration is handled via environment variables in `docker-compose.yml`.

| Variable | Default | Description |
|---|---|---|
| `LLM_URL` | `http://host.docker.internal:1234/v1` | OpenAI-compatible LLM endpoint |
| `DATA_DIR` | `/app/data` | Persistent data directory |
| `CHROMA_DIR` | `/app/data/chroma` | ChromaDB storage path |
| `WHISPER_MODEL` | `base` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large`) |
| `ENABLE_RERANK` | `true` | Enable cross-encoder reranking for RAG |
| `RERANK_MODEL` | `BAAI/bge-reranker-base` | HuggingFace cross-encoder model name |
| `RERANK_FETCH_K` | `20` | Number of candidates to fetch before reranking |
| `LOG_LEVEL` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `LOG_FORMAT` | `console` | Log format (`console` or `json`) |
| `LOG_FILE` | _(unset)_ | Optional path to write logs to a file |

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Database | DuckDB |
| Vector DB | ChromaDB |
| LLM Integration | LangChain, LangChain-OpenAI, LangChain-Community |
| Reranking | `sentence-transformers` + `langchain-classic` CrossEncoderReranker |
| Transcription | faster-whisper |
| Video Fetching | yt-dlp |
