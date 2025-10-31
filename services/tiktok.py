"""
TikTok Upload Service
Wrapper around TikTokAutoUploader functionality
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

# Add TikTokAutoUploader to path - try multiple possible locations
TIKTOK_UPLOADER_PATH = None
possible_paths = [
    Path(__file__).parent.parent.parent / "TiktokAutoUploader",  # E:\Workspace\Tool\TiktokAutoUploader
    Path(r"E:\Workspace\Tool\TiktokAutoUploader"),  # Absolute path
]

for path in possible_paths:
    if path.exists() and (path / "tiktok_uploader").exists():
        TIKTOK_UPLOADER_PATH = path
        # Add to Python path if not already there
        str_path = str(TIKTOK_UPLOADER_PATH)
        if str_path not in sys.path:
            sys.path.insert(0, str_path)
        break

logger = logging.getLogger(__name__)


class TikTokService:
    """Service for managing TikTok uploads"""

    def __init__(self):
        """Initialize TikTok service"""
        self.tiktok_available = self._check_availability()
        if self.tiktok_available:
            self._initialize_tiktok()

    def _check_availability(self) -> bool:
        """Check if TikTok uploader is available"""
        try:
            # Check if path was found
            if TIKTOK_UPLOADER_PATH is None:
                logger.warning("TikTok uploader path not found in any expected location")
                return False

            if not TIKTOK_UPLOADER_PATH.exists():
                logger.warning(f"TikTok uploader not found at: {TIKTOK_UPLOADER_PATH}")
                return False

            # Check if tiktok_uploader package exists
            tiktok_pkg = TIKTOK_UPLOADER_PATH / "tiktok_uploader"
            if not tiktok_pkg.exists():
                logger.warning(f"tiktok_uploader package not found in: {TIKTOK_UPLOADER_PATH}")
                return False

            # Try importing core modules only (not Video which needs moviepy)
            import tiktok_uploader.tiktok
            import tiktok_uploader.Config
            import tiktok_uploader.cookies

            logger.info("TikTok uploader modules loaded successfully")
            return True
        except ImportError as e:
            logger.error(f"Failed to import TikTok uploader: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking TikTok availability: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _initialize_tiktok(self):
        """Initialize TikTok modules"""
        try:
            from tiktok_uploader.tiktok import upload_video, login
            from tiktok_uploader.Config import Config
            from tiktok_uploader.cookies import load_cookies_from_file

            self.upload_video = upload_video
            self.login = login
            self.Config = Config
            self.load_cookies = load_cookies_from_file

            # Note: We skip importing Video class as it requires moviepy which may have dependency issues
            # Users will provide pre-processed video files directly

            # Load config
            config_path = TIKTOK_UPLOADER_PATH / "config.txt"
            if config_path.exists():
                self.Config.load(str(config_path))
                self.config = self.Config.get()
            else:
                logger.warning("config.txt not found, using defaults")
                self.config = None

        except Exception as e:
            logger.error(f"Failed to initialize TikTok modules: {e}")
            self.tiktok_available = False

    def is_available(self) -> bool:
        """Check if TikTok service is available"""
        return self.tiktok_available

    def get_saved_accounts(self) -> List[str]:
        """Get list of saved TikTok accounts"""
        if not self.tiktok_available:
            return []

        try:
            cookies_dir = self.get_cookies_dir()
            if not cookies_dir.exists():
                cookies_dir.mkdir(parents=True, exist_ok=True)
                return []

            accounts = []
            for file in cookies_dir.glob("tiktok_session-*.cookie"):
                # Extract account name from filename
                account_name = file.stem.replace("tiktok_session-", "")
                accounts.append(account_name)

            return sorted(accounts)
        except Exception as e:
            logger.error(f"Error getting saved accounts: {e}")
            return []

    def login_account(self, account_name: str) -> Tuple[bool, str]:
        """
        Login to TikTok account (opens browser)

        Args:
            account_name: Name to save the session as

        Returns:
            (success, message)
        """
        if not self.tiktok_available:
            return False, "TikTok uploader not available"

        try:
            logger.info(f"Starting login for account: {account_name}")
            session_id = self.login(account_name)

            if session_id:
                return True, f"Login successful! Session ID: {session_id[:10]}..."
            else:
                return False, "Login failed - no session ID received"

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, f"Login error: {str(e)}"

    def upload(
        self,
        account_name: str,
        video_path: str,
        title: str,
        schedule_time: int = 0,
        allow_comment: bool = True,
        allow_duet: bool = False,
        allow_stitch: bool = False,
        is_private: bool = False,
        proxy: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Upload video to TikTok

        Args:
            account_name: Saved account name
            video_path: Path to video file
            title: Video caption/title (max 2200 chars)
            schedule_time: Schedule time in seconds (0=now, 900-864000)
            allow_comment: Allow comments
            allow_duet: Allow duets
            allow_stitch: Allow stitch
            is_private: Private video (cannot be scheduled)
            proxy: Proxy URL (optional)

        Returns:
            (success, message)
        """
        if not self.tiktok_available:
            return False, "TikTok uploader not available"

        # Validate
        video_file = Path(video_path)
        if not video_file.exists():
            return False, f"Video file not found: {video_path}"

        if len(title) > 2200:
            return False, f"Title too long ({len(title)} chars, max 2200)"

        if is_private and schedule_time > 0:
            return False, "Private videos cannot be scheduled"

        if schedule_time > 0 and (schedule_time < 900 or schedule_time > 864000):
            return False, "Schedule time must be between 900 (15min) and 864000 (10 days) seconds"

        # Check if account exists
        accounts = self.get_saved_accounts()
        if account_name not in accounts:
            return False, f"Account '{account_name}' not found. Please login first."

        try:
            logger.info(f"Uploading video to TikTok account: {account_name}")
            logger.info(f"Video: {video_file.name}, Title: {title[:50]}...")

            success = self.upload_video(
                session_user=account_name,
                video=str(video_path),
                title=title,
                schedule_time=schedule_time,
                allow_comment=1 if allow_comment else 0,
                allow_duet=1 if allow_duet else 0,
                allow_stitch=1 if allow_stitch else 0,
                visibility_type=1 if is_private else 0,
                brand_organic_type=0,
                branded_content_type=0,
                ai_label=0,
                proxy=proxy
            )

            if success:
                schedule_msg = ""
                if schedule_time > 0:
                    hours = schedule_time // 3600
                    schedule_msg = f" (scheduled in {hours} hours)"
                return True, f"Video uploaded successfully{schedule_msg}!"
            else:
                return False, "Upload failed - check TikTok API response"

        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False, f"Upload error: {str(e)}"

    def delete_account(self, account_name: str) -> Tuple[bool, str]:
        """
        Delete saved account cookies

        Args:
            account_name: Account name to delete

        Returns:
            (success, message)
        """
        if not self.tiktok_available:
            return False, "TikTok uploader not available"

        try:
            cookies_dir = self.get_cookies_dir()
            cookie_file = cookies_dir / f"tiktok_session-{account_name}.cookie"

            if not cookie_file.exists():
                return False, f"Account '{account_name}' not found"

            cookie_file.unlink()
            logger.info(f"Deleted account: {account_name}")
            return True, f"Account '{account_name}' deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            return False, f"Error deleting account: {str(e)}"

    def validate_video(self, video_path: str) -> Tuple[bool, str]:
        """
        Validate video file for TikTok upload

        Args:
            video_path: Path to video file

        Returns:
            (valid, message)
        """
        video_file = Path(video_path)

        if not video_file.exists():
            return False, "Video file not found"

        # Check file extension
        valid_extensions = {'.mp4', '.avi', '.mov', '.webm', '.mkv', '.flv'}
        if video_file.suffix.lower() not in valid_extensions:
            return False, f"Invalid video format. Supported: {', '.join(valid_extensions)}"

        # Check file size (TikTok max: ~287MB for 3min, ~1.8GB for 10min)
        size_mb = video_file.stat().st_size / (1024 * 1024)
        if size_mb > 1800:
            return False, f"Video too large ({size_mb:.1f}MB, max 1800MB)"

        return True, f"Video valid ({size_mb:.1f}MB)"

    def get_cookies_dir(self) -> Path:
        """Get cookies directory path"""
        if TIKTOK_UPLOADER_PATH is None:
            return Path("./CookiesDir")
        return TIKTOK_UPLOADER_PATH / "CookiesDir"

    def get_videos_dir(self) -> Path:
        """Get videos directory path"""
        if TIKTOK_UPLOADER_PATH is None:
            return Path("./VideosDirPath")
        return TIKTOK_UPLOADER_PATH / "VideosDirPath"
