import os
import uuid
import hashlib
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional, BinaryIO
from .logging_config import get_logger
from .video_service import VideoService

# Initialize logger for this module
logger = get_logger(__name__)


class LocalVideoService:
    """Service for handling local video file uploads, metadata extraction, and transcription."""
    
    # Supported video MIME types
    SUPPORTED_MIME_TYPES = [
        'video/mp4',
        'video/mpeg',
        'video/quicktime',
        'video/x-msvideo',
        'video/x-matroska',
        'video/webm',
    ]
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.mpeg', '.mpg']
    
    def __init__(self, storage_dir: str, db_manager=None, video_service: VideoService = None):
        """Initialize the LocalVideoService.
        
        Args:
            storage_dir: Base directory for storing videos (e.g., /app/data/media)
            db_manager: DatabaseManager instance for persisting metadata
            video_service: VideoService instance for transcription (reuses Whisper)
        """
        logger.info(f"Initializing LocalVideoService with storage_dir: {storage_dir}")
        self.storage_dir = Path(storage_dir)
        self.videos_dir = self.storage_dir / "videos"
        self.temp_dir = self.storage_dir / "temp"
        self.db_manager = db_manager
        self.video_service = video_service
        
        # Create directories if they don't exist
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Video storage directory: {self.videos_dir}")
        logger.info(f"Temp directory: {self.temp_dir}")
    
    def _compute_file_hash(self, file_obj: BinaryIO) -> str:
        """Compute SHA-256 hash of a file.
        
        Args:
            file_obj: File-like object to hash
            
        Returns:
            str: Hexadecimal hash string
        """
        logger.debug("Computing file hash")
        sha256_hash = hashlib.sha256()
        
        # Read file in chunks to handle large files
        file_obj.seek(0)  # Reset to beginning
        for byte_block in iter(lambda: file_obj.read(4096), b""):
            sha256_hash.update(byte_block)
        
        file_obj.seek(0)  # Reset again for subsequent reads
        file_hash = sha256_hash.hexdigest()
        logger.debug(f"File hash computed: {file_hash[:16]}...")
        return file_hash
    
    def _extract_video_metadata(self, file_path: str) -> Dict:
        """Extract video metadata using ffprobe.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Dict with duration, width, height, and other metadata
        """
        logger.info(f"Extracting video metadata from: {file_path}")
        
        try:
            # Use ffprobe to extract metadata
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            metadata = json.loads(result.stdout)
            
            # Extract relevant information
            video_stream = None
            for stream in metadata.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            extracted = {
                'duration': None,
                'width': None,
                'height': None,
                'codec': None,
            }
            
            # Get duration from format section
            if 'format' in metadata:
                duration_str = metadata['format'].get('duration')
                if duration_str:
                    extracted['duration'] = float(duration_str)
            
            # Get video dimensions and codec
            if video_stream:
                extracted['width'] = video_stream.get('width')
                extracted['height'] = video_stream.get('height')
                extracted['codec'] = video_stream.get('codec_name')
            
            logger.info(f"Metadata extracted: duration={extracted['duration']}s, "
                       f"resolution={extracted['width']}x{extracted['height']}")
            return extracted
            
        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed: {e.stderr}")
            return {'duration': None, 'width': None, 'height': None, 'codec': None}
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}", exc_info=True)
            return {'duration': None, 'width': None, 'height': None, 'codec': None}
    
    def _validate_video_file(self, filename: str, mime_type: Optional[str] = None) -> bool:
        """Validate if file is a supported video format.
        
        Args:
            filename: Original filename
            mime_type: MIME type if available
            
        Returns:
            bool: True if valid video file
        """
        # Check extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.SUPPORTED_EXTENSIONS:
            logger.warning(f"Unsupported file extension: {file_ext}")
            return False
        
        # Check MIME type if provided
        if mime_type and mime_type not in self.SUPPORTED_MIME_TYPES:
            logger.warning(f"Unsupported MIME type: {mime_type}")
            return False
        
        return True
    
    def upload_video(self, file_obj: BinaryIO, filename: str, 
                    mime_type: Optional[str] = None) -> Dict:
        """Handle video file upload.
        
        Args:
            file_obj: File-like object containing video data
            filename: Original filename
            mime_type: MIME type of the file
            
        Returns:
            Dict with upload result and video metadata
        """
        logger.info(f"Processing video upload: {filename}")
        
        # Validate file
        if not self._validate_video_file(filename, mime_type):
            logger.error(f"Invalid video file: {filename}")
            return {
                "error": "Unsupported video format. Supported formats: " + 
                        ", ".join(self.SUPPORTED_EXTENSIONS)
            }
        
        # Compute file hash
        file_hash = self._compute_file_hash(file_obj)
        
        # Check for duplicates
        if self.db_manager:
            existing_video = self.db_manager.get_local_video_by_hash(file_hash)
            if existing_video:
                logger.info(f"Duplicate video detected: {existing_video['id']}")
                return {
                    "duplicate": True,
                    "existing_video": existing_video,
                    "message": "This video already exists in the library"
                }
        
        # Generate unique ID and storage path
        video_id = str(uuid.uuid4())
        file_extension = Path(filename).suffix
        stored_filename = f"{video_id}{file_extension}"
        stored_path = self.videos_dir / stored_filename
        
        # Save file to storage
        try:
            logger.info(f"Saving video to: {stored_path}")
            with open(stored_path, 'wb') as f:
                file_obj.seek(0)
                f.write(file_obj.read())
            
            file_size = stored_path.stat().st_size
            logger.info(f"Video saved successfully, size: {file_size} bytes")
            
        except Exception as e:
            logger.error(f"Error saving video file: {str(e)}", exc_info=True)
            return {"error": f"Failed to save video: {str(e)}"}
        
        # Extract metadata
        metadata = self._extract_video_metadata(str(stored_path))
        
        # Save to database
        if self.db_manager:
            try:
                success = self.db_manager.save_local_video(
                    video_id=video_id,
                    filename=filename,
                    stored_path=str(stored_path),
                    file_size=file_size,
                    file_hash=file_hash,
                    mime_type=mime_type,
                    duration=metadata.get('duration'),
                    width=metadata.get('width'),
                    height=metadata.get('height')
                )
                
                if not success:
                    # Duplicate detected after saving file (race condition)
                    logger.warning("Duplicate detected after file save, cleaning up")
                    stored_path.unlink()  # Delete the file
                    existing_video = self.db_manager.get_local_video_by_hash(file_hash)
                    return {
                        "duplicate": True,
                        "existing_video": existing_video,
                        "message": "This video already exists in the library"
                    }
                    
            except Exception as e:
                # Clean up file if database save fails
                logger.error(f"Database save failed, cleaning up file: {str(e)}", exc_info=True)
                if stored_path.exists():
                    stored_path.unlink()
                return {"error": f"Failed to save video metadata: {str(e)}"}
        
        logger.info(f"Video upload completed successfully: {video_id}")
        return {
            "success": True,
            "id": video_id,
            "filename": filename,
            "file_size": file_size,
            "duration": metadata.get('duration'),
            "width": metadata.get('width'),
            "height": metadata.get('height'),
            "stored_path": str(stored_path)
        }
    
    def get_video_path(self, video_id: str) -> Optional[str]:
        """Get the file system path for a video.
        
        Args:
            video_id: Video UUID
            
        Returns:
            str: Absolute path to video file, or None if not found
        """
        logger.debug(f"Getting video path for: {video_id}")
        
        if self.db_manager:
            video = self.db_manager.get_local_video_by_id(video_id)
            if video:
                path = video.get('stored_path')
                if path and os.path.exists(path):
                    logger.debug(f"Video path found: {path}")
                    return path
                else:
                    logger.warning(f"Video file not found at stored path: {path}")
        
        logger.warning(f"Video not found: {video_id}")
        return None
    
    def transcribe_video(self, video_id: str) -> Dict:
        """Transcribe a local video using Whisper.
        
        Args:
            video_id: Video UUID
            
        Returns:
            Dict with transcript text or error
        """
        logger.info(f"Transcribing local video: {video_id}")
        
        if not self.video_service:
            logger.error("VideoService not available for transcription")
            return {"error": "Transcription service not available"}
        
        # Get video path
        video_path = self.get_video_path(video_id)
        if not video_path:
            logger.error(f"Video not found for transcription: {video_id}")
            return {"error": "Video not found"}
        
        # Extract audio to temp file
        audio_path = None
        try:
            # Use ffmpeg to extract audio
            audio_filename = f"{video_id}.mp3"
            audio_path = self.temp_dir / audio_filename
            
            logger.info(f"Extracting audio to: {audio_path}")
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'libmp3lame',
                '-ar', '16000',  # 16kHz sample rate (good for Whisper)
                '-ac', '1',  # Mono
                '-y',  # Overwrite output file
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("Audio extraction completed")
            
            # Transcribe using VideoService
            logger.info("Starting transcription with Whisper")
            transcript = self.video_service.transcribe_audio(str(audio_path))
            
            # Update database
            if self.db_manager:
                self.db_manager.update_local_video_transcript(video_id, transcript)
            
            logger.info(f"Transcription completed for video: {video_id}")
            return {
                "success": True,
                "transcript": transcript,
                "video_id": video_id
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio extraction failed: {e.stderr}")
            return {"error": f"Failed to extract audio: {e.stderr}"}
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}", exc_info=True)
            return {"error": f"Transcription failed: {str(e)}"}
        finally:
            # Clean up temporary audio file
            if audio_path and audio_path.exists():
                try:
                    audio_path.unlink()
                    logger.debug(f"Cleaned up temp audio file: {audio_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp audio: {str(e)}")
    
    def delete_video(self, video_id: str) -> Dict:
        """Delete a local video and its metadata.
        
        Args:
            video_id: Video UUID
            
        Returns:
            Dict with success status or error
        """
        logger.info(f"Deleting local video: {video_id}")
        
        # Get video path before deleting from DB
        video_path = self.get_video_path(video_id)
        
        # Delete from database
        if self.db_manager:
            deleted = self.db_manager.delete_local_video(video_id)
            if not deleted:
                logger.warning(f"Video not found in database: {video_id}")
                return {"error": "Video not found"}
        
        # Delete file from storage
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                logger.info(f"Video file deleted: {video_path}")
            except Exception as e:
                logger.error(f"Failed to delete video file: {str(e)}", exc_info=True)
                return {"error": f"Failed to delete video file: {str(e)}"}
        
        logger.info(f"Video deleted successfully: {video_id}")
        return {"success": True, "message": "Video deleted successfully"}
