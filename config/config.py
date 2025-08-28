import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', './downloads'))
TEMP_DIR = Path(os.getenv('TEMP_DIR', './temp'))

# Create directories if they don't exist
DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)
TEMP_DIR.mkdir(exist_ok=True, parents=True)

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
SHORTENER_API_KEY = os.getenv('SHORTENER_API_KEY')

# Google/Blogger
BLOGGER_BLOG_ID = os.getenv('BLOGGER_BLOG_ID')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REFRESH_TOKEN = os.getenv('GOOGLE_REFRESH_TOKEN')

# TikTok
TIKTOK_USERNAME = os.getenv('TIKTOK_USERNAME')
TIKTOK_PASSWORD = os.getenv('TIKTOK_PASSWORD')
TIKTOK_SESSION_ID = os.getenv('TIKTOK_SESSION_ID')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / 'app.log', encoding='utf-8')
    ]
)

# Validate required settings
def validate_config():
    """Validate that all required configuration is present"""
    required_vars = [
        ('GEMINI_API_KEY', GEMINI_API_KEY),
        ('BLOGGER_BLOG_ID', BLOGGER_BLOG_ID),
        ('GOOGLE_CLIENT_ID', GOOGLE_CLIENT_ID),
        ('GOOGLE_CLIENT_SECRET', GOOGLE_CLIENT_SECRET),
        ('GOOGLE_REFRESH_TOKEN', GOOGLE_REFRESH_TOKEN),
        ('TIKTOK_USERNAME', TIKTOK_USERNAME),
        ('TIKTOK_PASSWORD', TIKTOK_PASSWORD),
    ]
    
    missing = [name for name, value in required_vars if not value]
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}") 