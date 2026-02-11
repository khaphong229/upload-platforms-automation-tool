"""
YouTube Upload Service
Handles video uploads to YouTube using the YouTube Data API v3
"""

import os
import logging
import pickle
from pathlib import Path
from typing import Tuple, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class YouTubeUploader:
    """Service to upload videos to YouTube"""

    # YouTube API scopes
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    # Privacy status options
    PRIVACY_PUBLIC = 'public'
    PRIVACY_PRIVATE = 'private'
    PRIVACY_UNLISTED = 'unlisted'

    # Category IDs (common ones)
    CATEGORY_GAMING = '20'
    CATEGORY_ENTERTAINMENT = '24'
    CATEGORY_EDUCATION = '27'
    CATEGORY_HOWTO_STYLE = '26'
    CATEGORY_SCIENCE_TECH = '28'
    CATEGORY_PEOPLE_BLOGS = '22'

    def __init__(self, credentials_path: str = None, token_path: str = None):
        """
        Initialize YouTube uploader

        Args:
            credentials_path: Path to OAuth2 client credentials JSON file
            token_path: Path to save/load OAuth tokens (per account)
        """
        self.credentials_path = Path(credentials_path or 'youtube_credentials.json')
        self.token_dir = Path('youtube_tokens')
        self.token_dir.mkdir(exist_ok=True)
        self.token_path = token_path

        self.youtube = None

    def is_available(self) -> bool:
        """Check if YouTube service is available (credentials file exists)"""
        return self.credentials_path.exists()

    def authenticate(self, account_name: str = 'default') -> bool:
        """
        Authenticate with YouTube API

        Args:
            account_name: Name to identify this account

        Returns:
            True if authentication successful
        """
        try:
            token_file = self.token_dir / f'{account_name}_token.pickle'
            creds = None

            # Load existing token
            if token_file.exists():
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)

            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired token...")
                    creds.refresh(Request())
                else:
                    if not self.credentials_path.exists():
                        logger.error(f"Credentials file not found: {self.credentials_path}")
                        return False

                    logger.info("Starting OAuth2 flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save the credentials for next time
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info(f"Token saved for account: {account_name}")

            # Build YouTube service
            self.youtube = build('youtube', 'v3', credentials=creds)
            logger.info(f"Successfully authenticated YouTube account: {account_name}")
            return True

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False

    def get_saved_accounts(self) -> List[str]:
        """Get list of saved YouTube accounts"""
        accounts = []
        for token_file in self.token_dir.glob('*_token.pickle'):
            account_name = token_file.stem.replace('_token', '')
            accounts.append(account_name)
        return sorted(accounts)

    def delete_account(self, account_name: str) -> Tuple[bool, str]:
        """Delete saved account credentials"""
        try:
            token_file = self.token_dir / f'{account_name}_token.pickle'
            if token_file.exists():
                token_file.unlink()
                return True, f"Account '{account_name}' deleted successfully"
            else:
                return False, f"Account '{account_name}' not found"
        except Exception as e:
            return False, f"Error deleting account: {str(e)}"

    def validate_video(self, video_path: str) -> Tuple[bool, str]:
        """
        Validate video file before upload

        Args:
            video_path: Path to video file

        Returns:
            (is_valid, message)
        """
        path = Path(video_path)

        if not path.exists():
            return False, "Video file not found"

        # Check file size (YouTube limit: 256 GB for verified, 128 GB for unverified)
        size_mb = path.stat().st_size / (1024 * 1024)
        size_gb = size_mb / 1024

        if size_gb > 128:
            return False, f"Video too large: {size_gb:.1f} GB (max 128 GB for unverified accounts)"

        # Check file extension
        valid_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.mpeg', '.mpg'}
        if path.suffix.lower() not in valid_extensions:
            return False, f"Invalid video format. Supported: {', '.join(valid_extensions)}"

        return True, f"Video valid: {size_mb:.1f} MB"

    def upload(
        self,
        account_name: str,
        video_path: str,
        title: str,
        description: str = '',
        tags: List[str] = None,
        category_id: str = CATEGORY_PEOPLE_BLOGS,
        privacy_status: str = PRIVACY_PRIVATE,
        thumbnail_path: str = None,
        made_for_kids: bool = False,
        notify_subscribers: bool = True
    ) -> Tuple[bool, str]:
        """
        Upload video to YouTube

        Args:
            account_name: YouTube account to upload to
            video_path: Path to video file
            title: Video title (max 100 chars)
            description: Video description (max 5000 chars)
            tags: List of tags (max 500 chars total)
            category_id: YouTube category ID
            privacy_status: 'public', 'private', or 'unlisted'
            thumbnail_path: Optional custom thumbnail image
            made_for_kids: Whether video is made for kids (COPPA)
            notify_subscribers: Whether to notify subscribers

        Returns:
            (success, message/video_url)
        """
        try:
            # Validate video
            valid, msg = self.validate_video(video_path)
            if not valid:
                return False, msg

            logger.info(f"Uploading video to YouTube account: {account_name}")

            # Authenticate if not already
            if not self.youtube:
                if not self.authenticate(account_name):
                    return False, "Authentication failed"

            # Truncate title and description if needed
            title = title[:100] if len(title) > 100 else title
            description = description[:5000] if len(description) > 5000 else description

            # Prepare tags
            if tags:
                # YouTube tag limit: 500 chars total
                tags_str = ','.join(tags)
                if len(tags_str) > 500:
                    # Truncate tags
                    truncated_tags = []
                    total_len = 0
                    for tag in tags:
                        if total_len + len(tag) + 1 <= 500:
                            truncated_tags.append(tag)
                            total_len += len(tag) + 1
                        else:
                            break
                    tags = truncated_tags

            # Video metadata
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags or [],
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': made_for_kids
                },
                'notifySubscribers': notify_subscribers
            }

            # Media file
            media = MediaFileUpload(
                video_path,
                chunksize=1024 * 1024,  # 1 MB chunks
                resumable=True
            )

            # Execute upload
            logger.info("Starting upload...")
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            retry_count = 0
            max_retries = 3

            while response is None and retry_count < max_retries:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info(f"Upload progress: {progress}%")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        # Retryable error
                        retry_count += 1
                        logger.warning(f"Retryable error {e.resp.status}, retry {retry_count}/{max_retries}")
                        if retry_count >= max_retries:
                            raise
                    else:
                        raise

            if response:
                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                # Upload thumbnail if provided
                if thumbnail_path and Path(thumbnail_path).exists():
                    try:
                        self.youtube.thumbnails().set(
                            videoId=video_id,
                            media_body=MediaFileUpload(thumbnail_path)
                        ).execute()
                        logger.info("Thumbnail uploaded successfully")
                    except Exception as e:
                        logger.warning(f"Failed to upload thumbnail: {e}")

                logger.info(f"Upload successful! Video ID: {video_id}")
                return True, video_url
            else:
                return False, "Upload failed: No response from YouTube"

        except HttpError as e:
            error_msg = f"HTTP error: {e.resp.status} - {e.content.decode()}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_channel_info(self) -> Optional[Dict]:
        """Get authenticated channel information"""
        try:
            if not self.youtube:
                return None

            request = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            )
            response = request.execute()

            if response.get('items'):
                channel = response['items'][0]
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'description': channel['snippet']['description'],
                    'subscribers': channel['statistics'].get('subscriberCount', 'Hidden'),
                    'video_count': channel['statistics'].get('videoCount', '0'),
                    'view_count': channel['statistics'].get('viewCount', '0'),
                    'thumbnail': channel['snippet']['thumbnails']['default']['url']
                }
            return None

        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            return None
