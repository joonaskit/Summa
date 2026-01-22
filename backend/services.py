import os
import glob
import requests
import mimetypes
from datetime import datetime
import pypdf 
from docx import Document 
from pptx import Presentation

class LocalFileService:
    def __init__(self, root_dir: str, db_manager=None):
        self.root_dir = root_dir
        self.db_manager = db_manager
        # Ensure directory exists for PoC
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)

    def list_files(self):
        files_data = []
        # Recursive search for relevant extensions
        extensions = ['*.md', '*.pdf', '*.docx', '*.pptx', '*.xlsx', '*.txt']
        
        # Helper to check summaries efficiently
        summaries_set = set()
        if self.db_manager:
            summaries_set = set(self.db_manager.get_files_with_summaries())

        # globe recursive needs python 3.10+ for 'root_dir/**/ext' or manual walk
        # Using os.walk for better compatibility and control
        for root, dirs, files in os.walk(self.root_dir):
            for file in files:
                if self._match_ext(file, extensions):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    
                    stat = os.stat(full_path)
                    last_modified_dt = datetime.fromtimestamp(stat.st_mtime)
                    file_type = os.path.splitext(file)[1][1:]
                    
                    file_info = {
                        "name": file,
                        "path": rel_path,
                        "type": file_type,
                        "size": stat.st_size,
                        "modified": last_modified_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        "has_summary": rel_path in summaries_set
                    }
                    files_data.append(file_info)
                    
                    # Sync to DB if available
                    if self.db_manager:
                        self.db_manager.upsert_file_metadata(
                            path=rel_path,
                            filename=file,
                            last_modified=last_modified_dt,
                            size=stat.st_size,
                            file_type=file_type
                        )
                        file_info["tags"] = self.db_manager.get_file_tags(rel_path)
        return files_data

    def _match_ext(self, filename, extensions):
        # Simplified matcher
        ext = os.path.splitext(filename)[1]
        return any(pat.endswith(ext) for pat in extensions)

    def get_content(self, rel_path):
        full_path = os.path.join(self.root_dir, rel_path)
        if not os.path.exists(full_path):
            return {"error": "File not found"}
        
        ext = os.path.splitext(full_path)[1].lower()
        
        if ext in ['.md', '.txt']:
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return {"content": f.read(), "type": "text"}
            except Exception as e:
                return {"error": f"Failed to read text file: {e}"}
        
        elif ext == '.pdf':
            try:
                text = ""
                reader = pypdf.PdfReader(full_path)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return {"content": text, "type": "text"}
            except Exception as e:
                return {"error": f"Failed to read PDF: {e}"}

        elif ext == '.docx':
            try:
                doc = Document(full_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                return {"content": text, "type": "text"}
            except Exception as e:
                return {"error": f"Failed to read DOCX: {e}"}

        elif ext == '.pptx':
            try:
                prs = Presentation(full_path)
                text = []
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text.append(shape.text)
                return {"content": "\n".join(text), "type": "text"}
            except Exception as e:
                return {"error": f"Failed to read PPTX: {e}"}
                
        else:
            # For binary files not yet supported (e.g. xlsx), return message
            return {"content": "Binary file content not displayable in text view yet.", "type": "binary"}

    def save_content(self, filename: str, content: str):
        # Basic sanitization could be done here
        safe_name = os.path.basename(filename)
        full_path = os.path.join(self.root_dir, safe_name)
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update DB
            if self.db_manager:
                 stat = os.stat(full_path)
                 self.db_manager.upsert_file_metadata(
                    path=safe_name, # since we save to root of data dir
                    filename=safe_name,
                    last_modified=datetime.now(),
                    size=stat.st_size,
                    file_type=os.path.splitext(safe_name)[1][1:]
                )

            return {"success": True, "path": safe_name}
        except Exception as e:
            return {"error": str(e)}

    def save_upload(self, file_obj, filename: str):
        """Save an uploaded binary file stream."""
        safe_name = os.path.basename(filename)
        full_path = os.path.join(self.root_dir, safe_name)
        
        try:
            with open(full_path, 'wb') as f:
                while contents := file_obj.read(1024 * 1024): # Read in chunks
                    f.write(contents)
            
            # Update DB
            if self.db_manager:
                 stat = os.stat(full_path)
                 self.db_manager.upsert_file_metadata(
                    path=safe_name, 
                    filename=safe_name,
                    last_modified=datetime.now(),
                    size=stat.st_size,
                    file_type=os.path.splitext(safe_name)[1][1:]
                )
                
            return {"success": True, "path": safe_name}
        except Exception as e:
            return {"error": str(e)}

    def delete_file(self, rel_path: str):
        """Delete a file from disk and DB."""
        full_path = os.path.join(self.root_dir, rel_path)
        
        # Security check: prevent directory traversal
        if ".." in rel_path or not os.path.abspath(full_path).startswith(os.path.abspath(self.root_dir)):
             return {"error": "Access denied"}
        
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                
                # Update DB
                if self.db_manager:
                    self.db_manager.delete_file(rel_path)
                    
                return {"success": True, "message": f"Deleted {rel_path}"}
            else:
                return {"error": "File not found"}
        except Exception as e:
            return {"error": f"Failed to delete file: {str(e)}"}

class HedgeDocService:
    def fetch_content(self, url: str, cookie: str = None):
        # HedgeDoc usually exposes raw content at /download or if it's already a raw link
        # If user provides view url like https://demo.hedgedoc.org/s/By-Q ...
        # We might need to transform it.
        # For now, assume user provides the link and we try to append /download if not present
        
        target_url = url
        headers = {}
        if cookie:
            headers['Cookie'] = cookie

        if not url.endswith('/download') and not '/raw' in url:
             # Basic heuristic: append /download
             # Note: This depends on the specific HedgeDoc instance.
             # Standard HedgeDoc: https://md.example.com/s/Features -> https://md.example.com/Features/download
             # Or https://md.example.com/Features -> https://md.example.com/Features/download
             pass
             
        # Best effort: try adding /download if just fetching the url returns html
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                # If forbidden, maybe it's private and we have a cookie, but url is wrong 
                # or cookie is invalid.
                return None
            
            # If Content-Type is text/markdown or text/plain, good.
            ct = resp.headers.get('Content-Type', '')
            if 'text/html' in ct:
                 # Try appending /download
                 download_url = url.rstrip('/') + '/download'
                 resp2 = requests.get(download_url, headers=headers)
                 if resp2.status_code == 200:
                     return resp2.text
                 return f"Could not extract markdown. Retrieved HTML from {url}"
            
            return resp.text
        except Exception as e:
            return f"Error fetching HedgeDoc: {str(e)}"

    def fetch_history(self, base_url: str, cookie: str):
        """
        Fetch history from /history endpoint.
        Requires authenticated session cookie.
        """
        if not base_url:
            return None
            
        history_url = base_url.rstrip('/') + '/history'
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0' # sometimes needed
        }
        
        try:
            resp = requests.get(history_url, headers=headers)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    # HedgeDoc /history returns a list of notes
                    # Each note has 'id', 'text' (title), 'time' (last visited/edit)
                    return data.get('history', [])
                except:
                     return {"error": "Failed to parse history JSON", "raw": resp.text[:200]}
            elif resp.status_code == 403:
                return {"error": "Forbidden. Cookie might be invalid."}
            else:
                return {"error": f"Failed to fetch history: {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

class GitHubService:
    def get_user_events(self, username: str):
        url = f"https://api.github.com/users/{username}/events/public"
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                events = resp.json()
                # Summarize standard push events
                summary = []
                for e in events[:10]: # Last 10 events
                    etype = e.get('type')
                    repo = e.get('repo', {}).get('name')
                    created_at = e.get('created_at')
                    if etype == 'PushEvent':
                        commits = len(e.get('payload', {}).get('commits', []))
                        summary.append(f"Pushed {commits} commits to {repo} at {created_at}")
                    elif etype == 'CreateEvent':
                         ref_type = e.get('payload', {}).get('ref_type')
                         summary.append(f"Created {ref_type} in {repo} at {created_at}")
                    else:
                        summary.append(f"{etype} at {repo} at {created_at}")
                return {"events": summary, "raw_count": len(events)}
            return None
        except Exception as e:
            return {"error": str(e)}

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Iterator, List

class LLMService:
    def __init__(self, base_url: str = "http://host.docker.internal:1234/v1", db_manager=None, local_file_service=None):
        self.base_url = base_url
        self.db_manager = db_manager
        self.local_file_service = local_file_service
        # Initialize LangChain ChatOpenAI
        # Note: API Key is required but ignored by local LLMs usually, but we set a dummy one.
        self.llm = ChatOpenAI(
            base_url=self.base_url,
            api_key="lm-studio",
            model="local-model", # Model name often doesn't matter for local endpoints
            temperature=0.7
        )

    def generate_summary(self, content: str) -> str:
        """Generates a summary for the given text content."""
        try:
            messages = [
                SystemMessage(content="You are a helpful assistant that summarizes documents efficiently."),
                HumanMessage(content=f"Please provide a concise summary of the following document:\n\n{content[:8000]}") # Truncate to avoid context window issues if huge
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def process_file(self, path: str):
        """Reads file, generates summary, and stores in DB."""
        if not self.local_file_service or not self.db_manager:
            return {"error": "Services not fully initialized"}

        # 1. Get Content
        file_data = self.local_file_service.get_content(path)
        if "error" in file_data:
            return file_data
        
        if file_data.get("type") != "text":
             return {"error": "Only text files can be summarized currently."}
            
        content = file_data.get("content")
        if not content:
             return {"error": "File is empty."}

        # 2. Generate Summary
        summary = self.generate_summary(content)
        
        # 3. Save to DB
        # Tags could be extracted by LLM too, but for now we leave empty
        self.db_manager.save_summary(
            path=path,
            summary=summary,
            tags=[],
            model="local-llm"
        )
        
    def generate_summary_stream(self, content: str) -> Iterator[str]:
        """Generates a summary stream for the given text content."""
        try:
            messages = [
                SystemMessage(content="You are a helpful assistant that summarizes documents efficiently."),
                HumanMessage(content=f"Please provide a concise summary of the following document:\n\n{content[:8000]}")
            ]
            for chunk in self.llm.stream(messages):
                yield chunk.content
        except Exception as e:
            yield f"Error generating summary: {str(e)}"

    def process_file_stream(self, path: str):
        """Reads file, streams summary generation, and stores in DB."""
        if not self.local_file_service or not self.db_manager:
            yield "Services not fully initialized"
            return

        # 1. Check if summary exists first? 
        # For now, we assume user clicked "Generate" so they want a fresh one or it doesn't exist.
        # But if we want to be smart, we could check DB. 
        # For this task, let's regenerate to show the streaming effect.

        # 2. Get Content
        file_data = self.local_file_service.get_content(path)
        if "error" in file_data:
            yield f"Error: {file_data['error']}"
            return
        
        if file_data.get("type") != "text":
             yield "Error: Only text files can be summarized currently."
             return
            
        content = file_data.get("content")
        if not content:
             yield "Error: File is empty."
             return

        # 3. Stream Summary & Collect
        full_summary = ""
        for chunk in self.generate_summary_stream(content):
            full_summary += chunk
            yield chunk
        
        # 4. Save to DB after streaming completes
        self.db_manager.save_summary(
            path=path,
            summary=full_summary,
            tags=[],
            model="local-llm"
        )
        
    def generate_tags(self, content: str) -> List[str]:
        """Generates tag suggestions for the given text content."""
        try:
            # Fetch existing tags
            existing_tags = []
            if self.db_manager:
                existing_tags = self.db_manager.get_all_tags()
            
            existing_tags_str = ", ".join(existing_tags) if existing_tags else "None"

            messages = [
                SystemMessage(content=f"You are a helpful assistant that analyzes documents and suggests meaningful tags. You have access to the following existing tags: [{existing_tags_str}]. Prioritize using these tags if they are relevant, but you may create new ones if necessary. Provide only a comma-separated list of 3-5 tags. Do not include any other text."),
                HumanMessage(content=f"Please suggest tags for the following document:\n\n{content[:5000]}")
            ]
            response = self.llm.invoke(messages)
            # Parse response
            raw_tags = response.content.strip()
            # Split by comma and clean
            tags = [t.strip() for t in raw_tags.split(',') if t.strip()]
            return tags[:5] # Limit to 5
        except Exception as e:
            return []

    def process_file_tags(self, path: str):
        """Generates tags for a file."""
        if not self.local_file_service:
             return {"error": "Services not fully initialized"}

        # 1. Get Content
        file_data = self.local_file_service.get_content(path)
        if "error" in file_data:
            return file_data
        
        if file_data.get("type") != "text":
             return {"error": "Only text files can be processed."}
            
        content = file_data.get("content")
        if not content:
             return {"error": "File is empty."}

        # 2. Generate Tags
        tags = self.generate_tags(content)
        return {"tags": tags}
