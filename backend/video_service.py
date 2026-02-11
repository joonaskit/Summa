import re
import yt_dlp
from typing import Dict, Optional
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
    
    def __init__(self):
        """Initialize the VideoService."""
        logger.info("Initializing VideoService")
        
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
