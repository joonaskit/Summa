from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from .services import LocalFileService, HedgeDocService, GitHubService, LLMService, RagService
from .video_service import VideoService
from .database import DatabaseManager
from .logging_config import get_logger
from pydantic import BaseModel
from typing import List, Optional
import os
import time

from contextlib import asynccontextmanager

# Initialize logger for this module
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Summa API application")
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Database path: {DB_PATH}")
    logger.info(f"LLM base URL: {LLM_BASE_URL}")
    db_manager.init_db()
    logger.info("Database initialized successfully")
    yield
    # Shutdown
    logger.info("Shutting down Summa API application")
    db_manager.close()
    logger.info("Database connection closed")

app = FastAPI(title="Summa API", lifespan=lifespan)

# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and outgoing responses."""
    start_time = time.time()
    
    # Log incoming request
    logger.info(
        f"Incoming request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    # Process request
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration:.3f}s"
        )
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} "
            f"error={str(e)} duration={duration:.3f}s",
            exc_info=True
        )
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Services
# In a real app, config might come from env vars
DATA_DIR = os.getenv("DATA_DIR", "./data")
DB_PATH = os.path.join(DATA_DIR, "db", "metadata.duckdb")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://host.docker.internal:1234/v1")

# Initialize Database
db_manager = DatabaseManager(DB_PATH)
# db_manager.init_db() remove this top level call

local_service = LocalFileService(root_dir=DATA_DIR, db_manager=db_manager)
hedgedoc_service = HedgeDocService()
github_service = GitHubService()
llm_service = LLMService(base_url=LLM_BASE_URL, db_manager=db_manager, local_file_service=local_service)
RAG_SERVICE = RagService(base_url=LLM_BASE_URL)
RAG_SERVICE_IM = RagService(base_url=LLM_BASE_URL, inmemory=True)
video_service = VideoService()

class HedgeDocRequest(BaseModel):
    url: str
    cookie: Optional[str] = None
    
class SummaryRequest(BaseModel):
    path: str

class HedgeDocHistoryRequest(BaseModel):
    base_url: str
    cookie: str

class VideoInfoRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    logger.debug("Health check endpoint called")
    return {"message": "Summa API is running"}

@app.get("/files")
def get_local_files():
    """List all files found in the data directory."""
    logger.info("Listing local files")
    files = local_service.list_files()
    logger.debug(f"Found {len(files)} files")
    return files

@app.get("/files/content")
def get_file_content(path: str):
    """Get content of a specific file (if text/markdown)."""
    logger.info(f"Fetching content for file: {path}")
    # Security check: prevent directory traversal
    # This is a basic PoC check
    if ".." in path or not os.path.abspath(os.path.join(DATA_DIR, path)).startswith(os.path.abspath(DATA_DIR)):
         logger.warning(f"Access denied for path: {path} (directory traversal attempt)")
         raise HTTPException(status_code=403, detail="Access denied")
    try:
        return local_service.get_content(path)
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"File content fetch failed for {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import UploadFile, File

@app.post("/files/upload")
def upload_file(file: UploadFile = File(...)):
    """Upload a file to the data directory."""
    logger.info(f"Uploading file: {file.filename}")
    # We use file.file which is the SpooledThinkingFile/BytesIO
    result = local_service.save_upload(file.file, file.filename)
    if "error" in result:
        logger.error(f"File upload failed for {file.filename}: {result['error']}")
        raise HTTPException(status_code=500, detail=result["error"])
    logger.info(f"File uploaded successfully: {file.filename}")
    return result

@app.delete("/files/delete")
def delete_file_endpoint(path: str):
    """Delete a file."""
    logger.info(f"Deleting file: {path}")
    result = local_service.delete_file(path)
    if "error" in result:
        # Check if 404 or 500
        if result["error"] == "File not found":
             logger.warning(f"File not found for deletion: {path}")
             raise HTTPException(status_code=404, detail=result["error"])
        elif result["error"] == "Access denied":
             logger.warning(f"Access denied for file deletion: {path}")
             raise HTTPException(status_code=403, detail=result["error"])
        else:
             logger.error(f"File deletion failed for {path}: {result['error']}")
             raise HTTPException(status_code=500, detail=result["error"])
    logger.info(f"File deleted successfully: {path}")
    return result

