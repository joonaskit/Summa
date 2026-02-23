# Database Schemas

This document describes all database schemas used in the application.

---

## DuckDB (Relational Database)

**File:** `data/hmo_data.db`  
**Manager:** [`database.py`](file:///home/jkikke/code/GIT/webdev/hmo_app/backend/database.py) — `DatabaseManager` class

### `files_metadata`

Stores metadata for all managed local files.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `path` | `VARCHAR` | `PRIMARY KEY` | Relative file path (from data root) |
| `filename` | `VARCHAR` | | Original filename |
| `last_modified` | `TIMESTAMP` | | File's last modification time |
| `size` | `BIGINT` | | File size in bytes |
| `file_type` | `VARCHAR` | | File extension (e.g. `md`, `pdf`) |
| `hash` | `VARCHAR` | | SHA-256 hash of file content |
| `tags` | `VARCHAR[]` | | Array of user-assigned tags |
| `vectorized_hash` | `VARCHAR` | | Hash of content at RAG ingestion time; `NULL` if not yet vectorized |

---

### `tags`

Global registry of available tags.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `name` | `VARCHAR` | `PRIMARY KEY` | Unique tag name |

---

### `file_summaries`

Stores LLM-generated summaries and associated tags for files.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `path` | `VARCHAR` | `PRIMARY KEY` | File path (matches `files_metadata.path`) |
| `summary_text` | `TEXT` | | LLM-generated summary |
| `tags` | `VARCHAR[]` | | LLM-suggested tags |
| `generated_at` | `TIMESTAMP` | | When the summary was generated |
| `model_used` | `VARCHAR` | | Identifier of the model used |

---

### `video_summaries`

Stores LLM-generated summaries for videos (both YouTube and local).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `VARCHAR` | `PRIMARY KEY` | Video ID (matches `videos.id` or `local_videos.id`) |
| `summary_text` | `TEXT` | | LLM-generated summary of the transcript |
| `tags` | `VARCHAR[]` | | Tags associated with the summary |
| `generated_at` | `TIMESTAMP` | | When the summary was generated |
| `model_used` | `VARCHAR` | | Identifier of the model used |

---

### `videos`

Stores YouTube video metadata and transcripts.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `VARCHAR` | `PRIMARY KEY` | YouTube video ID (11-char) |
| `youtube_url` | `VARCHAR` | `NOT NULL` | Full YouTube URL |
| `title` | `VARCHAR` | | Video title |
| `transcript_text` | `TEXT` | | Full transcript text |
| `created_at` | `TIMESTAMP` | | When the record was created |

---

### `local_videos`

Stores metadata for locally uploaded video files.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `VARCHAR` | `PRIMARY KEY` | UUID identifier |
| `filename` | `VARCHAR` | `NOT NULL` | Original filename |
| `stored_path` | `VARCHAR` | `NOT NULL` | Path where video is stored on disk |
| `file_size` | `BIGINT` | `NOT NULL` | File size in bytes |
| `file_hash` | `VARCHAR` | `NOT NULL`, `UNIQUE` | SHA-256 hash (deduplication key) |
| `mime_type` | `VARCHAR` | | Video MIME type (e.g. `video/mp4`) |
| `duration` | `FLOAT` | | Duration in seconds |
| `width` | `INTEGER` | | Video width in pixels |
| `height` | `INTEGER` | | Video height in pixels |
| `transcript_text` | `TEXT` | | Transcribed text (Whisper) |
| `created_at` | `TIMESTAMP` | `NOT NULL` | Record creation time |
| `transcribed_at` | `TIMESTAMP` | | When transcript was generated |

---

## ChromaDB (Vector Database)

**Directory:** `data/chroma/` (configurable via `CHROMA_DIR` env var, default `/app/data/chroma`)  
**Backend:** SQLite (`chroma.sqlite3`)  
**Manager:** [`services.py`](file:///home/jkikke/code/GIT/webdev/hmo_app/backend/services.py) — `RagService` class

### Collection: `summa_collection`

Used for RAG (Retrieval-Augmented Generation) similarity search over ingested documents.

| Field | Description |
|---|---|
| **Embedding model** | Configurable; default `text-embedding-granite-embedding-278m-multilingual` via LM Studio |
| **Embedding source** | OpenAI-compatible API at `base_url` (default `http://host.docker.internal:1234/v1`) |
| **Chunking strategy** | `RecursiveCharacterTextSplitter` — 1 000 chars per chunk, 200 char overlap |

#### Document schema (per chunk)

| Field | Type | Description |
|---|---|---|
| `page_content` | `string` | Text chunk content |
| `metadata.source` | `string` | Source file path |
| `metadata.start_index` | `int` | Character offset of chunk within original document |

> [!NOTE]
> An in-memory vector store (`InMemoryVectorStore`) is available as an alternative when `inmemory=True` is passed to `RagService`. This uses the same embedding model but does not persist data to disk.
