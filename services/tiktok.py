"""
TikTok Upload Service
Wrapper around TikTokAutoUploader functionality with lazy loading
"""
import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


def sanitize_account_name(account_name: str) -> str:
    """
    Sanitize account name for use in filenames
    Removes spaces and special characters

    Args:
        account_name: Original account name

    Returns:
        Sanitized account name safe for filenames
    """
    # Replace spaces with underscores
    sanitized = account_name.replace(' ', '_')
    # Remove any characters that are not alphanumeric, underscore, or hyphen
    sanitized = re.sub(r'[^\w\-]', '_', sanitized)
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized


# Bilingual error messages (English / Vietnamese)
ERROR_MESSAGES = {
    "path_not_found": {
        "en": "TikTok uploader path not found in any expected location",
        "vi": "Không tìm thấy đường dẫn TikTok uploader ở vị trí mong đợi"
    },
    "package_not_found": {
        "en": "tiktok_uploader package not found in: {path}",
        "vi": "Không tìm thấy gói tiktok_uploader trong: {path}"
    },
    "file_missing": {
        "en": "Required file missing: {file}",
        "vi": "Thiếu tệp bắt buộc: {file}"
    },
    "import_failed": {
        "en": "Failed to import TikTok modules: {error}\n\nPossible solutions:\n1. Install dependencies: pip install undetected-chromedriver beautifulsoup4 moviepy requests-auth-aws-sigv4\n2. Check TikTokAutoUploader exists at: {path}\n3. Restart the application",
        "vi": "Không thể nhập module TikTok: {error}\n\nGiải pháp có thể:\n1. Cài đặt các gói phụ thuộc: pip install undetected-chromedriver beautifulsoup4 moviepy requests-auth-aws-sigv4\n2. Kiểm tra TikTokAutoUploader tồn tại tại: {path}\n3. Khởi động lại ứng dụng"
    },
    "modules_not_loaded": {
        "en": "TikTok uploader modules could not be loaded. Check dependencies are installed.",
        "vi": "Không thể tải module TikTok uploader. Kiểm tra các gói phụ thuộc đã được cài đặt."
    },
    "login_failed": {
        "en": "Login failed - no session ID received",
        "vi": "Đăng nhập thất bại - không nhận được session ID"
    },
    "login_error": {
        "en": "Login error: {error}",
        "vi": "Lỗi đăng nhập: {error}"
    },
    "video_not_found": {
        "en": "Video file not found: {path}",
        "vi": "Không tìm thấy tệp video: {path}"
    },
    "title_too_long": {
        "en": "Title too long ({length} chars, max 2200)",
        "vi": "Tiêu đề quá dài ({length} ký tự, tối đa 2200)"
    },
    "private_schedule_error": {
        "en": "Private videos cannot be scheduled",
        "vi": "Video riêng tư không thể lên lịch"
    },
    "schedule_time_error": {
        "en": "Schedule time must be between 900 (15min) and 864000 (10 days) seconds",
        "vi": "Thời gian lên lịch phải từ 900 (15 phút) đến 864000 (10 ngày) giây"
    },
    "account_not_found": {
        "en": "Account '{account}' not found. Please login first.",
        "vi": "Tài khoản '{account}' không tìm thấy. Vui lòng đăng nhập trước."
    },
    "upload_failed": {
        "en": "Upload failed - check TikTok API response",
        "vi": "Tải lên thất bại - kiểm tra phản hồi API TikTok"
    },
    "upload_error": {
        "en": "Upload error: {error}",
        "vi": "Lỗi tải lên: {error}"
    },
    "upload_success": {
        "en": "Video uploaded successfully{schedule}!",
        "vi": "Video đã được tải lên thành công{schedule}!"
    },
    "login_success": {
        "en": "Login successful! Session ID: {session}...",
        "vi": "Đăng nhập thành công! Session ID: {session}..."
    }
}


def get_message(key: str, lang: str = "en", **kwargs) -> str:
    """Get bilingual error message"""
    msg_dict = ERROR_MESSAGES.get(key, {})
    msg = msg_dict.get(lang, msg_dict.get("en", key))
    return msg.format(**kwargs) if kwargs else msg


