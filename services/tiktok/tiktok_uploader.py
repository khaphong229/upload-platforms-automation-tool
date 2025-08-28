import logging
import time
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from config import TIKTOK_USERNAME, TIKTOK_PASSWORD

logger = logging.getLogger(__name__)

class TikTokUploader:
    """Service to upload videos to TikTok using Selenium automation"""
    
    def __init__(self, username=None, password=None, headless=False):
        self.username = username or TIKTOK_USERNAME
        self.password = password or TIKTOK_PASSWORD
        self.headless = headless
        self.driver = None
    
    def _setup_driver(self):
        """Set up and return a configured Chrome WebDriver"""
        logger.info("Setting up Chrome WebDriver")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        
        # Set up user agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        # Set up Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set page load timeout
        driver.set_page_load_timeout(60)
        
        return driver
    
    def login(self):
        """Log in to TikTok"""
        logger.info("Logging in to TikTok")
        
        if not self.driver:
            self.driver = self._setup_driver()
        
        try:
            # Navigate to TikTok login page
            self.driver.get("https://www.tiktok.com/login")
            
            # Wait for login page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//form[contains(@class, 'login-form')]"))
            )
            
            # Click on "Use phone / email / username" option if available
            try:
                use_email_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Use phone / email / username')]"))
                )
                use_email_btn.click()
                time.sleep(2)
            except TimeoutException:
                logger.info("Already on email login form")
            
            # Enter username
            username_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@name='username' or @placeholder='Email or username']"))
            )
            username_field.clear()
            username_field.send_keys(self.username)
            time.sleep(1)
            
            # Enter password
            password_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='password']"))
            )
            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(1)
            
            # Click login button
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            login_button.click()
            
            # Wait for login to complete (check for upload button or profile icon)
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'upload-icon') or contains(@class, 'profile-icon')]"))
            )
            
            logger.info("Successfully logged in to TikTok")
            return True
            
        except Exception as e:
            logger.error(f"Error logging in to TikTok: {str(e)}")
            # Take screenshot for debugging
            self.driver.save_screenshot("tiktok_login_error.png")
            return False
    
    def upload_video(self, video_path, caption, comment=None):
        """
        Upload a video to TikTok
        
        Args:
            video_path (str): Path to the video file
            caption (str): Caption for the video
            comment (str, optional): Comment to add to the video after upload
            
        Returns:
            dict: Information about the uploaded video including URL
        """
        logger.info(f"Uploading video: {video_path}")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if not self.driver:
            self.login()
        
        try:
            # Navigate to upload page
            self.driver.get("https://www.tiktok.com/upload")
            
            # Wait for upload page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'upload-container')]"))
            )
            
            # Find file input and upload video
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(os.path.abspath(video_path))
            
            # Wait for video to be processed
            WebDriverWait(self.driver, 60).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'video-preview')]"))
            )
            
            # Enter caption
            caption_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'caption-input')]/textarea"))
            )
            caption_field.clear()
            caption_field.send_keys(caption)
            
            # Click post button
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Post') or contains(@class, 'submit-button')]"))
            )
            post_button.click()
            
            # Wait for upload to complete
            WebDriverWait(self.driver, 120).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Your video is being uploaded to TikTok')]"))
            )
            
            # Wait for upload success message
            WebDriverWait(self.driver, 180).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Your video is now published')]"))
            )
            
            # Get the video URL if available
            video_url = None
            try:
                video_link = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'View')]"))
                )
                video_url = video_link.get_attribute("href")
            except:
                logger.warning("Could not get video URL")
            
            # Add comment if provided
            if comment and video_url:
                self._add_comment(video_url, comment)
            
            logger.info(f"Successfully uploaded video to TikTok: {video_url}")
            return {
                'url': video_url,
                'caption': caption,
                'status': 'published'
            }
            
        except Exception as e:
            logger.error(f"Error uploading video to TikTok: {str(e)}")
            # Take screenshot for debugging
            self.driver.save_screenshot("tiktok_upload_error.png")
            raise
    
    def _add_comment(self, video_url, comment):
        """Add a comment to a TikTok video"""
        logger.info(f"Adding comment to video: {video_url}")
        
        try:
            # Navigate to video page
            self.driver.get(video_url)
            
            # Wait for video page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'comment-input')]"))
            )
            
            # Enter comment
            comment_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'comment-input')]/input"))
            )
            comment_field.clear()
            comment_field.send_keys(comment)
            
            # Submit comment
            comment_field.send_keys(Keys.ENTER)
            
            # Wait for comment to be posted
            time.sleep(5)
            
            logger.info("Successfully added comment to video")
            return True
            
        except Exception as e:
            logger.error(f"Error adding comment to video: {str(e)}")
            return False
    
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("WebDriver closed") 