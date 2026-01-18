# 📚 Summa

A lightweight document gatherer and summarizer. **Summa** helps you consolidate information from local files, HedgeDoc notes, and GitHub activity, providing AI-powered summaries for your documents.

## ✨ Features

- **📂 Local File Vault**: Manage and view `.md`, `.pdf`, `.docx`, and `.pptx` files.
- **📝 HedgeDoc Integration**: Fetch and save notes directly from any HedgeDoc instance.
- **🐙 GitHub Stats**: Track recent activity and contributions for any GitHub user.
- **🤖 Local AI Summaries**: Generate streamed summaries for your documents using a local LLM (OpenAI-compatible API like LM Studio).
- **🗄️ Metadata Storage**: DuckDB-powered persistence for file metadata and generated summaries.

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
