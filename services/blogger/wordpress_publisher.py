import logging
import requests
from typing import List, Optional

logger = logging.getLogger(__name__)


class WordPressPublisher:
    """Service to publish blog posts to WordPress"""

    def __init__(self, site_url: str = None, username: str = None, password: str = None):
        """
        Initialize WordPress publisher

        Args:
            site_url: WordPress site URL (e.g., 'https://example.com')
            username: WordPress username
            password: WordPress application password or password
        """
        self.site_url = site_url
        self.username = username
        self.password = password

        # WordPress REST API endpoint
        if site_url:
            self.api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2"

    def create_post(self, title: str, content: str, status: str = "publish",
                   categories: Optional[List[str]] = None,
                   tags: Optional[List[str]] = None) -> dict:
        """
        Create a new WordPress post

        Args:
            title: Post title
            content: Post content (HTML)
            status: Post status ('publish', 'draft', 'pending', 'private')
            categories: List of category names
            tags: List of tag names

        Returns:
            dict: Created post data with 'id', 'link', 'status'
        """
        if not all([self.site_url, self.username, self.password]):
            raise ValueError("WordPress credentials not configured")

        logger.info(f"Creating WordPress post: {title}")

        # Get category IDs
        category_ids = []
        if categories:
            category_ids = self._get_or_create_categories(categories)

        # Get tag IDs
        tag_ids = []
        if tags:
            tag_ids = self._get_or_create_tags(tags)

        # Prepare post data
        post_data = {
            "title": title,
            "content": content,
            "status": status,
            "categories": category_ids,
            "tags": tag_ids
        }

        try:
            # Make API request
            response = requests.post(
                f"{self.api_url}/posts",
                json=post_data,
                auth=(self.username, self.password),
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            response.raise_for_status()
            post = response.json()

            logger.info(f"WordPress post created successfully: {post.get('link')}")

            return {
                'id': post.get('id'),
                'url': post.get('link'),
                'link': post.get('link'),
                'status': post.get('status'),
                'title': post.get('title', {}).get('rendered', title)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create WordPress post: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Failed to create WordPress post: {str(e)}")

    def _get_or_create_categories(self, category_names: List[str]) -> List[int]:
        """Get or create categories and return their IDs"""
        category_ids = []

        for name in category_names:
            try:
                # Search for existing category
                response = requests.get(
                    f"{self.api_url}/categories",
                    params={"search": name},
                    auth=(self.username, self.password),
                    timeout=10
                )

                if response.status_code == 200:
                    categories = response.json()
                    if categories:
                        category_ids.append(categories[0]['id'])
                        continue

                # Create new category if not found
                response = requests.post(
                    f"{self.api_url}/categories",
                    json={"name": name},
                    auth=(self.username, self.password),
                    timeout=10
                )

                if response.status_code == 201:
                    category = response.json()
                    category_ids.append(category['id'])

            except Exception as e:
                logger.warning(f"Failed to get/create category '{name}': {str(e)}")

        return category_ids

    def _get_or_create_tags(self, tag_names: List[str]) -> List[int]:
        """Get or create tags and return their IDs"""
        tag_ids = []

        for name in tag_names:
            try:
                # Search for existing tag
                response = requests.get(
                    f"{self.api_url}/tags",
                    params={"search": name},
                    auth=(self.username, self.password),
                    timeout=10
                )

                if response.status_code == 200:
                    tags = response.json()
                    if tags:
                        tag_ids.append(tags[0]['id'])
                        continue

                # Create new tag if not found
                response = requests.post(
                    f"{self.api_url}/tags",
                    json={"name": name},
                    auth=(self.username, self.password),
                    timeout=10
                )

                if response.status_code == 201:
                    tag = response.json()
                    tag_ids.append(tag['id'])

            except Exception as e:
                logger.warning(f"Failed to get/create tag '{name}': {str(e)}")

        return tag_ids

    def update_post(self, post_id: int, title: Optional[str] = None,
                   content: Optional[str] = None, status: Optional[str] = None) -> dict:
        """
        Update an existing WordPress post

        Args:
            post_id: WordPress post ID
            title: New title (optional)
            content: New content (optional)
            status: New status (optional)

        Returns:
            dict: Updated post data
        """
        if not all([self.site_url, self.username, self.password]):
            raise ValueError("WordPress credentials not configured")

        logger.info(f"Updating WordPress post ID: {post_id}")

        post_data = {}
        if title:
            post_data['title'] = title
        if content:
            post_data['content'] = content
        if status:
            post_data['status'] = status

        try:
            response = requests.post(
                f"{self.api_url}/posts/{post_id}",
                json=post_data,
                auth=(self.username, self.password),
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            response.raise_for_status()
            post = response.json()

            logger.info(f"WordPress post updated successfully")

            return {
                'id': post.get('id'),
                'url': post.get('link'),
                'status': post.get('status')
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update WordPress post: {str(e)}")
            raise Exception(f"Failed to update WordPress post: {str(e)}")

    def delete_post(self, post_id: int) -> bool:
        """
        Delete a WordPress post

        Args:
            post_id: WordPress post ID

        Returns:
            bool: True if successful
        """
        if not all([self.site_url, self.username, self.password]):
            raise ValueError("WordPress credentials not configured")

        logger.info(f"Deleting WordPress post ID: {post_id}")

        try:
            response = requests.delete(
                f"{self.api_url}/posts/{post_id}",
                auth=(self.username, self.password),
                timeout=30
            )

            response.raise_for_status()
            logger.info("WordPress post deleted successfully")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete WordPress post: {str(e)}")
            return False

    def test_connection(self) -> tuple:
        """
        Test WordPress connection

        Returns:
            tuple: (success: bool, message: str)
        """
        if not all([self.site_url, self.username, self.password]):
            return False, "WordPress credentials not configured"

        try:
            response = requests.get(
                f"{self.api_url}/posts",
                auth=(self.username, self.password),
                params={"per_page": 1},
                timeout=10
            )

            if response.status_code == 200:
                return True, "WordPress connection successful"
            else:
                return False, f"WordPress connection failed: {response.status_code}"

        except requests.exceptions.RequestException as e:
            return False, f"WordPress connection failed: {str(e)}"
