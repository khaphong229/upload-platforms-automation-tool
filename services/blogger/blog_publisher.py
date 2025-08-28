import logging
import time
from slugify import slugify
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from config import (
    BLOGGER_BLOG_ID,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REFRESH_TOKEN
)

logger = logging.getLogger(__name__)

class BloggerPublisher:
    """Service to publish content to Blogger"""
    
    def __init__(self, blog_id=None):
        self.blog_id = blog_id or BLOGGER_BLOG_ID
        self.service = self._create_blogger_service()
    
    def _create_blogger_service(self):
        """Create and return an authenticated Blogger API service"""
        try:
            # Validate required credentials
            if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN]):
                raise ValueError("Missing required Google OAuth credentials in .env file")
            
            # Create credentials from refresh token with proper scopes
            credentials = Credentials(
                None,  # No access token needed initially
                refresh_token=GOOGLE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET,
                scopes=['https://www.googleapis.com/auth/blogger']
            )
            
            # Force refresh the credentials to get new access token
            logger.info("Refreshing Google OAuth credentials...")
            credentials.refresh(Request())
            logger.info("Successfully refreshed OAuth credentials")
            
            # Build the Blogger service
            service = build('blogger', 'v3', credentials=credentials)
            logger.info("Successfully created Blogger service")
            return service
            
        except Exception as e:
            logger.error(f"Error creating Blogger service: {str(e)}")
            if "invalid_grant" in str(e).lower():
                logger.error("OAuth refresh token may be expired or invalid. Please regenerate the refresh token.")
                logger.error("Steps to fix:")
                logger.error("1. Go to Google OAuth Playground: https://developers.google.com/oauthplayground/")
                logger.error("2. Select Blogger API v3 scope")
                logger.error("3. Authorize and get new refresh token")
                logger.error("4. Update GOOGLE_REFRESH_TOKEN in .env file")
            raise
    
    def create_post(self, title, content, labels=None, is_draft=False):
        """
        Create a new blog post on Blogger
        
        Args:
            title (str): The title of the blog post
            content (str): The HTML content of the blog post
            labels (list): List of labels/tags for the post
            is_draft (bool): Whether to publish as draft
            
        Returns:
            dict: Information about the created post including URL
        """
        logger.info(f"Creating blog post: {title}")
        
        # Prepare the post body
        post_body = {
            'kind': 'blogger#post',
            'title': title,
            'content': content,
        }
        
        # Add labels if provided
        if labels:
            post_body['labels'] = labels
        
        # Set status (draft or published)
        if is_draft:
            post_body['status'] = 'DRAFT'
        
        try:
            # Insert the post
            post = self.service.posts().insert(
                blogId=self.blog_id,
                body=post_body,
                isDraft=is_draft
            ).execute()
            
            logger.info(f"Successfully created blog post: {post.get('url')}")
            return {
                'id': post.get('id'),
                'url': post.get('url'),
                'title': post.get('title'),
                'published': post.get('published'),
                'updated': post.get('updated')
            }
            
        except HttpError as e:
            logger.error(f"HTTP error creating blog post: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating blog post: {str(e)}")
            raise
    
    def update_post(self, post_id, title=None, content=None, labels=None):
        """
        Update an existing blog post
        
        Args:
            post_id (str): The ID of the post to update
            title (str, optional): New title for the post
            content (str, optional): New content for the post
            labels (list, optional): New labels for the post
            
        Returns:
            dict: Information about the updated post
        """
        logger.info(f"Updating blog post: {post_id}")
        
        try:
            # Get the current post
            post = self.service.posts().get(blogId=self.blog_id, postId=post_id).execute()
            
            # Update fields if provided
            if title:
                post['title'] = title
            if content:
                post['content'] = content
            if labels:
                post['labels'] = labels
            
            # Update the post
            updated_post = self.service.posts().update(
                blogId=self.blog_id,
                postId=post_id,
                body=post
            ).execute()
            
            logger.info(f"Successfully updated blog post: {updated_post.get('url')}")
            return {
                'id': updated_post.get('id'),
                'url': updated_post.get('url'),
                'title': updated_post.get('title'),
                'published': updated_post.get('published'),
                'updated': updated_post.get('updated')
            }
            
        except HttpError as e:
            logger.error(f"HTTP error updating blog post: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating blog post: {str(e)}")
            raise
    
    def get_blog_info(self):
        """
        Get information about the blog
        
        Returns:
            dict: Information about the blog
        """
        logger.info(f"Getting info for blog: {self.blog_id}")
        
        try:
            blog = self.service.blogs().get(blogId=self.blog_id).execute()
            
            logger.info(f"Successfully retrieved blog info: {blog.get('name')}")
            return {
                'id': blog.get('id'),
                'name': blog.get('name'),
                'description': blog.get('description'),
                'url': blog.get('url'),
                'posts_count': blog.get('posts', {}).get('totalItems', 0)
            }
            
        except HttpError as e:
            logger.error(f"HTTP error getting blog info: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting blog info: {str(e)}")
            raise 