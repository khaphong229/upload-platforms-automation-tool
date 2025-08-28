import logging
import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

class ContentGenerator:
    """Service to generate content using Google Gemini API"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or GEMINI_API_KEY
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def generate_blog_post(self, title, video_info, apk_links, max_tokens=1000):
        """
        Generate a blog post about a video with APK links
        
        Args:
            title (str): The title of the blog post
            video_info (dict): Information about the video
            apk_links (dict): Dictionary of APK links (original -> shortened)
            max_tokens (int): Maximum number of tokens for the generated content
            
        Returns:
            str: The generated blog post content
        """
        logger.info(f"Generating blog post for: {title}")
        
        # Create a prompt for the AI
        prompt = self._create_blog_prompt(title, video_info, apk_links)
        
        try:
            # Call the Gemini API
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": max_tokens,
                }
            )
            
            # Extract the generated content
            content = response.text.strip()
            logger.info(f"Successfully generated blog post of {len(content)} characters")
            logger.info(content)
            return content
            
        except Exception as e:
            logger.error(f"Error generating blog post: {str(e)}")
            # Fallback to a simple template if AI generation fails
            return self._create_fallback_content(title, video_info, apk_links)
    
    def _create_blog_prompt(self, title, video_info, apk_links):
        """Create a prompt for the AI to generate a blog post"""
        
        # Extract video information
        video_title = video_info.get('title', title)
        video_description = video_info.get('description', '')
        
        # Create a list of APK links
        apk_links_text = "\n".join([f"- {name}: {url}" for name, url in apk_links.items()])
        
        # Create the prompt
        prompt = f"""
        Write a comprehensive blog post about the following video and app:
        
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
        
        Format the blog post in HTML with appropriate tags (h1, h2, p, ul, li, etc.)
        """
        
        return prompt
    
    def _create_fallback_content(self, title, video_info, apk_links):
        """Create a simple blog post template as fallback"""
        
        # Extract video information
        video_title = video_info.get('title', title)
        video_description = video_info.get('description', '')
        
        # Create a list of APK links
        apk_links_html = "\n".join([f"<li><a href='{url}' target='_blank'>{name}</a></li>" for name, url in apk_links.items()])
        
        # Create a simple HTML template
        html_content = f"""
        <h1>{title}</h1>
        
        <p>Welcome to our blog post about {video_title}. In this article, we'll provide you with information about this app and direct download links.</p>
        
        <h2>About the App</h2>
        <p>{video_description}</p>
        
        <h2>Download Links</h2>
        <p>You can download the APK files from the following links:</p>
        <ul>
        {apk_links_html}
        </ul>
        
        <h2>How to Install</h2>
        <p>1. Download the APK file from the links above</p>
        <p>2. Enable installation from unknown sources in your device settings</p>
        <p>3. Open the APK file and follow the installation instructions</p>
        <p>4. Enjoy the app!</p>
        
        <p>If you have any questions or issues with the download, please leave a comment below.</p>
        """
        
        return html_content
    
    def generate_tiktok_caption(self, title, blog_url, max_length=150):
        """
        Generate a caption for TikTok video
        
        Args:
            title (str): The title of the video
            blog_url (str): URL to the blog post
            max_length (int): Maximum length of the caption
            
        Returns:
            str: The generated caption
        """
        logger.info(f"Generating TikTok caption for: {title}")
        
        try:
            # Call the Gemini API
            prompt = f"Create a short, engaging TikTok caption (maximum {max_length} characters) for a video about '{title}'. Include emojis and make it attention-grabbing. The caption should encourage viewers to check out the blog post at {blog_url} for download links."
            
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 100,
                }
            )
            
            # Extract the generated content and ensure it's not too long
            caption = response.text.strip()
            if len(caption) > max_length:
                caption = caption[:max_length-3] + "..."
                
            logger.info(f"Successfully generated TikTok caption: {caption}")
            return caption
            
        except Exception as e:
            logger.error(f"Error generating TikTok caption: {str(e)}")
            # Fallback to a simple caption if AI generation fails
            return f"📱 Check out {title}! Download links in blog: {blog_url} #app #download #mobile" 