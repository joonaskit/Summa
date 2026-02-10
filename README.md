# 📚 Summa

A lightweight document gatherer and summarizer. **Summa** helps you consolidate information from local files, HedgeDoc notes, and GitHub activity, providing AI-powered summaries for your documents.

## ✨ Features

### 📂 Library
- Manage and view local `.md`, `.txt`, `.pdf`, `.docx`, and `.pptx` files
- Upload files individually or in bulk
- Generate AI-powered summaries for documents using a local LLM
- Organize files with custom tags
- AI-powered tag suggestions based on file content
- Filter files by tags, document type, and summary status
- View file content directly in the browser

### 📝 HedgeDoc Integration
- Connect to any HedgeDoc instance using session cookies
- View your note history
- Fetch and preview note content
- Download individual notes or bulk download multiple notes to your library
- Quick fetch by URL for public or private notes

### 🔮 Nexus (RAG Chat)
- **Chat with a database**: Ingest multiple documents into a vector database and ask questions across all of them
- **Chat with a file**: Upload a file and have a conversation about its content without persisting to the database
- File summarization on demand
- Powered by local LLM with OpenAI-compatible API (e.g., LM Studio)
- Conversation history management

### 🗄️ Infrastructure
- **DuckDB**: Persistent storage for file metadata, tags, and generated summaries
- **ChromaDB**: Vector database for storing document embeddings used in RAG
- **LangChain**: RAG implementation with vector embeddings
- **Streaming responses**: Real-time AI responses for better UX

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- (Optional) [LM Studio](https://lmstudio.ai/) or similar for local LLM features.

### Running the App

1.  Clone the repository:
    ```bash
    git clone git@github.com:joonaskit/Summa.git
    cd Summa
    ```

2.  Start the services:
    ```bash
    docker compose up --build
    ```

3.  Access the applications:
    - **Frontend (Streamlit)**: [http://localhost:8501](http://localhost:8501)
    - **Backend (FastAPI)**: [http://localhost:8000](http://localhost:8000)

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Database**: DuckDB
- **LLM Integration**: LangChain + LangChain-OpenAI


## Logs

### Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export LOG_LEVEL=INFO
### Set log format (console or json)
export LOG_FORMAT=console
### Optional: Set log file path
export LOG_FILE=/var/log/summa/backend.log
