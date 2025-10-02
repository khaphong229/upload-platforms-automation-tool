"""
Enhanced TikTok Uploader with improved error handling and features.
"""
import os
import time
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum, auto
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)

class UploadStatus(Enum):
    PENDING = auto()
    UPLOADING = auto()
    PROCESSING = auto()
    PUBLISHED = auto()
    FAILED = auto()
    SCHEDULED = auto()

@dataclass
class UploadResult:
    success: bool
    message: str
    video_url: str = ""
    status: UploadStatus = UploadStatus.PENDING
    profile: str = ""
    timestamp: float = 0.0

class EnhancedTikTokUploader:
    """Enhanced TikTok uploader with better error handling and features."""
    
    def __init__(self, config_path=None):
        """Initialize the uploader with configuration."""
        self.driver = None
        self.wait = None
        self.current_profile = None
        self.config_path = config_path or Path.home() / '.tiktok_uploader' / 'config.json'
        self.config = self.load_config()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Ensure directories exist
        self.profiles_dir = Path(self.config_path).parent / 'profiles'
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> dict:
        """Load configuration from file."""
        config_path = Path(self.config_path)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                print(f"Warning: Config file is corrupted ({e}), creating a new one")
        
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        return {
            "profiles": {},
            "default_hashtags": ["viral", "fyp", "foryoupage"],
            "max_retries": 3,
            "headless": False
        }
    
    def save_config(self):
        """Save configuration to file."""
        try:
            config_path = Path(self.config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def create_driver(self, profile_name=None):
        """Create new Chrome driver instance with profile"""
        options = Options()
        
        # Add basic options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-notifications")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Add profile path if specified
        if profile_name and profile_name in self.config.get("profiles", {}):
            profile_path = self.config["profiles"][profile_name]["path"]
            if Path(profile_path).exists():
                options.add_argument(f"--user-data-dir={profile_path}")
                self.logger.info(f"Using profile path: {profile_path}")

        try:
            # Try to create driver with webdriver manager
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
            except:
                # Fallback to system chromedriver
                service = Service()
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_window_size(1200, 800)
            return driver
            
        except Exception as e:
            self.logger.error(f"Failed to create driver: {str(e)}")
            raise Exception(f"Failed to create Chrome driver: {str(e)}")
    
    def get_profiles(self) -> List[str]:
        """Get list of available profiles."""
        return list(self.config.get("profiles", {}).keys())
    
    def add_profile(self, profile_name: str) -> bool:
        """Add a new profile."""
        if not profile_name or not isinstance(profile_name, str):
            raise ValueError("Profile name must be a non-empty string")
            
        profile_name = profile_name.strip()
        if not profile_name:
            raise ValueError("Profile name cannot be empty")
            
        if profile_name in self.config.get("profiles", {}):
            self.logger.warning(f"Profile '{profile_name}' already exists")
            return False
            
        profile_path = self.profiles_dir / profile_name
        profile_path.mkdir(exist_ok=True)
        
        if "profiles" not in self.config:
            self.config["profiles"] = {}
            
        self.config["profiles"][profile_name] = {
            "path": str(profile_path),
            "created_at": time.time(),
            "last_used": 0,
            "status": "inactive"
        }
        
        self.save_config()
        self.logger.info(f"Added new profile: {profile_name}")
        return True
    
    def remove_profile(self, profile_name: str) -> bool:
        """Remove a profile and its data."""
        if profile_name not in self.config.get("profiles", {}):
            self.logger.warning(f"Profile '{profile_name}' not found")
            return False
            
        # Remove profile directory
        try:
            profile_path = Path(self.config["profiles"][profile_name]["path"])
            if profile_path.exists():
                shutil.rmtree(profile_path, ignore_errors=True)
        except Exception as e:
            self.logger.warning(f"Could not remove profile directory: {e}")
        
        # Remove from config
        del self.config["profiles"][profile_name]
        self.save_config()
        
        self.logger.info(f"Removed profile: {profile_name}")
        return True
    
    def login(self, profile_name):
        """Improved login handling"""
        if not profile_name:
            raise ValueError("Profile name is required")
            
        try:
            # Close existing session
            self.close()
            
            # Create new driver
            self.driver = self.create_driver(profile_name)
            self.wait = WebDriverWait(self.driver, 30)
            self.current_profile = profile_name

            # Navigate to TikTok
            self.logger.info(f"Navigating to TikTok for profile: {profile_name}")
            self.driver.get("https://www.tiktok.com")
            time.sleep(3)

            # Check if already logged in by going to upload page
            self.driver.get("https://www.tiktok.com/upload")
            time.sleep(5)

            # Check if we're on the upload page (logged in) or redirected to login
            current_url = self.driver.current_url.lower()
            if "login" in current_url:
                self.logger.info(f"Login required for profile: {profile_name}")
                # Don't close driver - let user log in manually
                return False
            elif "upload" in current_url:
                # Check for upload elements to confirm we're logged in
                try:
                    # Look for file input or upload area
                    upload_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                        "input[type='file'], [data-e2e*='upload'], .upload-btn, .upload-area")
                    if upload_elements:
                        self.logger.info(f"Successfully logged in for profile: {profile_name}")
                        return True
                except Exception as e:
                    self.logger.warning(f"Could not verify login elements: {e}")
                
                # Fallback check - if we're on upload page and no login form, assume success
                login_forms = self.driver.find_elements(By.CSS_SELECTOR, 
                    "form[action*='login'], .login-form, [data-e2e*='login']")
                if not login_forms:
                    self.logger.info(f"Login successful for profile: {profile_name} (fallback check)")
                    return True
            
            self.logger.warning(f"Unclear login status for profile: {profile_name}")
            return False

        except Exception as e:
            self.logger.error(f"Login error for {profile_name}: {str(e)}")
            # Don't close driver on error - might be temporary
            return False
    
    def upload_video(
        self,
        video_path: str,
        caption: str = "",
        hashtags: List[str] = None,
        profile_name: str = None,
        schedule_time: int = None
    ) -> UploadResult:
        """
        Upload a video to TikTok.
        
        Args:
            video_path: Path to the video file
            caption: Video caption
            hashtags: List of hashtags
            profile_name: Profile to use for upload
            schedule_time: Unix timestamp for scheduled upload (optional)
            
        Returns:
            UploadResult with status and details
        """
        result = UploadResult(
            success=False,
            message="Upload not started",
            status=UploadStatus.PENDING,
            timestamp=time.time()
        )
        
        try:
            # Validate video
            video_path = Path(video_path)
            if not video_path.exists():
                result.message = f"Video file not found: {video_path}"
                result.status = UploadStatus.FAILED
                return result
            
            # Prepare caption with hashtags
            if not hashtags:
                hashtags = self.config.get("default_hashtags", [])
                
            caption = self._prepare_caption(caption, hashtags)
            
            # Login if not already
            if not self.driver or (profile_name and profile_name != self.current_profile):
                if not profile_name:
                    profiles = self.get_profiles()
                    if not profiles:
                        result.message = "No profiles available. Please add a profile first."
                        result.status = UploadStatus.FAILED
                        return result
                    profile_name = profiles[0]
                
                if not self.login(profile_name):
                    result.message = f"Failed to login with profile: {profile_name}"
                    result.status = UploadStatus.FAILED
                    return result
            
            result.profile = self.current_profile
            
            # Start upload process
            result.status = UploadStatus.UPLOADING
            self.logger.info(f"Starting upload: {video_path.name}")
            
            # Find and click upload button
            upload_btn = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='upload-input']"))
            )
            upload_btn.send_keys(str(video_path.absolute()))
            
            # Wait for upload to complete
            self.wait.until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".uploading-status"))
            )
            
            # Add caption
            caption_area = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='video-title']"))
            )
            caption_area.clear()
            caption_area.send_keys(caption)
            
            # Handle scheduling if needed
            if schedule_time:
                self._schedule_upload(schedule_time)
                result.status = UploadStatus.SCHEDULED
                result.message = "Video scheduled successfully"
            else:
                # Click post button
                post_btn = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-e2e='btn-post']"))
                )
                post_btn.click()
                
                # Wait for upload to complete
                self.wait.until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".posting-status"))
                )
                
                # Get video URL if available
                try:
                    video_url = self.driver.current_url
                    if "/video/" in video_url:
                        result.video_url = video_url
                except:
                    pass
                
                result.status = UploadStatus.PUBLISHED
                result.message = "Video published successfully"
            
            result.success = True
            self.logger.info(f"Upload completed: {video_path.name}")
            
        except Exception as e:
            result.status = UploadStatus.FAILED
            result.message = f"Upload failed: {str(e)}"
            self.logger.error(f"Upload error: {str(e)}", exc_info=True)
            
            # Take screenshot on error
            if self.driver:
                try:
                    self.driver.save_screenshot("upload_error.png")
                except:
                    pass
        
        return result
    
    def _prepare_caption(self, caption: str, hashtags: List[str]) -> str:
        """Prepare caption with hashtags."""
        if not caption:
            caption = ""
            
        # Add hashtags if not already present
        for tag in hashtags:
            if not tag.startswith("#"):
                tag = f"#{tag}"
            if tag not in caption:
                caption += f" {tag}"
                
        return caption.strip()
    
    def _schedule_upload(self, schedule_time: int):
        """Schedule an upload for a future time."""
        try:
            # Click schedule button
            schedule_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-e2e='schedule-btn']"))
            )
            schedule_btn.click()
            
            # Set schedule time (implementation depends on TikTok's UI)
            # This is a placeholder - actual implementation would need to interact with the date/time picker
            self.logger.warning("Scheduling is not fully implemented yet")
            
        except Exception as e:
            self.logger.error(f"Failed to schedule upload: {str(e)}")
            raise
    
    def close(self):
        """Close the browser and clean up."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None
                self.wait = None
                self.current_profile = None
    
    def __del__(self):
        """Ensure resources are cleaned up."""
        self.close()

# Alias for backward compatibility
TikTokUploader = EnhancedTikTokUploader