@app.post("/hedgedoc")
def fetch_hedgedoc(request: HedgeDocRequest):
    """Fetch content from a HedgeDoc URL."""
    logger.info(f"Fetching HedgeDoc content from: {request.url}")
    content = hedgedoc_service.fetch_content(request.url, request.cookie)
    if content is None:
        logger.error(f"Failed to fetch HedgeDoc content from: {request.url}")
        raise HTTPException(status_code=404, detail="Could not fetch HedgeDoc content")
    logger.info(f"Successfully fetched HedgeDoc content from: {request.url}")
    return {"content": content}

@app.post("/hedgedoc/history")
def fetch_hedgedoc_history(request: HedgeDocHistoryRequest):
    """Fetch history (my notes) from HedgeDoc."""
    logger.info(f"Fetching HedgeDoc history from: {request.base_url}")
    history = hedgedoc_service.fetch_history(request.base_url, request.cookie)
    if isinstance(history, dict) and "error" in history:
        logger.error(f"Failed to fetch HedgeDoc history: {history['error']}")
        raise HTTPException(status_code=400, detail=history["error"])
    logger.info(f"Successfully fetched HedgeDoc history, {len(history)} items")
    return {"history": history}

class HedgeDocDownloadRequest(BaseModel):
    url: str
    cookie: Optional[str] = None
    filename: str

@app.post("/hedgedoc/download")
def download_hedgedoc(request: HedgeDocDownloadRequest):
    """Download content from HedgeDoc and save to data directory."""
    logger.info(f"Downloading HedgeDoc content from {request.url} to {request.filename}")
    content = hedgedoc_service.fetch_content(request.url, request.cookie)
    if content is None:
        logger.error(f"Failed to fetch HedgeDoc content for download from: {request.url}")
        raise HTTPException(status_code=404, detail="Could not fetch HedgeDoc content")
    
    result = local_service.save_content(request.filename, content)
    if "error" in result:
        logger.error(f"Failed to save HedgeDoc content to {request.filename}: {result['error']}")
        raise HTTPException(status_code=500, detail=result["error"])
    
    logger.info(f"Successfully downloaded HedgeDoc content to: {request.filename}")
    return result

@app.get("/github/{username}")
def get_github_stats(username: str):
    """Fetch recent contribution stats/events for a GitHub user."""
    logger.info(f"Fetching GitHub stats for user: {username}")
    data = github_service.get_user_events(username)
    if data is None:
         logger.error(f"Failed to fetch GitHub stats for user: {username}")
         raise HTTPException(status_code=404, detail="GitHub user not found or API error")
    logger.info(f"Successfully fetched GitHub stats for user: {username}")
    return data

from fastapi.responses import StreamingResponse

@app.post("/files/summary")
def generate_file_summary(request: SummaryRequest):
    """Generate a summary for a local file using the local LLM (Streamed)."""
    logger.info(f"Generating summary for file: {request.path}")
    return StreamingResponse(llm_service.process_file_stream(request.path), media_type="text/plain")

@app.get("/files/summary")
def get_file_summary(path: str):
    """Retrieve an existing summary for a file from the database."""
    logger.info(f"Retrieving summary for file: {path}")
    summary = db_manager.get_summary(path)
    if not summary:
        logger.warning(f"Summary not found for file: {path}")
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary

class TagCreate(BaseModel):
    name: str

class FileTagUpdate(BaseModel):
    path: str
    tags: List[str]

@app.get("/tags")
def get_tags():
    """Get all available tags."""
    logger.debug("Fetching all tags")
    tags = db_manager.get_all_tags()
    logger.debug(f"Found {len(tags)} tags")
    return tags

@app.post("/tags")
def create_tag(tag: TagCreate):
    """Create a new tag."""
    logger.info(f"Creating tag: {tag.name}")
    db_manager.add_tag(tag.name)
    logger.info(f"Tag created successfully: {tag.name}")
    return {"message": "Tag created"}

@app.delete("/tags/{name}")
def delete_tag(name: str):
    """Delete a tag."""
    logger.info(f"Deleting tag: {name}")
    db_manager.delete_tag(name)
    logger.info(f"Tag deleted successfully: {name}")
    return {"message": "Tag deleted"}

