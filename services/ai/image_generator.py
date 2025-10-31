import logging
import os
import base64
import requests
from pathlib import Path
from typing import Optional, Dict, List
import google.generativeai as genai
from config import GEMINI_API_KEY
from .ai_config import AIConfig

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Service to generate images using AI"""

    def __init__(self):
        self.ai_config = AIConfig()
        self.active_provider = self.ai_config.get_active_provider()
        self.provider_config = self.ai_config.get_provider_config()

        # Initialize based on provider
        if self.active_provider == "gemini":
            genai.configure(api_key=self.provider_config.get('api_key') or GEMINI_API_KEY)
            logger.info("Initialized Gemini for image generation")

        # Create temp directory for images
        self.temp_dir = Path("temp/images")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def generate_blog_image(self, title: str, description: str = "", language: str = "english", count: int = 1) -> List[Dict]:
        """
        Generate images for a blog post

        Args:
            title (str): The blog post title
            description (str): Additional description for context
            language (str): Language for image prompt
            count (int): Number of images to generate (default: 1)

        Returns:
            List[Dict]: List of generated image info with 'path', 'url', and 'prompt'
        """
        logger.info(f"Generating {count} image(s) for blog post: {title}")

        # Create image prompt
        prompt = self._create_image_prompt(title, description, language)
        logger.info(f"Image generation prompt: {prompt}")

        images = []

        try:
            if self.active_provider == "gemini":
                # Try Gemini Imagen if available (note: may require special API access)
                images = self._generate_with_gemini_imagen(prompt, count)
            elif self.active_provider == "openai":
                # Use DALL-E
                images = self._generate_with_dalle(prompt, count)
            else:
                logger.warning(f"Image generation not supported for provider: {self.active_provider}")
                # Generate placeholder image
                images = self._generate_placeholder(title, count)

        except Exception as e:
            logger.error(f"Error generating images: {str(e)}")
            # Fallback to placeholder
            images = self._generate_placeholder(title, count)

        return images

    def _create_image_prompt(self, title: str, description: str, language: str) -> str:
        """Create a prompt for image generation"""

        # Base prompt for high-quality blog header image
        base_prompt = f"Create a professional, eye-catching blog header image for: {title}"

        if description:
            base_prompt += f". Context: {description}"

        # Add quality modifiers
        quality_prompt = (
            f"{base_prompt}. "
            "Style: modern, vibrant, high-quality, professional blog featured image. "
            "Clean composition, attractive colors, suitable for mobile apps and technology blog. "
            "No text overlay, 16:9 aspect ratio."
        )

        return quality_prompt

    def _generate_with_gemini_imagen(self, prompt: str, count: int) -> List[Dict]:
        """Generate images using Gemini/Imagen (requires special access)"""
        logger.info("Attempting to generate with Gemini Imagen...")

        # Note: Imagen API may require special access/setup
        # This is a placeholder for future Gemini image generation
        # For now, fall back to placeholder
        raise NotImplementedError("Gemini Imagen not yet available in standard API")

    def _generate_with_dalle(self, prompt: str, count: int) -> List[Dict]:
        """Generate images using OpenAI DALL-E"""
        logger.info("Generating images with DALL-E...")

        openai_api_key = self.provider_config.get('api_key')
        if not openai_api_key:
            raise ValueError("OpenAI API key not configured")

        images = []

        for i in range(count):
            try:
                # Call DALL-E API
                response = requests.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "n": 1,
                        "size": "1792x1024",  # 16:9 aspect ratio
                        "quality": "standard"
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    data = response.json()
                    image_url = data['data'][0]['url']

                    # Download image
                    img_response = requests.get(image_url, timeout=30)
                    if img_response.status_code == 200:
                        # Save to temp file
                        file_path = self.temp_dir / f"blog_image_{i+1}.png"
                        file_path.write_bytes(img_response.content)

                        images.append({
                            'path': str(file_path),
                            'url': image_url,
                            'prompt': prompt,
                            'base64': base64.b64encode(img_response.content).decode('utf-8')
                        })
                        logger.info(f"Generated image {i+1}: {file_path}")
                else:
                    logger.error(f"DALL-E API error: {response.status_code} - {response.text}")
                    raise Exception(f"DALL-E API returned {response.status_code}")

            except Exception as e:
                logger.error(f"Error generating image {i+1}: {str(e)}")
                raise

        return images

    def _generate_placeholder(self, title: str, count: int) -> List[Dict]:
        """Generate placeholder images when AI generation fails or is unavailable"""
        logger.warning("Generating placeholder images (AI image generation unavailable)")

        images = []

        for i in range(count):
            # Use a placeholder image service
            # Using placeholder.com for simple colored placeholders
            width, height = 1200, 675  # 16:9 aspect ratio
            placeholder_url = f"https://via.placeholder.com/{width}x{height}/4A90E2/FFFFFF?text={title.replace(' ', '+')}"

            try:
                # Download placeholder
                response = requests.get(placeholder_url, timeout=10)
                if response.status_code == 200:
                    file_path = self.temp_dir / f"placeholder_image_{i+1}.png"
                    file_path.write_bytes(response.content)

                    images.append({
                        'path': str(file_path),
                        'url': placeholder_url,
                        'prompt': f"Placeholder for: {title}",
                        'base64': base64.b64encode(response.content).decode('utf-8')
                    })
                    logger.info(f"Generated placeholder image {i+1}: {file_path}")
            except Exception as e:
                logger.error(f"Error generating placeholder {i+1}: {str(e)}")
                # Create a minimal placeholder info
                images.append({
                    'path': '',
                    'url': placeholder_url,
                    'prompt': f"Placeholder for: {title}",
                    'base64': ''
                })

        return images

    def upload_to_imgur(self, image_path: str) -> Optional[str]:
        """
        Upload image to Imgur for hosting
        Returns the hosted image URL
        """
        try:
            # Note: This requires IMGUR_CLIENT_ID in config
            # You can get one from https://api.imgur.com/oauth2/addclient
            imgur_client_id = os.getenv('IMGUR_CLIENT_ID')

            if not imgur_client_id:
                logger.warning("IMGUR_CLIENT_ID not configured, skipping upload")
                return None

            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read())

            response = requests.post(
                'https://api.imgur.com/3/image',
                headers={'Authorization': f'Client-ID {imgur_client_id}'},
                data={'image': image_data},
                timeout=30
            )

            if response.status_code == 200:
                url = response.json()['data']['link']
                logger.info(f"Uploaded to Imgur: {url}")
                return url
            else:
                logger.error(f"Imgur upload failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error uploading to Imgur: {str(e)}")
            return None
