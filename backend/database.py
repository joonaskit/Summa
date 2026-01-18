import duckdb
import os
from typing import Optional, List, Dict, Any

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establishes a connection to the DuckDB database."""
        self.connection = duckdb.connect(self.db_path)
    
    def close(self):
        """Closes the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def init_db(self):
        """Initializes the database schema."""
        if not self.connection:
            self.connect()
        
        # Create table for file metadata
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS files_metadata (
                path VARCHAR PRIMARY KEY,
                filename VARCHAR,
                last_modified TIMESTAMP,
                size BIGINT,
                file_type VARCHAR,
                hash VARCHAR
            )
        """)

        # Create table for file summaries/content analysis
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS file_summaries (
                path VARCHAR PRIMARY KEY,
                summary_text TEXT,
                tags VARCHAR[],
                generated_at TIMESTAMP,
                model_used VARCHAR,
                FOREIGN KEY (path) REFERENCES files_metadata(path)
            )
        """)
        
    def upsert_file_metadata(self, path: str, filename: str, last_modified: Any, size: int, file_type: str):
        """Insert or update file metadata."""
        if not self.connection:
            self.connect()
            
        self.connection.execute("""
            INSERT INTO files_metadata (path, filename, last_modified, size, file_type)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (path) DO UPDATE SET
                filename = EXCLUDED.filename,
                last_modified = EXCLUDED.last_modified,
                size = EXCLUDED.size,
                file_type = EXCLUDED.file_type
        """, (path, filename, last_modified, size, file_type))

    def get_file_metadata(self, path: str) -> Optional[Dict]:
        """Retrieve metadata for a specific file."""
        if not self.connection:
            self.connect()
            
        result = self.connection.execute("SELECT * FROM files_metadata WHERE path = ?", (path,)).fetchone()
        if result:
            # zip with column names if we want a dict, or just use indices
            columns = [desc[0] for desc in self.connection.description]
            return dict(zip(columns, result))
        return None

    def save_summary(self, path: str, summary: str, tags: List[str], model: str):
        """Save a summary for a file."""
        if not self.connection:
            self.connect()
            
        # We need to make sure the file exists in metadata first, usually handled by upsert_file_metadata
        # But for safety, we could enforce FK constraints or handle it here.
        # Assuming metadata is synced.
        
        import datetime
        now = datetime.datetime.now()
        
        self.connection.execute("""
            INSERT INTO file_summaries (path, summary_text, tags, generated_at, model_used)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (path) DO UPDATE SET
                summary_text = EXCLUDED.summary_text,
                tags = EXCLUDED.tags,
                generated_at = EXCLUDED.generated_at,
                model_used = EXCLUDED.model_used
        """, (path, summary, tags, now, model))

    def get_summary(self, path: str) -> Optional[Dict]:
        """Retrieve summary for a specific file."""
        if not self.connection:
            self.connect()
            
        result = self.connection.execute("SELECT * FROM file_summaries WHERE path = ?", (path,)).fetchone()
        if result:
            columns = [desc[0] for desc in self.connection.description]
            return dict(zip(columns, result))
        return None