@app.post("/files/tags")
def update_file_tags(update: FileTagUpdate):
    """Update tags for a file."""
    logger.info(f"Updating tags for file: {update.path}, tags: {update.tags}")
    
    # Ensure all tags are registered in the global 'tags' table
    for tag in update.tags:
        db_manager.add_tag(tag)
    
    db_manager.update_file_tags(update.path, update.tags)
    logger.info(f"Tags updated successfully for file: {update.path}")
    return {"message": "Tags updated"}

@app.post("/files/suggest_tags")
def suggest_tags(request: SummaryRequest):
    """Generate tag suggestions for a file using LLM."""
    logger.info(f"Generating tag suggestions for file: {request.path}")
    # Reusing SummaryRequest since it just needs path
    result = llm_service.process_file_tags(request.path)
    if "error" in result:
        logger.error(f"Tag suggestion failed for {request.path}: {result['error']}")
        raise HTTPException(status_code=500, detail=result["error"])
    logger.info(f"Tag suggestions generated for file: {request.path}")
    return result

@app.get("/llm/models")
def get_llm_models():
    logger.debug("Fetching available LLM models")
    return llm_service.get_models()

@app.get("/llm/embedding_models")
def get_llm_embedding_models():
    logger.debug("Fetching available embedding models")
    return llm_service.get_embedding_models()

@app.get("/llm/summary")
async def get_summary(content:str, filename:str):
    logger.info(f"Generating summary for file: {filename}")
    return StreamingResponse(llm_service.generate_summary_stream(content=content), media_type="text/plain")

class QueryRequest(BaseModel):
    query: str
    inmemory: Optional[bool] = False

@app.post("/rag/query", status_code=status.HTTP_200_OK)
def rag_query(request: QueryRequest):
    logger.info(f"RAG query: {request.query[:100]}...")  # Log first 100 chars
    try:
        if request.inmemory:
            logger.info("RAG query (inmemory)")
            result = RAG_SERVICE_IM.query_with_context(request.query)
        else:
            logger.info("RAG query (db)")
            result = RAG_SERVICE.query_with_context(request.query)
        logger.info("RAG query completed successfully")
        return result
    except Exception as e:
        logger.error(f"RAG query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag/query_stream")
def rag_query_stream(request: QueryRequest):
    logger.info(f"RAG streaming query: {request.query[:100]}...")  # Log first 100 chars
    return RAG_SERVICE.query_with_context_stream(request.query)

class IngestRequest(BaseModel):
    paths: List[str]
    inmemory: Optional[bool] = False

@app.post("/rag/ingest", status_code=status.HTTP_201_CREATED)
def rag_ingest(request: IngestRequest):
    logger.info(f"Ingesting {len(request.paths)} files into RAG system")
    try:
        rag_service = RAG_SERVICE_IM if request.inmemory else RAG_SERVICE
        result = rag_service.ingest_files(request.paths)
        logger.info(f"Successfully ingested {len(request.paths)} files")
        return result
    except FileNotFoundError as e:
        logger.error(f"File not found during RAG ingestion: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Invalid value during RAG ingestion: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"RAG ingestion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag/ingest_uploaded_file", status_code=status.HTTP_201_CREATED)
async def rag_ingest_uploaded_file(file: UploadFile = File(...), inmemory: Optional[bool] = True):
    logger.info(f"Ingesting uploaded file into RAG system")
    try:
        rag_service = RAG_SERVICE_IM if inmemory else RAG_SERVICE
        result = rag_service.ingest_uploaded_file(file)
        logger.info(f"Successfully ingested uploaded file")
        return result
    except FileNotFoundError as e:
        logger.error(f"File not found during RAG ingestion: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Invalid value during RAG ingestion: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"RAG ingestion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video/info")
def get_video_info(request: VideoInfoRequest):
    """Fetch metadata for a YouTube video."""
    logger.info(f"Fetching video info for URL: {request.url}")
    try:
        metadata = video_service.get_video_info(request.url)
        logger.info(f"Successfully fetched video info for: {request.url}")
        return metadata
    except ValueError as e:
        logger.warning(f"Invalid video URL: {request.url} - {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch video info for {request.url}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
