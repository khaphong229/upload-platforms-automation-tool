#!/usr/bin/env python3
import os
import sys
import logging
import argparse
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.logging import RichHandler

# Import configuration
from config import validate_config
from config import DOWNLOAD_DIR, TEMP_DIR

# Import services
from services.youtube import YouTubeDownloader
from services.shortener import URLShortener
from services.ai import ContentGenerator
from services.blogger import BloggerPublisher
from services.tiktok import TikTokUploader

# Import utilities
from utils import sanitize_filename, clean_temp_dir

# Set up rich console
console = Console()

# Set up logging with rich handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("main")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Auto Content Distribution Tool")
    
    parser.add_argument("--youtube-url", help="YouTube video URL to download")
    parser.add_argument("--title", help="Custom title for the blog post")
    parser.add_argument("--apk-links", nargs="+", help="List of APK download links")
    parser.add_argument("--skip-download", action="store_true", help="Skip downloading the video")
    parser.add_argument("--skip-blog", action="store_true", help="Skip creating blog post")
    parser.add_argument("--skip-tiktok", action="store_true", help="Skip uploading to TikTok")
    parser.add_argument("--draft", action="store_true", help="Save blog post as draft")
    
    return parser.parse_args()

def get_user_input():
    """Get input from the user"""
    console.print("[bold blue]===== Auto Content Distribution Tool =====[/bold blue]")
    
    youtube_url = Prompt.ask("[bold]Enter YouTube video URL[/bold]")
    
    # Get video info to suggest a title
    yt_downloader = YouTubeDownloader()
    try:
        video_info = yt_downloader.get_video_info(youtube_url)
        suggested_title = video_info.get('title', '')
        console.print(f"[green]Video found:[/green] {suggested_title}")
    except Exception as e:
        console.print(f"[red]Error getting video info: {str(e)}[/red]")
        suggested_title = ""
    
    title = Prompt.ask("[bold]Enter blog post title[/bold]", default=suggested_title)
    
    # Get APK links
    apk_links = []
    console.print("[bold]Enter APK download links (empty line to finish):[/bold]")
    while True:
        link = Prompt.ask("APK link", default="")
        if not link:
            break
        name = Prompt.ask("Link name/description", default=f"Download APK {len(apk_links) + 1}")
        apk_links.append((name, link))
    
    # Confirm settings
    console.print("\n[bold]Settings:[/bold]")
    console.print(f"YouTube URL: {youtube_url}")
    console.print(f"Title: {title}")
    console.print("APK Links:")
    for name, link in apk_links:
        console.print(f"  - {name}: {link}")
    
    if not Confirm.ask("[bold]Proceed with these settings?[/bold]"):
        console.print("[yellow]Aborted by user[/yellow]")
        sys.exit(0)
    
    return {
        'youtube_url': youtube_url,
        'title': title,
        'apk_links': dict(apk_links)
    }

def download_youtube_video(youtube_url, title):
    """Download video from YouTube"""
    console.print("[bold blue]Downloading YouTube video...[/bold blue]")
    
    try:
        # Create sanitized filename from title
        filename = sanitize_filename(title)
        
        # Download the video
        downloader = YouTubeDownloader()
        video_info = downloader.download_video(youtube_url, f"{filename}.mp4")
        
        console.print(f"[green]Video downloaded successfully:[/green] {video_info['file_path']}")
        return video_info
    except Exception as e:
        console.print(f"[red]Error downloading video: {str(e)}[/red]")
        if Confirm.ask("[bold]Continue without video?[/bold]"):
            return None
        else:
            sys.exit(1)

def shorten_apk_links(apk_links):
    """Shorten APK download links"""
    console.print("[bold blue]Shortening APK links...[/bold blue]")
    
    try:
        shortener = URLShortener()
        shortened_links = {}
        
        for name, url in apk_links.items():
            shortened_url = shortener.shorten_url(url)
            shortened_links[name] = shortened_url
            console.print(f"[green]Shortened:[/green] {name} - {shortened_url}")
        
        return shortened_links
    except Exception as e:
        console.print(f"[red]Error shortening links: {str(e)}[/red]")
        if Confirm.ask("[bold]Continue with original links?[/bold]"):
            return apk_links
        else:
            sys.exit(1)

def create_blog_post(title, video_info, shortened_links, is_draft=False):
    """Create a blog post with the video and APK links"""
    console.print("[bold blue]Creating blog post...[/bold blue]")
    
    try:
        # Generate content using AI
        content_generator = ContentGenerator()
        blog_content = content_generator.generate_blog_post(title, video_info, shortened_links)
        
        # Create blog post
        blogger = BloggerPublisher()
        post = blogger.create_post(
            title=title,
            content=blog_content,
            labels=["APK", "Download", "Mobile App"],
            is_draft=is_draft
        )
        
        console.print(f"[green]Blog post created successfully:[/green] {post['url']}")
        return post
    except Exception as e:
        console.print(f"[red]Error creating blog post: {str(e)}[/red]")
        if Confirm.ask("[bold]Continue without blog post?[/bold]"):
            return None
        else:
            sys.exit(1)

def upload_to_tiktok(video_path, title, blog_url):
    """Upload video to TikTok with blog link"""
    console.print("[bold blue]Uploading to TikTok...[/bold blue]")
    
    try:
        # Generate caption with AI
        content_generator = ContentGenerator()
        caption = content_generator.generate_tiktok_caption(title, blog_url)
        
        # Upload to TikTok
        tiktok = TikTokUploader(headless=False)  # Set to True for headless mode
        
        # Login first
        if not tiktok.login():
            raise Exception("Failed to log in to TikTok")
        
        # Upload the video
        result = tiktok.upload_video(
            video_path=video_path,
            caption=caption,
            comment=f"Download links: {blog_url}"
        )
        
        # Close the browser
        tiktok.close()
        
        console.print(f"[green]Video uploaded to TikTok successfully:[/green] {result.get('url', 'URL not available')}")
        return result
    except Exception as e:
        console.print(f"[red]Error uploading to TikTok: {str(e)}[/red]")
        return None

def main():
    """Main function"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Validate configuration
        try:
            validate_config()
        except ValueError as e:
            console.print(f"[red]Configuration error: {str(e)}[/red]")
            console.print("[yellow]Please check your .env file and ensure all required variables are set.[/yellow]")
            sys.exit(1)
        
        # Clean old temporary files
        clean_temp_dir(older_than_days=1)
        
        # Get input from command line args or user
        if args.youtube_url and args.title and args.apk_links:
            input_data = {
                'youtube_url': args.youtube_url,
                'title': args.title,
                'apk_links': {f"Download APK {i+1}": link for i, link in enumerate(args.apk_links)}
            }
        else:
            input_data = get_user_input()
        
        # Download YouTube video
        video_info = None
        if not args.skip_download:
            video_info = download_youtube_video(input_data['youtube_url'], input_data['title'])
        
        # Shorten APK links
        shortened_links = shorten_apk_links(input_data['apk_links'])
        
        # Create blog post
        blog_post = None
        if not args.skip_blog:
            blog_post = create_blog_post(
                input_data['title'],
                video_info,
                shortened_links,
                is_draft=args.draft
            )
        
        # Upload to TikTok
        if not args.skip_tiktok and video_info and blog_post:
            upload_to_tiktok(
                video_info['file_path'],
                input_data['title'],
                blog_post['url']
            )
        
        console.print("[bold green]Process completed successfully![/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Process interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main() 