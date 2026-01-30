from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .services import LocalFileService, HedgeDocService, GitHubService, LLMService
from .database import DatabaseManager
from pydantic import BaseModel
from typing import List, Optional
import os

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db_manager.init_db()
    yield
    # Shutdown
    db_manager.close()

app = FastAPI(title="Summa API", lifespan=lifespan)

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

class HedgeDocRequest(BaseModel):
    url: str
    cookie: Optional[str] = None
    
class SummaryRequest(BaseModel):
    path: str

class HedgeDocHistoryRequest(BaseModel):
    base_url: str
    cookie: str

@app.get("/")
def read_root():
    return {"message": "Summa API is running"}

@app.get("/files")
def get_local_files():
    """List all files found in the data directory."""
    return local_service.list_files()

@app.get("/files/content")
def get_file_content(path: str):
    """Get content of a specific file (if text/markdown)."""
    # Security check: prevent directory traversal
    # This is a basic PoC check
    if ".." in path or not os.path.abspath(os.path.join(DATA_DIR, path)).startswith(os.path.abspath(DATA_DIR)):
         raise HTTPException(status_code=403, detail="Access denied")
    
    return local_service.get_content(path)

from fastapi import UploadFile, File

@app.post("/files/upload")
def upload_file(file: UploadFile = File(...)):
    """Upload a file to the data directory."""
    # We use file.file which is the SpooledThinkingFile/BytesIO
    result = local_service.save_upload(file.file, file.filename)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.delete("/files/delete")
def delete_file_endpoint(path: str):
    """Delete a file."""
    result = local_service.delete_file(path)
    if "error" in result:
        # Check if 404 or 500
        if result["error"] == "File not found":
             raise HTTPException(status_code=404, detail=result["error"])
        elif result["error"] == "Access denied":
             raise HTTPException(status_code=403, detail=result["error"])
        else:
             raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/hedgedoc")
def fetch_hedgedoc(request: HedgeDocRequest):
    """Fetch content from a HedgeDoc URL."""
    content = hedgedoc_service.fetch_content(request.url, request.cookie)
    if content is None:
        raise HTTPException(status_code=404, detail="Could not fetch HedgeDoc content")
    return {"content": content}

@app.post("/hedgedoc/history")
def fetch_hedgedoc_history(request: HedgeDocHistoryRequest):
    """Fetch history (my notes) from HedgeDoc."""
    history = hedgedoc_service.fetch_history(request.base_url, request.cookie)
    if isinstance(history, dict) and "error" in history:
        raise HTTPException(status_code=400, detail=history["error"])
    return {"history": history}

class HedgeDocDownloadRequest(BaseModel):
    url: str
    cookie: Optional[str] = None
    filename: str

@app.post("/hedgedoc/download")
def download_hedgedoc(request: HedgeDocDownloadRequest):
    """Download content from HedgeDoc and save to data directory."""
    content = hedgedoc_service.fetch_content(request.url, request.cookie)
    if content is None:
        raise HTTPException(status_code=404, detail="Could not fetch HedgeDoc content")
    
    result = local_service.save_content(request.filename, content)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return result

@app.get("/github/{username}")
def get_github_stats(username: str):
    """Fetch recent contribution stats/events for a GitHub user."""
    data = github_service.get_user_events(username)
    if data is None:
         raise HTTPException(status_code=404, detail="GitHub user not found or API error")
    return data

from fastapi.responses import StreamingResponse

@app.post("/files/summary")
def generate_file_summary(request: SummaryRequest):
    """Generate a summary for a local file using the local LLM (Streamed)."""
    return StreamingResponse(llm_service.process_file_stream(request.path), media_type="text/plain")

@app.get("/files/summary")
def get_file_summary(path: str):
    """Retrieve an existing summary for a file from the database."""
    summary = db_manager.get_summary(path)
    if not summary:
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
    return db_manager.get_all_tags()

@app.post("/tags")
def create_tag(tag: TagCreate):
    """Create a new tag."""
    db_manager.add_tag(tag.name)
    return {"message": "Tag created"}

@app.delete("/tags/{name}")
def delete_tag(name: str):
    """Delete a tag."""
    db_manager.delete_tag(name)
    return {"message": "Tag deleted"}

@app.post("/files/tags")
def update_file_tags(update: FileTagUpdate):
    """Update tags for a file."""
    print(f"DEBUG: Endpoint update_file_tags called with path={update.path} tags={update.tags}")
    
    # Ensure all tags are registered in the global 'tags' table
    for tag in update.tags:
        db_manager.add_tag(tag)
    
    db_manager.update_file_tags(update.path, update.tags)
    return {"message": "Tags updated"}

@app.post("/files/suggest_tags")
def suggest_tags(request: SummaryRequest):
    """Generate tag suggestions for a file using LLM."""
    # Reusing SummaryRequest since it just needs path
    result = llm_service.process_file_tags(request.path)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/llm/models")
def get_llm_models():
    return llm_service.get_models()

@app.get("/llm/embedding_models")
def get_llm_embedding_models():
    return llm_service.get_embedding_models()

