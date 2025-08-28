import os
import logging
import yt_dlp
from pathlib import Path
from config import DOWNLOAD_DIR

logger = logging.getLogger(__name__)

class YouTubeDownloader:
    """Service to download videos from YouTube"""
    
    def __init__(self, download_dir=None):
        self.download_dir = Path(download_dir) if download_dir else DOWNLOAD_DIR
        self.download_dir.mkdir(exist_ok=True, parents=True)
    
    def download_video(self, url, output_filename=None):
        """
        Download a video from YouTube
        
        Args:
            url (str): YouTube video URL
            output_filename (str, optional): Custom filename for the downloaded video
            
        Returns:
            dict: Information about the downloaded video including path, title, etc.
        """
        logger.info(f"Downloading video from {url}")
        
        # Set download options
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Prefer mp4 format
            'outtmpl': str(self.download_dir / (output_filename or '%(title)s.%(ext)s')),
            'noplaylist': True,
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
        }
        
        try:
            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Get video details
                video_info = {
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'upload_date': info.get('upload_date', ''),
                }
                
                # Get the downloaded file path
                if output_filename:
                    filename = output_filename
                    if '.' not in filename:
                        filename += f".{info['ext']}"
                else:
                    filename = ydl.prepare_filename(info)
                
                file_path = Path(filename)
                
                video_info['file_path'] = str(file_path)
                video_info['file_size'] = file_path.stat().st_size if file_path.exists() else 0
                
                logger.info(f"Successfully downloaded video: {video_info['title']}")
                return video_info
                
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise
    
    def get_video_info(self, url):
        """
        Get information about a YouTube video without downloading it
        
        Args:
            url (str): YouTube video URL
            
        Returns:
            dict: Information about the video
        """
        logger.info(f"Getting info for video: {url}")
        
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                video_info = {
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'upload_date': info.get('upload_date', ''),
                }
                
                logger.info(f"Successfully retrieved video info: {video_info['title']}")
                return video_info
                
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise 