import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PromptManager:
    """Manager for AI prompt templates"""

    def __init__(self, prompts_file="prompts.json"):
        self.prompts_file = Path(prompts_file)
        self.prompts = {}
        self.load_prompts()

    def load_prompts(self):
        """Load prompts from JSON file"""
        if self.prompts_file.exists():
            try:
                with open(self.prompts_file, 'r', encoding='utf-8') as f:
                    self.prompts = json.load(f)
                logger.info(f"Loaded {len(self.prompts)} prompts from {self.prompts_file}")
            except Exception as e:
                logger.error(f"Error loading prompts: {str(e)}")
                self.prompts = {}
                self._create_default_prompts()
        else:
            self._create_default_prompts()

    def save_prompts(self):
        """Save prompts to JSON file"""
        try:
            with open(self.prompts_file, 'w', encoding='utf-8') as f:
                json.dump(self.prompts, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.prompts)} prompts to {self.prompts_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving prompts: {str(e)}")
            return False

    def _create_default_prompts(self):
        """Create default prompt templates"""
        self.prompts = {
            "default_blog": {
                "name": "Default Blog Post",
                "template": """Write a comprehensive blog post about the following video and app:

TITLE: {title}

VIDEO INFORMATION:
Title: {video_title}
Description: {video_description}

APK DOWNLOAD LINKS:
{apk_links_text}

The blog post should:
1. Have an engaging introduction about the app/game
2. Describe key features and benefits
3. Include the download links prominently
4. Have a clear call-to-action
5. Be SEO-friendly with appropriate headings and structure
6. Be between 500-800 words

Format the blog post in HTML with appropriate tags (h1, h2, p, ul, li, etc.)""",
                "type": "blog",
                "created_at": datetime.now().isoformat(),
                "is_default": True
            },
            "default_tiktok": {
                "name": "Default TikTok Caption",
                "template": "Create a short, engaging TikTok caption (maximum {max_length} characters) for a video about '{title}'. Include emojis and make it attention-grabbing. The caption should encourage viewers to check out the blog post at {blog_url} for download links.",
                "type": "tiktok",
                "created_at": datetime.now().isoformat(),
                "is_default": True
            },
            "gaming_blog": {
                "name": "Gaming Blog Post",
                "template": """Create an exciting blog post about the following gaming app:

TITLE: {title}

VIDEO INFORMATION:
Title: {video_title}
Description: {video_description}

DOWNLOAD LINKS:
{apk_links_text}

Write a blog post that:
1. Opens with a hook about why this game is trending
2. Describes gameplay mechanics and unique features
3. Highlights graphics, controls, and user experience
4. Includes download links with clear installation instructions
5. Has sections: Introduction, Features, Gameplay, Download Guide
6. Uses gaming-related keywords for SEO
7. Length: 600-900 words
8. Format in HTML with proper heading tags""",
                "type": "blog",
                "created_at": datetime.now().isoformat(),
                "is_default": False
            },
            "app_review_blog": {
                "name": "App Review Style",
                "template": """Write a detailed app review for:

TITLE: {title}

VIDEO INFORMATION:
Title: {video_title}
Description: {video_description}

DOWNLOAD LINKS:
{apk_links_text}

Structure the review as follows:
1. Introduction - What the app does
2. Key Features - Bullet points of main features
3. Pros and Cons - Balanced review
4. User Experience - Interface and usability
5. Download Information - Links and installation guide
6. Conclusion - Final recommendation
7. Use HTML formatting with h2, h3, p, ul, li tags
8. Length: 700-1000 words""",
                "type": "blog",
                "created_at": datetime.now().isoformat(),
                "is_default": False
            },
            "viral_tiktok": {
                "name": "Viral TikTok Caption",
                "template": "Create a viral-style TikTok caption (max {max_length} chars) for '{title}'. Use trending emojis, create FOMO, include a question to boost engagement. Mention: Download link in bio! {blog_url}",
                "type": "tiktok",
                "created_at": datetime.now().isoformat(),
                "is_default": False
            }
        }
        self.save_prompts()

    def get_prompt(self, prompt_id: str) -> Optional[Dict]:
        """Get a specific prompt by ID"""
        return self.prompts.get(prompt_id)

    def get_all_prompts(self, prompt_type: Optional[str] = None) -> Dict:
        """Get all prompts, optionally filtered by type"""
        if prompt_type:
            return {k: v for k, v in self.prompts.items() if v.get('type') == prompt_type}
        return self.prompts

    def add_prompt(self, prompt_id: str, name: str, template: str, prompt_type: str = "blog") -> bool:
        """Add a new prompt template"""
        if prompt_id in self.prompts:
            logger.warning(f"Prompt '{prompt_id}' already exists")
            return False

        self.prompts[prompt_id] = {
            "name": name,
            "template": template,
            "type": prompt_type,
            "created_at": datetime.now().isoformat(),
            "is_default": False
        }

        return self.save_prompts()

    def update_prompt(self, prompt_id: str, name: Optional[str] = None,
                     template: Optional[str] = None) -> bool:
        """Update an existing prompt"""
        if prompt_id not in self.prompts:
            logger.warning(f"Prompt '{prompt_id}' not found")
            return False

        if self.prompts[prompt_id].get('is_default', False):
            logger.warning(f"Cannot modify default prompt '{prompt_id}'")
            return False

        if name:
            self.prompts[prompt_id]['name'] = name
        if template:
            self.prompts[prompt_id]['template'] = template

        self.prompts[prompt_id]['updated_at'] = datetime.now().isoformat()

        return self.save_prompts()

    def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a prompt template"""
        if prompt_id not in self.prompts:
            logger.warning(f"Prompt '{prompt_id}' not found")
            return False

        if self.prompts[prompt_id].get('is_default', False):
            logger.warning(f"Cannot delete default prompt '{prompt_id}'")
            return False

        del self.prompts[prompt_id]
        return self.save_prompts()

    def get_prompt_names(self, prompt_type: Optional[str] = None) -> List[tuple]:
        """Get list of (prompt_id, prompt_name) tuples"""
        prompts = self.get_all_prompts(prompt_type)
        return [(k, v['name']) for k, v in prompts.items()]

    def format_prompt(self, prompt_id: str, **kwargs) -> str:
        """Format a prompt template with provided variables"""
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            raise ValueError(f"Prompt '{prompt_id}' not found")

        try:
            return prompt['template'].format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing variable {e} for prompt '{prompt_id}'")
            raise ValueError(f"Missing variable {e} for prompt template")
