"""
N8N Webhook Integration for YouTube Upload
Alternative approach using existing n8n workflow
"""

import requests
import logging
from typing import Tuple, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class N8NYouTubeUploader:
    """
    Upload videos to YouTube via n8n webhook
    This is an alternative to the direct API approach
    """

    def __init__(self, webhook_url: str):
        """
        Initialize n8n uploader

        Args:
            webhook_url: Your n8n webhook URL
                        e.g., "http://localhost:5678/webhook/youtube-upload"
        """
        self.webhook_url = webhook_url

    def is_available(self) -> bool:
        """Check if n8n server is reachable"""
        try:
            response = requests.get(
                self.webhook_url.replace('/webhook/', '/webhook-test/'),
                timeout=5
            )
            return response.status_code in [200, 404]  # 404 is ok, means server is up
        except Exception as e:
            logger.error(f"n8n server not reachable: {e}")
            return False

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = '',
        tags: list = None,
        privacy_status: str = 'private',
        category_id: str = '22',
        made_for_kids: bool = False,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Upload video to YouTube via n8n webhook

        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags
            privacy_status: 'public', 'private', or 'unlisted'
            category_id: YouTube category ID
            made_for_kids: Whether video is for children
            **kwargs: Additional parameters

        Returns:
            (success, message/video_url)
        """
        try:
            # Validate video exists
            video_file = Path(video_path)
            if not video_file.exists():
                return False, f"Video file not found: {video_path}"

            logger.info(f"Uploading video via n8n: {video_file.name}")

            # Option 1: Send video path (if n8n is on same machine)
            if kwargs.get('send_path', False):
                payload = {
                    'video_path': str(video_file.absolute()),
                    'title': title,
                    'description': description,
                    'tags': tags or [],
                    'privacy_status': privacy_status,
                    'category_id': category_id,
                    'made_for_kids': made_for_kids
                }

                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=300  # 5 minutes timeout
                )

            # Option 2: Upload video file (multipart)
            else:
                with open(video_file, 'rb') as f:
                    files = {'video': (video_file.name, f, 'video/mp4')}

                    data = {
                        'title': title,
                        'description': description,
                        'tags': ','.join(tags or []),
                        'privacy_status': privacy_status,
                        'category_id': category_id,
                        'made_for_kids': str(made_for_kids).lower()
                    }

                    response = requests.post(
                        self.webhook_url,
                        files=files,
                        data=data,
                        timeout=600  # 10 minutes for large files
                    )

            # Check response
            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    video_url = result.get('video_url', '')
                    logger.info(f"Upload successful: {video_url}")
                    return True, video_url
                else:
                    error = result.get('error', 'Unknown error')
                    logger.error(f"Upload failed: {error}")
                    return False, error
            else:
                error = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"n8n request failed: {error}")
                return False, error

        except requests.Timeout:
            error = "Upload timeout - video may be too large or network slow"
            logger.error(error)
            return False, error

        except requests.ConnectionError:
            error = "Cannot connect to n8n server. Is it running?"
            logger.error(error)
            return False, error

        except Exception as e:
            error = f"Upload error: {str(e)}"
            logger.error(error)
            return False, error

    def get_status(self, job_id: str) -> Optional[Dict]:
        """
        Get upload job status (if n8n supports async uploads)

        Args:
            job_id: Upload job ID

        Returns:
            Job status dict or None
        """
        try:
            status_url = f"{self.webhook_url}/status/{job_id}"
            response = requests.get(status_url, timeout=10)

            if response.status_code == 200:
                return response.json()

            return None

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return None


# Example usage
if __name__ == "__main__":
    # Initialize uploader
    uploader = N8NYouTubeUploader("http://localhost:5678/webhook/youtube-upload")

    # Check if n8n is available
    if not uploader.is_available():
        print("❌ n8n server not available")
        exit(1)

    # Upload video
    success, result = uploader.upload(
        video_path="test_video.mp4",
        title="Test Video",
        description="This is a test upload via n8n",
        tags=["test", "n8n", "automation"],
        privacy_status="private",
        send_path=True  # Use True if n8n is on same machine
    )

    if success:
        print(f"✅ Upload successful!")
        print(f"Video URL: {result}")
    else:
        print(f"❌ Upload failed: {result}")
