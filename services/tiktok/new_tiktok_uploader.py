import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from tiktok_uploader.upload import upload_video
from tiktok_uploader.auth import AuthBackend

logger = logging.getLogger(__name__)

class NewTikTokUploader:
    """Service to upload videos to TikTok using tiktok-uploader library"""
    
    def __init__(self, cookies_file=None, session_id=None, headless=False):
        """
        Initialize TikTok uploader with authentication
        
        Args:
            cookies_file (str): Path to cookies.txt file
            session_id (str): TikTok session ID
            headless (bool): Run browser in headless mode
        """
        self.cookies_file = cookies_file
        self.session_id = session_id
        self.headless = headless
        self.auth = None
        self.cookies_list = None

        # Prioritize authentication: 1. cookies.txt, 2. session_id
        if self.cookies_file and os.path.exists(self.cookies_file) and os.path.getsize(self.cookies_file) > 0:
            logger.info(f"Using cookies file for authentication: {self.cookies_file}")
            self.auth = True # Indicates that we have a valid auth method
        elif self.session_id:
            logger.info("Using session ID for authentication")
            self._create_cookies_list()
            self.auth = True
        else:
            logger.warning("No valid authentication method provided. Upload will likely fail.")
            logger.info("\n" + self.get_authentication_instructions())
    
    def upload_video(self, video_path, caption, comment=None, hashtags=None, schedule=None, cover=None):
        """
        Upload a video to TikTok using tiktok-uploader library
        
        Args:
            video_path (str): Path to the video file
            caption (str): Caption for the video (can include hashtags)
            comment (str, optional): Comment to add after upload
            hashtags (list, optional): List of hashtags to add
            schedule (datetime, optional): Schedule video for later
            cover (str, optional): Path to cover image
            
        Returns:
            dict: Information about the uploaded video
        """
        logger.info(f"Uploading video: {video_path}")
        logger.info(f"Caption: {caption}")
        logger.info(f"Hashtags: {hashtags}")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Validate authentication before proceeding
        if not self.auth:
            raise Exception("No authentication method available")
            
        logger.info("Authentication validated, proceeding with upload...")
        
        try:
            # Prepare description with hashtags
            description = caption
            if hashtags:
                hashtag_str = " ".join([f"#{tag.strip('#')}" for tag in hashtags])
                description = f"{caption} {hashtag_str}"
            
            logger.info(f"Final description: {description}")
            
            # Prepare upload parameters according to official API
            upload_params = {
                'description': description,
                'browser': 'chrome',
                'headless': self.headless,
                'comment': True,  # Allow comments
                'stitch': True,   # Allow stitches
                'duet': True      # Allow duets
            }
            
            # Add authentication - prioritize cookies file
            if self.cookies_file and os.path.exists(self.cookies_file) and os.path.getsize(self.cookies_file) > 0:
                logger.info(f"Using cookies file: {self.cookies_file}")
                upload_params['cookies'] = self.cookies_file
            elif self.cookies_list:
                logger.info("Using cookies_list for authentication")
                upload_params['cookies_list'] = self.cookies_list
            else:
                logger.error("Authentication not initialized. Cannot upload.")
                raise Exception("TikTok authentication failed. Please provide cookies.txt or a session ID.")
                
            logger.info("Authentication parameters added successfully")
            
            # Add optional parameters
            if schedule:
                upload_params['schedule'] = schedule
            if cover:
                upload_params['cover'] = cover
            
            # Upload video
            logger.info("Starting video upload to TikTok...")
            logger.info(f"Upload parameters: {upload_params}")
            
            try:
                logger.info("About to call upload_video function...")
                logger.info(f"Video path: {video_path}")
                logger.info(f"Upload parameters: {upload_params}")
                
                # Call upload_video with video path as first argument according to documentation
                result = upload_video(video_path, **upload_params)
                
                logger.info(f"Upload result: {result}")
                logger.info("Successfully uploaded video to TikTok")
                return {
                    'status': 'success',
                    'description': description,
                    'video_path': video_path,
                    'result': result
                }
            except Exception as upload_error:
                logger.error(f"TikTok upload failed with error: {str(upload_error)}")
                logger.error(f"Upload error type: {type(upload_error)}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                raise upload_error
            
        except Exception as e:
            logger.error(f"Error uploading video to TikTok: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'video_path': video_path
            }
    
    def upload_multiple_videos(self, videos_data):
        """
        Upload multiple videos to TikTok
        
        Args:
            videos_data (list): List of video dictionaries with 'path', 'description', etc.
            
        Returns:
            list: Results for each video upload
        """
        logger.info(f"Uploading {len(videos_data)} videos to TikTok")
        
        results = []
        for video_data in videos_data:
            try:
                result = self.upload_video(
                    video_path=video_data['path'],
                    caption=video_data['description'],
                    hashtags=video_data.get('hashtags'),
                    schedule=video_data.get('schedule'),
                    cover=video_data.get('cover')
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to upload video {video_data['path']}: {str(e)}")
                results.append({
                    'status': 'failed',
                    'error': str(e),
                    'video_path': video_data['path']
                })
        
        return results
    
    def _create_cookies_list(self):
        """Create cookies list from session_id for authentication."""
        if self.session_id:
            self.cookies_list = [{
                'name': 'sessionid',
                'value': self.session_id,
                'domain': '.tiktok.com',
                'path': '/',
                'expiry': int((datetime.now() + timedelta(days=30)).timestamp())
            }]
            logger.info("Created cookies list from session ID")

    @staticmethod
    def get_authentication_instructions():
        """
        Get instructions for extracting sessionid from browser
        
        Returns:
            str: Instructions for getting sessionid
        """
        instructions = """
        HƯỚNG DẪN XÁC THỰC TIKTOK:

        Để upload video, bạn cần cung cấp thông tin xác thực. Có 2 cách:

        Cách 1 (Khuyên dùng): Sử dụng file cookies.txt
        1. Cài extension 'Get cookies.txt' cho trình duyệt (Chrome, Firefox).
        2. Đăng nhập vào TikTok.com.
        3. Nhấn vào biểu tượng extension và chọn 'Export As' để tải file cookies.txt.
        4. Đảm bảo file này được đặt tên là 'cookies.txt' và nằm cùng thư mục với ứng dụng.

        Cách 2: Sử dụng Session ID
        1. Đăng nhập vào TikTok.com.
        2. Nhấn F12 để mở Developer Tools.
        3. Đi đến tab 'Application' -> 'Cookies' -> 'https://www.tiktok.com'.
        4. Tìm cookie có tên 'sessionid' và sao chép giá trị của nó.
        5. Dán giá trị này vào ô 'TikTok Session ID' trong phần Settings của ứng dụng.

        Lưu ý:
        - Ứng dụng sẽ ưu tiên sử dụng file cookies.txt nếu có.
        - Thông tin xác thực có thể hết hạn sau một thời gian, bạn cần cập nhật lại.
        """
        return instructions
