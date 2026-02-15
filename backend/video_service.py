import re
import os
import time
import yt_dlp
from pathlib import Path
from typing import Dict, Optional
from faster_whisper import WhisperModel
from .logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)


class VideoService:
    """Service for handling YouTube video URLs and extracting metadata."""
    
    # YouTube URL patterns
    YOUTUBE_PATTERNS = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    
    def __init__(self, db_manager=None):
        """Initialize the VideoService.
        
        Args:
            db_manager: Optional DatabaseManager instance for caching transcripts
        """
        logger.info("Initializing VideoService")
        self.db_manager = db_manager
        
    def _is_valid_youtube_url(self, url: str) -> bool:
        """
        Validate if the URL is a valid YouTube URL.
        
        Args:
            url: The URL to validate
            
        Returns:
            bool: True if valid YouTube URL, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
            
        for pattern in self.YOUTUBE_PATTERNS:
            if re.match(pattern, url.strip()):
                return True
        return False
    
    def _extract_video_id(self, url: str) -> str:
        """
        Extract the 11-character video ID from a YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            str: The 11-character video ID
            
        Raises:
            ValueError: If video ID cannot be extracted
        """
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL")
        
        for pattern in self.YOUTUBE_PATTERNS:
            match = re.match(pattern, url.strip())
            if match:
                video_id = match.group(1)
                logger.debug(f"Extracted video ID: {video_id} from URL: {url}")
                return video_id
        
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    def get_video_info(self, url: str) -> Dict[str, any]:
        """
        Fetch metadata for a YouTube video without downloading it.
        
        Args:
            url: YouTube video URL
            
        Returns:
            dict: Video metadata containing title, author, duration, and thumbnail_url
            
        Raises:
            ValueError: If the URL is invalid or not a YouTube URL
            Exception: If there's an error fetching video information
        """
        logger.info(f"Fetching video info for URL: {url}")
        
        # Validate URL
        if not self._is_valid_youtube_url(url):
            logger.warning(f"Invalid YouTube URL provided: {url}")
            raise ValueError("Invalid YouTube URL. Please provide a valid YouTube video URL.")
        
        # Configure yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,  # Don't download the video
            'format': 'best',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video information
                info = ydl.extract_info(url, download=False)
                
                # Extract relevant metadata
                metadata = {
                    'title': info.get('title', 'Unknown Title'),
                    'author': info.get('uploader', info.get('channel', 'Unknown Author')),
                    'duration': info.get('duration', 0),  # Duration in seconds
                    'thumbnail_url': info.get('thumbnail', ''),
                }
                
                logger.info(f"Successfully fetched video info: {metadata['title']}")
                logger.debug(f"Video metadata: {metadata}")
                
                return metadata
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"yt-dlp download error for URL {url}: {error_msg}")
            
            # Check for common error cases
            if 'Video unavailable' in error_msg or 'Private video' in error_msg:
                raise ValueError("Video is unavailable or private")
            elif 'not a valid URL' in error_msg:
                raise ValueError("Invalid YouTube URL")
            else:
                raise Exception(f"Failed to fetch video information: {error_msg}")
                
        except Exception as e:
            logger.error(f"Unexpected error fetching video info for URL {url}: {str(e)}", exc_info=True)
            raise Exception(f"Failed to fetch video information: {str(e)}")
    
    def download_audio(self, url: str) -> str:
        """
        Download only the audio track from a YouTube video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            str: Path to the downloaded audio file
            
        Raises:
            ValueError: If the URL is invalid or not a YouTube URL
            Exception: If there's an error downloading the audio
        """
        logger.info(f"Downloading audio for URL: {url}")
        
        # Validate URL
        if not self._is_valid_youtube_url(url):
            logger.warning(f"Invalid YouTube URL provided for audio download: {url}")
            raise ValueError("Invalid YouTube URL. Please provide a valid YouTube video URL.")
        
        # Create temporary directory if it doesn't exist
        temp_dir = Path("/tmp/summa_audio")
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Temporary audio directory: {temp_dir}")
        
        # Generate unique filename using timestamp
        timestamp = int(time.time())
        output_path = temp_dir / f"audio_{timestamp}.mp3"
        
        # Configure yt-dlp options for audio-only download
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(temp_dir / f"audio_{timestamp}.%(ext)s"),
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Starting audio download from: {url}")
                ydl.download([url])
                
            # Verify the file was created
            if not output_path.exists():
                logger.error(f"Audio file was not created at expected path: {output_path}")
                raise Exception("Audio file was not created successfully")
            
            logger.info(f"Successfully downloaded audio to: {output_path}")
            return str(output_path)
            
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"yt-dlp download error for URL {url}: {error_msg}")
            
            # Check for common error cases
            if 'Video unavailable' in error_msg or 'Private video' in error_msg:
                raise ValueError("Video is unavailable or private")
            elif 'not a valid URL' in error_msg:
                raise ValueError("Invalid YouTube URL")
            else:
                raise Exception(f"Failed to download audio: {error_msg}")
                
        except Exception as e:
            logger.error(f"Unexpected error downloading audio for URL {url}: {str(e)}", exc_info=True)
            raise Exception(f"Failed to download audio: {str(e)}")
    
    def transcribe_audio(self, file_path: str) -> str:
        """
        Transcribe an audio file using faster-whisper.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            str: Full transcript of the audio
            
        Raises:
            FileNotFoundError: If the audio file doesn't exist
            Exception: If there's an error during transcription
        """
        logger.info(f"Transcribing audio file: {file_path}")
        
        # Verify file exists
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        try:
            # Initialize Whisper model (base model for balance of speed/accuracy)
            # Model will be downloaded on first use (~150MB)
            whisper_model = os.getenv("WHISPER_MODEL", "base")
            logger.info(f"Loading Whisper model ({whisper_model})")
            model = WhisperModel(whisper_model, device="cpu", compute_type="int8")
            
            # Transcribe the audio
            logger.info("Starting transcription...")
            segments, info = model.transcribe(file_path, beam_size=5)
            
            logger.info(f"Detected language: {info.language} with probability {info.language_probability}")
            
            # Combine all segments into full transcript
            transcript_parts = []
            for segment in segments:
                transcript_parts.append(segment.text)
                logger.debug(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
            
            full_transcript = " ".join(transcript_parts).strip()
            
            logger.info(f"Transcription completed. Length: {len(full_transcript)} characters")
            return full_transcript
            
        except Exception as e:
            logger.error(f"Error transcribing audio file {file_path}: {str(e)}", exc_info=True)
            raise Exception(f"Failed to transcribe audio: {str(e)}")
    
    def transcribe_video_with_cache(self, url: str) -> Dict[str, any]:
        """
        Transcribe a YouTube video with database caching.
        
        Checks the database first for an existing transcript. If found, returns it immediately.
        Otherwise, downloads audio, transcribes it, saves to database, and returns the result.
        
        Args:
            url: YouTube video URL
            
        Returns:
            dict: Contains 'url', 'title', 'transcript', and 'from_cache' keys
            
        Raises:
            ValueError: If the URL is invalid
            Exception: If there's an error during the process
        """
        logger.info(f"Transcribing video with cache: {url}")
        
        # Validate URL first
        if not self._is_valid_youtube_url(url):
            logger.warning(f"Invalid YouTube URL: {url}")
            raise ValueError("Invalid YouTube URL. Please provide a valid YouTube video URL.")
        
        # Extract video ID
        video_id = self._extract_video_id(url)
        
        # Check database if available
        if self.db_manager:
            logger.info(f"Checking database for video: {video_id}")
            cached_video = self.db_manager.get_video_by_url(url)
            
            if cached_video:
                logger.info(f"Video found in cache: {video_id}")
                return {
                    "url": url,
                    "title": cached_video.get("title", "Unknown Title"),
                    "transcript": cached_video.get("transcript_text", ""),
                    "from_cache": True
                }
            else:
                logger.info(f"Video not in cache, will transcribe: {video_id}")
        else:
            logger.warning("Database manager not available, skipping cache check")
        
        # Not in cache, proceed with transcription
        audio_path = None
        try:
            # Get video metadata
            logger.info("Fetching video metadata...")
            metadata = self.get_video_info(url)
            title = metadata.get("title", "Unknown Title")
            
            # Download audio
            logger.info("Downloading audio...")
            audio_path = self.download_audio(url)
            
            # Transcribe
            logger.info("Transcribing audio...")
            transcript = self.transcribe_audio(audio_path)
            
            # Save to database if available
            if self.db_manager:
                logger.info(f"Saving transcript to database: {video_id}")
                self.db_manager.save_video(
                    video_id=video_id,
                    youtube_url=url,
                    title=title,
                    transcript=transcript
                )
            
            # Clean up
            self._cleanup_audio_file(audio_path)
            
            logger.info(f"Successfully transcribed and cached video: {video_id}")
            return {
                "url": url,
                "title": title,
                "transcript": transcript,
                "from_cache": False
            }
            
        except Exception as e:
            # Clean up on error
            if audio_path:
                self._cleanup_audio_file(audio_path)
            logger.error(f"Error in transcribe_video_with_cache: {str(e)}", exc_info=True)
            raise

    
    def _cleanup_audio_file(self, file_path: str) -> None:
        """
        Safely delete a temporary audio file.
        
        Args:
            file_path: Path to the audio file to delete
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary audio file: {file_path}")
            else:
                logger.warning(f"Audio file not found for cleanup: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up audio file {file_path}: {str(e)}", exc_info=True)