class TikTokService:
    """Service for managing TikTok uploads with lazy loading"""

    def __init__(self, language: str = "en"):
        """
        Initialize TikTok service (lazy loading - no imports yet)

        Args:
            language: Language for messages ("en" or "vi")
        """
        self._uploader_path = None
        self._modules_loaded = False
        self._availability_checked = False
        self._tiktok_available = False
        self._language = language  # Default language for error messages

        # These will be populated on first use
        self.upload_video = None
        self.login = None
        self.Config = None
        self.load_cookies = None
        self.config = None

    def set_language(self, language: str):
        """Set language for error messages"""
        self._language = language

    def _msg(self, key: str, **kwargs) -> str:
        """Get message in current language"""
        return get_message(key, self._language, **kwargs)

    def _find_uploader_path(self) -> Optional[Path]:
        """Find TikTokAutoUploader path"""
        if self._uploader_path is not None:
            return self._uploader_path

        possible_paths = [
            Path(__file__).parent.parent.parent / "TiktokAutoUploader",
            Path(r"E:\Workspace\Tool\TiktokAutoUploader"),
        ]

        for path in possible_paths:
            if path.exists() and (path / "tiktok_uploader").exists():
                self._uploader_path = path
                # Add to Python path if not already there
                str_path = str(self._uploader_path)
                if str_path not in sys.path:
                    sys.path.insert(0, str_path)
                logger.info(f"Found TikTokAutoUploader at: {path}")
                return self._uploader_path

        logger.warning("TikTokAutoUploader path not found")
        return None

    def _check_availability(self) -> bool:
        """Check if TikTok uploader is available (lazy check)"""
        if self._availability_checked:
            return self._tiktok_available

        self._availability_checked = True

        try:
            # Find path first
            uploader_path = self._find_uploader_path()
            if uploader_path is None:
                msg = self._msg("path_not_found")
                logger.warning(msg)
                self._tiktok_available = False
                return False

            # Check if tiktok_uploader package exists
            tiktok_pkg = uploader_path / "tiktok_uploader"
            if not tiktok_pkg.exists():
                msg = self._msg("package_not_found", path=uploader_path)
                logger.warning(msg)
                self._tiktok_available = False
                return False

            # Try a minimal import test to verify it can be imported
            # Don't actually import yet - just check if the files exist
            required_files = [
                tiktok_pkg / "tiktok.py",
                tiktok_pkg / "Config.py",
                tiktok_pkg / "cookies.py",
            ]

            for file in required_files:
                if not file.exists():
                    msg = self._msg("file_missing", file=file)
                    logger.warning(msg)
                    self._tiktok_available = False
                    return False

            logger.info("TikTok uploader appears to be available (lazy check)")
            self._tiktok_available = True
            return True

        except Exception as e:
            logger.error(f"Error checking TikTok availability: {e}")
            self._tiktok_available = False
            return False

    def _ensure_modules_loaded(self) -> bool:
        """Ensure TikTok modules are loaded (lazy loading)"""
        if self._modules_loaded:
            return True

        if not self._check_availability():
            return False

        try:
            logger.info("Loading TikTok modules (lazy loading)...")

            # NOW we actually import (only when needed)
            from tiktok_uploader.tiktok import upload_video, login
            from tiktok_uploader.Config import Config
            from tiktok_uploader.cookies import load_cookies_from_file

            self.upload_video = upload_video
            self.login = login
            self.Config = Config
            self.load_cookies = load_cookies_from_file

            # Load config using the static load method
            config_path = self._uploader_path / "config.txt"
            if config_path.exists():
                try:
                    # Use the static load method (singleton pattern)
                    self.config = Config.load(str(config_path))
                    logger.info(f"Config loaded from: {config_path}")
                except Exception as e:
                    logger.warning(f"Failed to load config: {e}, using defaults")
                    # Get default config instance
                    self.config = Config.get()
            else:
                logger.warning("config.txt not found, using defaults")
                # Get default config instance
                self.config = Config.get()

            self._modules_loaded = True
            logger.info("TikTok modules loaded successfully!")
            return True

        except ImportError as e:
            error_detail = str(e)
            msg = self._msg("import_failed", error=error_detail, path=self._uploader_path or "Unknown")
            logger.error(msg)

            # Log detailed traceback for debugging
            import traceback
            logger.error("Detailed traceback:")
            logger.error(traceback.format_exc())

            # Store the detailed error for UI display
            self._last_error = msg
            self._tiktok_available = False
            return False
        except Exception as e:
            logger.error(f"Failed to initialize TikTok modules: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self._last_error = str(e)
            self._tiktok_available = False
            return False

    def get_last_error(self) -> str:
        """Get the last error message (useful for debugging)"""
        return getattr(self, '_last_error', self._msg("modules_not_loaded"))

    def is_available(self) -> bool:
        """Check if TikTok service is available"""
        return self._check_availability()

    def get_saved_accounts(self) -> List[str]:
        """Get list of saved TikTok accounts"""
        if not self.is_available():
            return []

        try:
            cookies_dir = self.get_cookies_dir()
            # get_cookies_dir now ensures directory exists

            if not cookies_dir.exists():
                logger.warning(f"Cookies directory does not exist: {cookies_dir}")
                return []

            accounts = []
            for file in cookies_dir.glob("tiktok_session-*.cookie"):
                # Extract account name from filename
                account_name = file.stem.replace("tiktok_session-", "")
                accounts.append(account_name)

            logger.info(f"Found {len(accounts)} saved TikTok account(s)")
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
            (success, message) - returns bilingual message
        """
        # Load modules now if not already loaded
        if not self._ensure_modules_loaded():
            return False, self.get_last_error()

        # Sanitize account name for filename safety
        sanitized_name = sanitize_account_name(account_name)

        if not sanitized_name:
            return False, "Invalid account name. Please use alphanumeric characters only."

        # Ensure CookiesDir exists in the TikTokAutoUploader directory
        cookies_dir = self.get_cookies_dir()
        try:
            cookies_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cookies directory: {cookies_dir}")
        except Exception as e:
            logger.error(f"Failed to create cookies directory: {e}")
            return False, f"Failed to create cookies directory: {str(e)}"

        # Save current working directory
        original_cwd = os.getcwd()

        try:
            # Change to TikTokAutoUploader directory so cookies are saved there
            if self._uploader_path:
                os.chdir(str(self._uploader_path))
                logger.info(f"Changed working directory to: {self._uploader_path}")

            logger.info(f"Starting login for account: {account_name} (sanitized: {sanitized_name})")
            # Use sanitized name for login
            session_id = self.login(sanitized_name)

            if session_id:
                msg_en = get_message("login_success", "en", session=session_id[:10])
                msg_vi = get_message("login_success", "vi", session=session_id[:10])

                # Log warning if name was changed
                if sanitized_name != account_name:
                    warning = f"\n\nNote: Account name was sanitized from '{account_name}' to '{sanitized_name}' for file safety."
                    logger.warning(warning)
                    return True, f"{msg_en}\n{msg_vi}{warning}"

                return True, f"{msg_en}\n{msg_vi}"
            else:
                msg_en = get_message("login_failed", "en")
                msg_vi = get_message("login_failed", "vi")
                return False, f"{msg_en}\n{msg_vi}"

        except Exception as e:
            logger.error(f"Login error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            msg_en = get_message("login_error", "en", error=str(e))
            msg_vi = get_message("login_error", "vi", error=str(e))
            return False, f"{msg_en}\n{msg_vi}"

        finally:
            # Always restore original working directory
            os.chdir(original_cwd)
            logger.info(f"Restored working directory to: {original_cwd}")

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
        # Load modules now if not already loaded
        if not self._ensure_modules_loaded():
            return False, self.get_last_error()

        # Validate
        video_file = Path(video_path)
        if not video_file.exists():
            msg_en = get_message("video_not_found", "en", path=video_path)
            msg_vi = get_message("video_not_found", "vi", path=video_path)
            return False, f"{msg_en}\n{msg_vi}"

        if len(title) > 2200:
            msg_en = get_message("title_too_long", "en", length=len(title))
            msg_vi = get_message("title_too_long", "vi", length=len(title))
            return False, f"{msg_en}\n{msg_vi}"

        if is_private and schedule_time > 0:
            msg_en = get_message("private_schedule_error", "en")
            msg_vi = get_message("private_schedule_error", "vi")
            return False, f"{msg_en}\n{msg_vi}"

        if schedule_time > 0 and (schedule_time < 900 or schedule_time > 864000):
            msg_en = get_message("schedule_time_error", "en")
            msg_vi = get_message("schedule_time_error", "vi")
            return False, f"{msg_en}\n{msg_vi}"

        # Sanitize account name
        sanitized_name = sanitize_account_name(account_name)

        # Check if account exists (check for both original and sanitized names)
        accounts = self.get_saved_accounts()
        if account_name not in accounts and sanitized_name not in accounts:
            msg_en = get_message("account_not_found", "en", account=account_name)
            msg_vi = get_message("account_not_found", "vi", account=account_name)
            return False, f"{msg_en}\n{msg_vi}"

        # Use sanitized name if original not found
        upload_account_name = sanitized_name if sanitized_name in accounts else account_name

        # Save current working directory
        original_cwd = os.getcwd()

        try:
            # Change to TikTokAutoUploader directory so cookies are loaded from there
            if self._uploader_path:
                os.chdir(str(self._uploader_path))
                logger.info(f"Changed working directory to: {self._uploader_path}")

            logger.info(f"Uploading video to TikTok account: {account_name} (using: {upload_account_name})")
            logger.info(f"Video: {video_file.name}, Title: {title[:50]}...")

            success = self.upload_video(
                session_user=upload_account_name,
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
                schedule_msg_en = ""
                schedule_msg_vi = ""
                if schedule_time > 0:
                    hours = schedule_time // 3600
                    schedule_msg_en = f" (scheduled in {hours} hours)"
                    schedule_msg_vi = f" (đã lên lịch sau {hours} giờ)"

                msg_en = get_message("upload_success", "en", schedule=schedule_msg_en)
                msg_vi = get_message("upload_success", "vi", schedule=schedule_msg_vi)
                return True, f"{msg_en}\n{msg_vi}"
            else:
                msg_en = get_message("upload_failed", "en")
                msg_vi = get_message("upload_failed", "vi")
                return False, f"{msg_en}\n{msg_vi}"

        except ConnectionError as e:
            logger.error(f"Connection error during upload: {e}")
            msg_en = "Connection error: Network connection was interrupted. Please check your internet connection and try again."
            msg_vi = "Lỗi kết nối: Kết nối mạng bị gián đoạn. Vui lòng kiểm tra kết nối internet và thử lại."
            return False, f"{msg_en}\n{msg_vi}"
        except Exception as e:
            logger.error(f"Upload error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            msg_en = get_message("upload_error", "en", error=str(e))
            msg_vi = get_message("upload_error", "vi", error=str(e))
            return False, f"{msg_en}\n{msg_vi}"

        finally:
            # Always restore original working directory
            os.chdir(original_cwd)
            logger.info(f"Restored working directory to: {original_cwd}")

    def delete_account(self, account_name: str) -> Tuple[bool, str]:
        """
        Delete saved account cookies

        Args:
            account_name: Account name to delete

        Returns:
            (success, message)
        """
        if not self.is_available():
            return False, "TikTok uploader not available"

        try:
            cookies_dir = self.get_cookies_dir()
            # Try both original and sanitized names
            sanitized_name = sanitize_account_name(account_name)

            cookie_file = cookies_dir / f"tiktok_session-{account_name}.cookie"
            cookie_file_sanitized = cookies_dir / f"tiktok_session-{sanitized_name}.cookie"

            # Try to delete whichever exists
            deleted = False
            if cookie_file.exists():
                cookie_file.unlink()
                deleted = True
                logger.info(f"Deleted account: {account_name}")
            elif cookie_file_sanitized.exists():
                cookie_file_sanitized.unlink()
                deleted = True
                logger.info(f"Deleted account (sanitized): {sanitized_name}")

            if deleted:
                return True, f"Account '{account_name}' deleted successfully"
            else:
                return False, f"Account '{account_name}' not found"

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
        """Get cookies directory path and ensure it exists"""
        uploader_path = self._find_uploader_path()
        if uploader_path is None:
            cookies_dir = Path("./CookiesDir")
        else:
            cookies_dir = uploader_path / "CookiesDir"

        # Ensure directory exists
        try:
            cookies_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create cookies directory: {e}")

        return cookies_dir

    def get_videos_dir(self) -> Path:
        """Get videos directory path"""
        uploader_path = self._find_uploader_path()
        if uploader_path is None:
            return Path("./VideosDirPath")
        return uploader_path / "VideosDirPath"
