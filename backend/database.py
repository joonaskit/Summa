import duckdb
import os
from typing import Optional, List, Dict, Any

from .logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
        logger.info(f"DatabaseManager initialized with path: {db_path}")

    def connect(self):
        """Establishes a connection to the DuckDB database."""
        logger.info(f"Connecting to database: {self.db_path}")
        self.connection = duckdb.connect(self.db_path)
        logger.info("Database connection established")
    
    def close(self):
        """Closes the database connection."""
        if self.connection:
            logger.info("Closing database connection")
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

    def init_db(self):
        """Initializes the database schema."""
        logger.info("Initializing database schema")
        if not self.connection:
            self.connect()
        
        # Create table for file metadata
        logger.debug("Creating files_metadata table")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS files_metadata (
                path VARCHAR PRIMARY KEY,
                filename VARCHAR,
                last_modified TIMESTAMP,
                size BIGINT,
                file_type VARCHAR,
                hash VARCHAR,
                tags VARCHAR[]
            )

        """)

        # Migration: Add tags column if it doesn't exist (for existing DBs)
        try:
            columns = [c[1] for c in self.connection.execute("PRAGMA table_info('files_metadata')").fetchall()]
            if 'tags' not in columns:
                logger.info("Migrating: Adding tags column to files_metadata")
                self.connection.execute("ALTER TABLE files_metadata ADD COLUMN tags VARCHAR[]")
        except Exception as e:
            logger.warning(f"Migration warning: {e}")

        # Create table for tags
        logger.debug("Creating tags table")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                name VARCHAR PRIMARY KEY
            )
        """)

        # Create table for file summaries/content analysis
        logger.debug("Creating file_summaries table")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS file_summaries (
                path VARCHAR PRIMARY KEY,
                summary_text TEXT,
                tags VARCHAR[],
                generated_at TIMESTAMP,
                model_used VARCHAR
                -- Removed FOREIGN KEY due to DuckDB strictness on parent updates
            )
        """)
        
        # Migration: Remove FK from file_summaries if it exists
        try:
            has_fk = self.connection.execute("SELECT 1 FROM duckdb_constraints WHERE table_name='file_summaries' AND constraint_type='FOREIGN KEY'").fetchone()
            if has_fk:
                logger.info("Migrating file_summaries to remove Foreign Key constraint")
                self.connection.execute("ALTER TABLE file_summaries RENAME TO file_summaries_old")
                self.connection.execute("""
                    CREATE TABLE file_summaries (
                        path VARCHAR PRIMARY KEY,
                        summary_text TEXT,
                        tags VARCHAR[],
                        generated_at TIMESTAMP,
                        model_used VARCHAR
                    )
                """)
                self.connection.execute("INSERT INTO file_summaries SELECT * FROM file_summaries_old")
                self.connection.execute("DROP TABLE file_summaries_old")
                logger.info("Migration complete")
        except Exception as e:
            logger.warning(f"Migration error (FK removal): {e}")
        
        # Create table for video transcripts
        logger.debug("Creating videos table")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id VARCHAR PRIMARY KEY,
                youtube_url VARCHAR NOT NULL,
                title VARCHAR,
                transcript_text TEXT,
                created_at TIMESTAMP
            )
        """)
        
        # Create table for local videos
        logger.debug("Creating local_videos table")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS local_videos (
                id VARCHAR PRIMARY KEY,
                filename VARCHAR NOT NULL,
                stored_path VARCHAR NOT NULL,
                file_size BIGINT NOT NULL,
                file_hash VARCHAR NOT NULL,
                mime_type VARCHAR,
                duration FLOAT,
                width INTEGER,
                height INTEGER,
                transcript_text TEXT,
                created_at TIMESTAMP NOT NULL,
                transcribed_at TIMESTAMP,
                UNIQUE(file_hash)
            )
        """)
        
        logger.info("Database schema initialized successfully")
        
    def upsert_file_metadata(self, path: str, filename: str, last_modified: Any, size: int, file_type: str):
        """Insert or update file metadata."""
        logger.debug(f"Upserting file metadata for: {path}")
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
        logger.debug(f"File metadata upserted for: {path}")

    def get_file_metadata(self, path: str) -> Optional[Dict]:
        """Retrieve metadata for a specific file."""
        logger.debug(f"Retrieving file metadata for: {path}")
        if not self.connection:
            self.connect()
            
        result = self.connection.execute("SELECT * FROM files_metadata WHERE path = ?", (path,)).fetchone()
        if result:
            # zip with column names if we want a dict, or just use indices
            columns = [desc[0] for desc in self.connection.description]
            return dict(zip(columns, result))
        logger.debug(f"No metadata found for: {path}")
        return None

    def save_summary(self, path: str, summary: str, tags: List[str], model: str):
        """Save a summary for a file."""
        logger.info(f"Saving summary for file: {path}")
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
        logger.info(f"Summary saved for file: {path}")

    def get_summary(self, path: str) -> Optional[Dict]:
        """Retrieve summary for a specific file."""
        logger.debug(f"Retrieving summary for file: {path}")
        if not self.connection:
            self.connect()
            
        result = self.connection.execute("SELECT * FROM file_summaries WHERE path = ?", (path,)).fetchone()
        if result:
            columns = [desc[0] for desc in self.connection.description]
            return dict(zip(columns, result))
        logger.debug(f"No summary found for: {path}")
        return None

    def get_files_with_summaries(self) -> List[str]:
        """Retrieve a list of file paths that have summaries."""
        logger.debug("Retrieving files with summaries")
        if not self.connection:
            self.connect()
        result = self.connection.execute("SELECT path FROM file_summaries").fetchall()
        paths = [row[0] for row in result]
        logger.debug(f"Found {len(paths)} files with summaries")
        return paths

    def get_all_tags(self) -> List[str]:
        """Retrieve all available tags."""
        logger.debug("Retrieving all tags")
        if not self.connection:
            self.connect()
        result = self.connection.execute("SELECT name FROM tags ORDER BY name").fetchall()
        tags = [row[0] for row in result]
        logger.debug(f"Found {len(tags)} tags")
        return tags

    def add_tag(self, name: str):
        """Add a new tag."""
        if not self.connection:
            self.connect()
        # Clean tag name
        name = name.strip()
        if not name:
             return
        logger.debug(f"Adding tag: {name}")
        self.connection.execute("INSERT INTO tags (name) VALUES (?) ON CONFLICT DO NOTHING", (name,))

    def delete_tag(self, name: str):
        """Delete a tag."""
        logger.info(f"Deleting tag: {name}")
        if not self.connection:
            self.connect()
        self.connection.execute("DELETE FROM tags WHERE name = ?", (name,))
        logger.info(f"Tag deleted: {name}")

    def update_file_tags(self, path: str, tags: List[str]):
        """Update tags for a specific file."""
        logger.info(f"Updating tags for {path} to {tags}")
        if not self.connection:
            self.connect()
        
        # Update
        self.connection.execute("UPDATE files_metadata SET tags = ? WHERE path = ?", (tags, path))
            
        # Verify
        res = self.connection.execute("SELECT tags FROM files_metadata WHERE path = ?", (path,)).fetchone()
        logger.debug(f"Verify update for {path}: {res[0] if res else 'Row not found'}")

    def get_file_tags(self, path: str) -> List[str]:
        """Get tags for a file."""
        if not self.connection:
            self.connect()
        result = self.connection.execute("SELECT tags FROM files_metadata WHERE path = ?", (path,)).fetchone()
        logger.debug(f"Get tags for {path}: {result[0] if result else 'None'}")
        if result and result[0]:
            return result[0]
        return []

    def delete_file(self, path: str):
        """Delete file metadata and summaries."""
        logger.info(f"Deleting file from database: {path}")
        if not self.connection:
            self.connect()
        
        # Delete from summaries
        self.connection.execute("DELETE FROM file_summaries WHERE path = ?", (path,))
        
        # Delete from metadata
        self.connection.execute("DELETE FROM files_metadata WHERE path = ?", (path,))
        logger.info(f"File deleted from database: {path}")

    def save_video(self, video_id: str, youtube_url: str, title: str, transcript: str):
        """Save video metadata and transcript to database."""
        logger.info(f"Saving video to database: {video_id}")
        if not self.connection:
            self.connect()
        
        import datetime
        now = datetime.datetime.now()
        
        self.connection.execute("""
            INSERT INTO videos (id, youtube_url, title, transcript_text, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                youtube_url = EXCLUDED.youtube_url,
                title = EXCLUDED.title,
                transcript_text = EXCLUDED.transcript_text
        """, (video_id, youtube_url, title, transcript, now))
        logger.info(f"Video saved successfully: {video_id}")

    def get_video_by_url(self, youtube_url: str) -> Optional[Dict]:
        """Retrieve video data by YouTube URL.
        
        Note: This method extracts the video ID from the URL and searches by ID,
        so different URL formats for the same video will return the same result.
        """
        logger.debug(f"Retrieving video by URL: {youtube_url}")
        if not self.connection:
            self.connect()
        
        # Extract video ID from URL using regex patterns
        import re
        video_id = None
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, youtube_url.strip())
            if match:
                video_id = match.group(1)
                break
        
        if not video_id:
            logger.warning(f"Could not extract video ID from URL: {youtube_url}")
            return None
        
        logger.debug(f"Extracted video ID: {video_id}")
        result = self.connection.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        
        if result:
            columns = [desc[0] for desc in self.connection.description]
            video_data = dict(zip(columns, result))
            logger.debug(f"Video found in database: {video_id}")
            return video_data
        
        logger.debug(f"Video not found in database: {video_id}")
        return None

    def get_all_videos(self) -> List[Dict]:
        """Retrieve all videos from the database.
        
        Returns:
            List[Dict]: List of all video records with all columns
        """
        logger.debug("Retrieving all videos from database")
        if not self.connection:
            self.connect()
        
        results = self.connection.execute(
            "SELECT id, youtube_url, title, transcript_text, created_at FROM videos ORDER BY created_at DESC"
        ).fetchall()
        
        if results:
            columns = [desc[0] for desc in self.connection.description]
            videos = [dict(zip(columns, row)) for row in results]
            logger.debug(f"Found {len(videos)} videos in database")
            return videos
        
        logger.debug("No videos found in database")
        return []

    def delete_video_by_url(self, youtube_url: str) -> bool:
        """Delete a video from the database by YouTube URL.
        
        Args:
            youtube_url: YouTube video URL
            
        Returns:
            bool: True if video was deleted, False if not found
        """
        logger.info(f"Deleting video by URL: {youtube_url}")
        if not self.connection:
            self.connect()
        
        # Extract video ID from URL using regex patterns
        import re
        video_id = None
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, youtube_url.strip())
            if match:
                video_id = match.group(1)
                break
        
        if not video_id:
            logger.warning(f"Could not extract video ID from URL: {youtube_url}")
            return False
        
        logger.debug(f"Extracted video ID for deletion: {video_id}")
        
        # Check if video exists
        result = self.connection.execute("SELECT id FROM videos WHERE id = ?", (video_id,)).fetchone()
        
        if not result:
            logger.warning(f"Video not found in database: {video_id}")
            return False
        
        # Delete the video
        self.connection.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        logger.info(f"Successfully deleted video: {video_id}")
        return True

    # Local Video Methods
    
    def save_local_video(self, video_id: str, filename: str, stored_path: str, 
                        file_size: int, file_hash: str, mime_type: Optional[str] = None,
                        duration: Optional[float] = None, width: Optional[int] = None, 
                        height: Optional[int] = None) -> bool:
        """Save local video metadata to database.
        
        Args:
            video_id: Unique identifier (UUID)
            filename: Original filename
            stored_path: Path where video is stored
            file_size: File size in bytes
            file_hash: SHA-256 hash of file
            mime_type: Video MIME type
            duration: Video duration in seconds
            width: Video width in pixels
            height: Video height in pixels
            
        Returns:
            bool: True if saved successfully, False if duplicate hash exists
        """
        logger.info(f"Saving local video to database: {video_id}")
        if not self.connection:
            self.connect()
        
        import datetime
        now = datetime.datetime.now()
        
        try:
            self.connection.execute("""
                INSERT INTO local_videos (id, filename, stored_path, file_size, file_hash, 
                                         mime_type, duration, width, height, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (video_id, filename, stored_path, file_size, file_hash, 
                  mime_type, duration, width, height, now))
            logger.info(f"Local video saved successfully: {video_id}")
            return True
        except Exception as e:
            # Check if it's a duplicate hash error
            if "UNIQUE constraint" in str(e) or "Constraint Error" in str(e):
                logger.warning(f"Duplicate video hash detected: {file_hash}")
                return False
            else:
                logger.error(f"Error saving local video: {str(e)}", exc_info=True)
                raise

    def get_local_video_by_id(self, video_id: str) -> Optional[Dict]:
        """Retrieve local video metadata by ID.
        
        Args:
            video_id: Video UUID
            
        Returns:
            Dict with video metadata or None if not found
        """
        logger.debug(f"Retrieving local video by ID: {video_id}")
        if not self.connection:
            self.connect()
        
        result = self.connection.execute(
            "SELECT * FROM local_videos WHERE id = ?", (video_id,)
        ).fetchone()
        
        if result:
            columns = [desc[0] for desc in self.connection.description]
            video_data = dict(zip(columns, result))
            logger.debug(f"Local video found: {video_id}")
            return video_data
        
        logger.debug(f"Local video not found: {video_id}")
        return None

    def get_local_video_by_hash(self, file_hash: str) -> Optional[Dict]:
        """Retrieve local video metadata by file hash.
        
        Args:
            file_hash: SHA-256 hash of video file
            
        Returns:
            Dict with video metadata or None if not found
        """
        logger.debug(f"Retrieving local video by hash: {file_hash[:16]}...")
        if not self.connection:
            self.connect()
        
        result = self.connection.execute(
            "SELECT * FROM local_videos WHERE file_hash = ?", (file_hash,)
        ).fetchone()
        
        if result:
            columns = [desc[0] for desc in self.connection.description]
            video_data = dict(zip(columns, result))
            logger.debug(f"Local video found by hash: {video_data['id']}")
            return video_data
        
        logger.debug("No local video found with this hash")
        return None

    def get_all_local_videos(self) -> List[Dict]:
        """Retrieve all local videos from database.
        
        Returns:
            List of video metadata dictionaries
        """
        logger.debug("Retrieving all local videos from database")
        if not self.connection:
            self.connect()
        
        results = self.connection.execute("""
            SELECT id, filename, stored_path, file_size, file_hash, mime_type, 
                   duration, width, height, transcript_text, created_at, transcribed_at
            FROM local_videos 
            ORDER BY created_at DESC
        """).fetchall()
        
        if results:
            columns = [desc[0] for desc in self.connection.description]
            videos = [dict(zip(columns, row)) for row in results]
            logger.debug(f"Found {len(videos)} local videos in database")
            return videos
        
        logger.debug("No local videos found in database")
        return []

    def update_local_video_transcript(self, video_id: str, transcript: str) -> bool:
        """Update transcript for a local video.
        
        Args:
            video_id: Video UUID
            transcript: Transcript text
            
        Returns:
            bool: True if updated successfully, False if video not found
        """
        logger.info(f"Updating transcript for local video: {video_id}")
        if not self.connection:
            self.connect()
        
        import datetime
        now = datetime.datetime.now()
        
        # Check if video exists
        result = self.connection.execute(
            "SELECT id FROM local_videos WHERE id = ?", (video_id,)
        ).fetchone()
        
        if not result:
            logger.warning(f"Local video not found for transcript update: {video_id}")
            return False
        
        # Update transcript
        self.connection.execute("""
            UPDATE local_videos 
            SET transcript_text = ?, transcribed_at = ?
            WHERE id = ?
        """, (transcript, now, video_id))
        
        logger.info(f"Transcript updated successfully for local video: {video_id}")
        return True

    def delete_local_video(self, video_id: str) -> bool:
        """Delete local video metadata from database.
        
        Args:
            video_id: Video UUID
            
        Returns:
            bool: True if deleted, False if not found
        """
        logger.info(f"Deleting local video from database: {video_id}")
        if not self.connection:
            self.connect()
        
        # Check if video exists
        result = self.connection.execute(
            "SELECT id FROM local_videos WHERE id = ?", (video_id,)
        ).fetchone()
        
        if not result:
            logger.warning(f"Local video not found for deletion: {video_id}")
            return False
        
        # Delete the video
        self.connection.execute("DELETE FROM local_videos WHERE id = ?", (video_id,))
        logger.info(f"Successfully deleted local video: {video_id}")
        return True

