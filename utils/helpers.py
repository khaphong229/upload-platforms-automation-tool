import os
import re
import shutil
import logging
import tempfile
from pathlib import Path
from slugify import slugify
from config import TEMP_DIR

logger = logging.getLogger(__name__)

def sanitize_filename(filename):
    """
    Sanitize a filename to make it safe for all operating systems
    
    Args:
        filename (str): The filename to sanitize
        
    Returns:
        str: A sanitized filename
    """
    # Use slugify to handle most of the sanitization
    sanitized = slugify(filename, separator="_")
    
    # Remove any remaining problematic characters
    sanitized = re.sub(r'[^\w\-_.]', '_', sanitized)
    
    # Ensure the filename isn't too long
    if len(sanitized) > 200:
        sanitized = sanitized[:197] + "..."
    
    return sanitized

def create_temp_dir(prefix="temp_"):
    """
    Create a temporary directory
    
    Args:
        prefix (str): Prefix for the directory name
        
    Returns:
        Path: Path to the created directory
    """
    # Ensure the base temp directory exists
    TEMP_DIR.mkdir(exist_ok=True, parents=True)
    
    # Create a unique subdirectory
    temp_dir = TEMP_DIR / f"{prefix}{next(tempfile._get_candidate_names())}"
    temp_dir.mkdir(exist_ok=True)
    
    logger.info(f"Created temporary directory: {temp_dir}")
    return temp_dir

def clean_temp_dir(dir_path=None, older_than_days=1):
    """
    Clean temporary directories
    
    Args:
        dir_path (Path, optional): Specific directory to clean, or None to clean all temp dirs
        older_than_days (int): Remove directories older than this many days
        
    Returns:
        int: Number of directories removed
    """
    import time
    from datetime import datetime, timedelta
    
    if dir_path:
        # Clean specific directory
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)
            logger.info(f"Removed temporary directory: {dir_path}")
            return 1
        return 0
    
    # Clean all old directories in the temp dir
    if not TEMP_DIR.exists():
        return 0
    
    count = 0
    cutoff_time = datetime.now() - timedelta(days=older_than_days)
    
    for item in TEMP_DIR.iterdir():
        if not item.is_dir():
            continue
        
        # Check if the directory is old enough to delete
        mtime = datetime.fromtimestamp(item.stat().st_mtime)
        if mtime < cutoff_time:
            try:
                shutil.rmtree(item, ignore_errors=True)
                logger.info(f"Removed old temporary directory: {item}")
                count += 1
            except Exception as e:
                logger.error(f"Error removing directory {item}: {str(e)}")
    
    return count

def extract_video_id_from_url(url):
    """
    Extract the video ID from a YouTube URL
    
    Args:
        url (str): YouTube URL
        
    Returns:
        str: YouTube video ID or None if not found
    """
    # Regular expressions for different YouTube URL formats
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def format_file_size(size_bytes):
    """
    Format file size in human-readable format
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Formatted file size
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB" 