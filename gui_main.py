#!/usr/bin/env python3
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
import threading
import logging
import time
from pathlib import Path
import queue
from datetime import datetime

# Import configuration
from config import validate_config
from config import DOWNLOAD_DIR, TEMP_DIR, TIKTOK_SESSION_ID

# Import services
from services.youtube import YouTubeDownloader
from services.shortener import URLShortener
from services.ai import ContentGenerator
from services.blogger import BloggerPublisher
from services.tiktok import TikTokUploader, NewTikTokUploader

# Import utilities
from utils import sanitize_filename, clean_temp_dir


class LogHandler(logging.Handler):
    """Custom logging handler for GUI"""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        log_entry = self.format(record)
        self.log_queue.put(log_entry)


class ContentDistributionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Content Distribution Tool")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Initialize variables
        self.youtube_url = tk.StringVar()
        self.title = tk.StringVar()
        self.local_video_path = tk.StringVar()
        self.video_source = tk.StringVar(value="youtube")  # "youtube" or "local"
        self.apk_links = []
        self.skip_download = tk.BooleanVar()
        self.skip_blog = tk.BooleanVar()
        self.skip_tiktok = tk.BooleanVar()
        self.draft_mode = tk.BooleanVar()
        
        # Progress tracking
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")
        self.is_processing = False
        
        # Initialize batch uploader
        try:
            self.batch_uploader = EnhancedTikTokUploader()
        except Exception as e:
            self.batch_uploader = None
            print(f"Warning: Could not initialize batch uploader: {e}")
        
        # Logging setup
        self.log_queue = queue.Queue()
        self.setup_logging()
        
        # Create GUI
        self.create_widgets()
        
        # Start log monitoring
        self.check_log_queue()
        
        # Validate config on startup
        self.validate_configuration()
    
    def setup_logging(self):
        """Setup logging for GUI"""
        # Create custom handler
        log_handler = LogHandler(self.log_queue)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # Configure root logger
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger()
        logger.addHandler(log_handler)
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Create main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Auto Content Distribution Tool", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(1, weight=1)
        
        # Create tabs
        self.create_content_distribution_tab()
        # Removed TikTok Batch Uploader Tab

    def create_content_distribution_tab(self):
        """Create the content distribution tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Content Distribution")

        # Video Source section
        source_frame = ttk.LabelFrame(tab, text="Video Source", padding="10")
        source_frame.pack(fill='x', pady=5)
        source_frame.columnconfigure(1, weight=1)
        # Radio buttons for video source
        ttk.Radiobutton(source_frame, text="YouTube URL", variable=self.video_source, 
                       value="youtube", command=self.on_source_change).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        ttk.Radiobutton(source_frame, text="Local Video File", variable=self.video_source, 
                       value="local", command=self.on_source_change).grid(row=0, column=1, sticky=tk.W)
        
        # YouTube URL input
        self.youtube_frame = ttk.Frame(source_frame)
        self.youtube_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.youtube_frame.columnconfigure(0, weight=1)
        
        ttk.Label(self.youtube_frame, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        url_input_frame = ttk.Frame(self.youtube_frame)
        url_input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        url_input_frame.columnconfigure(0, weight=1)
        
        self.url_entry = ttk.Entry(url_input_frame, textvariable=self.youtube_url, width=50)
        self.url_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.fetch_info_btn = ttk.Button(url_input_frame, text="Get Info", command=self.fetch_video_info)
        self.fetch_info_btn.grid(row=0, column=1)
        
        # Local video file input
        self.local_frame = ttk.Frame(source_frame)
        self.local_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.local_frame.columnconfigure(0, weight=1)
        
        ttk.Label(self.local_frame, text="Video File:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        file_input_frame = ttk.Frame(self.local_frame)
        file_input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        file_input_frame.columnconfigure(0, weight=1)
        
        self.file_entry = ttk.Entry(file_input_frame, textvariable=self.local_video_path, width=50, state=tk.DISABLED)
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.browse_btn = ttk.Button(file_input_frame, text="Browse", command=self.browse_video_file, state=tk.DISABLED)
        self.browse_btn.grid(row=0, column=1)
        
        # Title section
        title_frame = ttk.LabelFrame(tab, text="Blog Post Settings", padding="10")
        title_frame.pack(fill='x', pady=10)
        title_frame.columnconfigure(1, weight=1)
        
        ttk.Label(title_frame, text="Blog Title:", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=5)
        
        self.title_entry = ttk.Entry(title_frame, textvariable=self.title, width=60)
        self.title_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        ttk.Label(title_frame, text="Enter your custom blog post title", 
                 font=('Arial', 8), foreground='gray').grid(
            row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # APK Links section
        apk_section_frame = ttk.Frame(tab)
        apk_section_frame.pack(fill='x', pady=10)
        
        ttk.Label(apk_section_frame, text="APK Links:", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, sticky=(tk.W, tk.N), pady=5)
        
        apk_frame = ttk.Frame(apk_section_frame)
        apk_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        apk_section_frame.columnconfigure(1, weight=1)
        apk_frame.columnconfigure(0, weight=1)
        
        # APK links listbox with scrollbar
        listbox_frame = ttk.Frame(apk_frame)
        listbox_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        listbox_frame.columnconfigure(0, weight=1)
        
        self.apk_listbox = tk.Listbox(listbox_frame, height=4)
        self.apk_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        apk_scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.apk_listbox.yview)
        apk_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.apk_listbox.configure(yscrollcommand=apk_scrollbar.set)
        
        # APK buttons
        apk_btn_frame = ttk.Frame(apk_frame)
        apk_btn_frame.grid(row=1, column=0, sticky=tk.W)
        
        ttk.Button(apk_btn_frame, text="Add APK Link", command=self.add_apk_link).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(apk_btn_frame, text="Remove Selected", command=self.remove_apk_link).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(apk_btn_frame, text="Clear All", command=self.clear_apk_links).grid(row=0, column=2)
        
        # Options section
        options_frame = ttk.LabelFrame(tab, text="Processing Options", padding="10")
        options_frame.pack(fill='x', pady=10)
        
        ttk.Checkbutton(options_frame, text="Skip Download", variable=self.skip_download).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Skip Blog Creation", variable=self.skip_blog).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        ttk.Checkbutton(options_frame, text="Skip TikTok Upload", variable=self.skip_tiktok).grid(row=1, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Save as Draft", variable=self.draft_mode).grid(row=1, column=1, sticky=tk.W, padx=(20, 0))
        
        # Progress section
        progress_frame = ttk.LabelFrame(tab, text="Progress", padding="10")
        progress_frame.pack(fill='x', pady=10)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, sticky=tk.W)
        
        # Control buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(pady=20)
        
        self.start_btn = ttk.Button(btn_frame, text="Start Process", command=self.start_process, 
                                   style='Accent.TButton')
        self.start_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_process, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(btn_frame, text="Settings", command=self.open_settings).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(btn_frame, text="Clear Log", command=self.clear_log).grid(row=0, column=3)
        
        # Log section
        log_frame = ttk.LabelFrame(tab, text="Log", padding="10")
        log_frame.pack(fill='both', expand=True, pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Initialize UI state
        self.on_source_change()
    
        # Load existing profiles
        self.refresh_batch_profiles()

    def validate_configuration(self):
        """Validate configuration on startup"""
        try:
            validate_config()
            self.log_message("Configuration validated successfully", "INFO")
        except ValueError as e:
            self.log_message(f"Configuration error: {str(e)}", "ERROR")
            messagebox.showerror("Configuration Error", 
                               f"Configuration error: {str(e)}\n\nPlease check your .env file.")
    
    def on_source_change(self):
        """Handle video source selection change"""
        if self.video_source.get() == "youtube":
            # Enable YouTube controls
            self.url_entry.config(state=tk.NORMAL)
            self.fetch_info_btn.config(state=tk.NORMAL)
            # Disable local file controls
            self.file_entry.config(state=tk.DISABLED)
            self.browse_btn.config(state=tk.DISABLED)
            # Show/hide frames
            self.youtube_frame.grid()
            self.local_frame.grid_remove()
        else:
            # Disable YouTube controls
            self.url_entry.config(state=tk.DISABLED)
            self.fetch_info_btn.config(state=tk.DISABLED)
            # Enable local file controls
            self.file_entry.config(state=tk.NORMAL)
            self.browse_btn.config(state=tk.NORMAL)
            # Show/hide frames
            self.youtube_frame.grid_remove()
            self.local_frame.grid()
    
    def browse_video_file(self):
        """Browse for local video file"""
        filetypes = [
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm"),
            ("MP4 files", "*.mp4"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=filetypes
        )
        
        if filename:
            self.local_video_path.set(filename)
            # Extract filename for default title if title is empty
            if not self.title.get():
                video_name = Path(filename).stem
                # Clean up the filename for title
                clean_title = video_name.replace("_", " ").replace("-", " ").title()
                self.title.set(clean_title)
            
            self.log_message(f"Selected video file: {filename}", "INFO")
    
    def fetch_video_info(self):
        """Fetch video information from YouTube URL"""
        url = self.youtube_url.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL first")
            return
        
        def fetch_info():
            try:
                self.status_var.set("Fetching video info...")
                self.fetch_info_btn.config(state=tk.DISABLED)
                
                downloader = YouTubeDownloader()
                video_info = downloader.get_video_info(url)
                
                # Auto-fill title from YouTube video
                suggested_title = video_info.get('title', '')
                if suggested_title:
                    self.title.set(suggested_title)
                    self.log_message(f"Auto-filled blog title: {suggested_title}", "INFO")
                
                self.log_message(f"Video found: {video_info.get('title', 'Unknown')}", "INFO")
                self.status_var.set("Video info fetched successfully")
                
            except Exception as e:
                self.log_message(f"Error fetching video info: {str(e)}", "ERROR")
                self.status_var.set("Error fetching video info")
            finally:
                self.fetch_info_btn.config(state=tk.NORMAL)
        
        threading.Thread(target=fetch_info, daemon=True).start()
    
    def add_apk_link(self):
        """Add APK link dialog"""
        dialog = APKLinkDialog(self.root)
        if dialog.result:
            name, url = dialog.result
            self.apk_links.append((name, url))
            self.apk_listbox.insert(tk.END, f"{name}: {url}")
            self.log_message(f"Added APK link: {name}", "INFO")
    
    def remove_apk_link(self):
        """Remove selected APK link"""
        selection = self.apk_listbox.curselection()
        if selection:
            index = selection[0]
            removed_item = self.apk_links.pop(index)
            self.apk_listbox.delete(index)
            self.log_message(f"Removed APK link: {removed_item[0]}", "INFO")
    
    def clear_apk_links(self):
        """Clear all APK links"""
        if self.apk_links and messagebox.askyesno("Confirm", "Clear all APK links?"):
            self.apk_links.clear()
            self.apk_listbox.delete(0, tk.END)
            self.log_message("Cleared all APK links", "INFO")
    
    def start_process(self):
        """Start the content distribution process"""
        # Validate inputs based on video source
        if self.video_source.get() == "youtube":
            if not self.youtube_url.get().strip():
                messagebox.showerror("Error", "Please enter a YouTube URL")
                return
        else:
            if not self.local_video_path.get().strip():
                messagebox.showerror("Error", "Please select a video file")
                return
            if not Path(self.local_video_path.get()).exists():
                messagebox.showerror("Error", "Selected video file does not exist")
                return
        
        if not self.title.get().strip():
            messagebox.showerror("Error", "Please enter a blog title")
            return
        
        # Start processing in separate thread
        self.is_processing = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        threading.Thread(target=self.process_content, daemon=True).start()
    
    def stop_process(self):
        """Stop the current process"""
        self.is_processing = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Process stopped by user")
        self.log_message("Process stopped by user", "WARNING")
    
    def process_content(self):
        """Main content processing function"""
        try:
            # Clean old temporary files
            clean_temp_dir(older_than_days=1)
            
            total_steps = 4  # Download, Shorten, Blog, TikTok
            current_step = 0
            
            # Step 1: Get video (download or use local)
            video_info = None
            if not self.skip_download.get() and self.is_processing:
                current_step += 1
                if self.video_source.get() == "youtube":
                    self.update_progress(current_step, total_steps, "Downloading YouTube video...")
                    video_info = self.download_youtube_video()
                else:
                    self.update_progress(current_step, total_steps, "Using local video file...")
                    video_info = self.use_local_video()
            
            # Step 2: Shorten APK links
            shortened_links = {}
            if self.apk_links and self.is_processing:
                current_step += 1
                self.update_progress(current_step, total_steps, "Shortening APK links...")
                shortened_links = self.shorten_apk_links()
            
            # Step 3: Create blog post
            blog_post = None
            if not self.skip_blog.get() and self.is_processing:
                current_step += 1
                self.update_progress(current_step, total_steps, "Creating blog post...")
                blog_post = self.create_blog_post(video_info, shortened_links)
            
            # Step 4: Upload to TikTok
            if not self.skip_tiktok.get() and video_info and self.is_processing:
                current_step += 1
                self.update_progress(current_step, total_steps, "Uploading to TikTok...")
                tiktok_result = self.upload_to_tiktok(video_info, blog_post)
                if not tiktok_result:
                    raise Exception("TikTok upload failed - check logs for details")
            
            if self.is_processing:
                self.update_progress(100, 100, "Process completed successfully!")
                self.log_message("All tasks completed successfully!", "INFO")
                messagebox.showinfo("Success", "Content distribution completed successfully!")
            
        except Exception as e:
            self.log_message(f"Unexpected error: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        finally:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.is_processing = False
    
    def use_local_video(self):
        """Use local video file"""
        try:
            video_path = Path(self.local_video_path.get())
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Create video info structure similar to YouTube downloader
            video_info = {
                'file_path': str(video_path),
                'title': self.title.get(),
                'filename': video_path.name,
                'duration': None,  # Could be extracted with ffmpeg if needed
                'size': video_path.stat().st_size
            }
            
            self.log_message(f"Using local video: {video_path}", "INFO")
            return video_info
        except Exception as e:
            self.log_message(f"Error using local video: {str(e)}", "ERROR")
            if messagebox.askyesno("Error", f"Error using local video: {str(e)}\n\nContinue without video?"):
                return None
            else:
                raise e
    
    def download_youtube_video(self):
        """Download video from YouTube"""
        try:
            filename = sanitize_filename(self.title.get())
            downloader = YouTubeDownloader()
            video_info = downloader.download_video(self.youtube_url.get(), f"{filename}.mp4")
            
            self.log_message(f"Video downloaded: {video_info['file_path']}", "INFO")
            return video_info
        except Exception as e:
            self.log_message(f"Error downloading video: {str(e)}", "ERROR")
            if messagebox.askyesno("Error", f"Error downloading video: {str(e)}\n\nContinue without video?"):
                return None
            else:
                raise e
    
    def shorten_apk_links(self):
        """Shorten APK download links"""
        try:
            shortener = URLShortener()
            shortened_links = {}
            
            for name, url in self.apk_links:
                if not self.is_processing:
                    break
                shortened_url = shortener.shorten_url(url)
                shortened_links[name] = shortened_url
                self.log_message(f"Shortened: {name} - {shortened_url}", "INFO")
            
            return shortened_links
        except Exception as e:
            self.log_message(f"Error shortening links: {str(e)}", "ERROR")
            if messagebox.askyesno("Error", f"Error shortening links: {str(e)}\n\nContinue with original links?"):
                return {name: url for name, url in self.apk_links}
            else:
                raise e
    
    def create_blog_post(self, video_info, shortened_links):
        """Create a blog post"""
        try:
            content_generator = ContentGenerator()
            blog_content = content_generator.generate_blog_post(
                self.title.get(), video_info, shortened_links)
            
            blogger = BloggerPublisher()
            post = blogger.create_post(
                title=self.title.get(),
                content=blog_content,
                labels=["APK", "Download", "Mobile App"],
                is_draft=self.draft_mode.get()
            )
            
            self.log_message(f"Blog post created: {post['url']}", "INFO")
            return post
        except Exception as e:
            self.log_message(f"Error creating blog post: {str(e)}", "ERROR")
            if messagebox.askyesno("Error", f"Error creating blog post: {str(e)}\n\nContinue without blog post?"):
                return None
            else:
                raise e
    
    def upload_to_tiktok(self, video_info, blog_post):
        """Upload video to TikTok using new tiktok-uploader library"""
        try:
            content_generator = ContentGenerator()
            
            # Generate caption with or without blog URL
            if blog_post and blog_post.get('url'):
                caption = content_generator.generate_tiktok_caption(self.title.get(), blog_post['url'])
            else:
                # No blog post - generate caption without blog URL
                caption = content_generator.generate_tiktok_caption(self.title.get(), None)
            
            # Check for cookies.txt file
            cookies_file = "cookies.txt"
            if not os.path.exists(cookies_file):
                self.log_message("cookies.txt file not found. Creating empty file - please add your TikTok cookies.", "WARNING")
                # Create empty cookies file
                with open(cookies_file, 'w') as f:
                    f.write("# Add your TikTok cookies here\n")
            
            # Check if cookies file has actual content
            with open(cookies_file, 'r') as f:
                content = f.read().strip()
                if not content or content.startswith('#'):
                    self.log_message("cookies.txt is empty. TikTok upload may fail without proper authentication.", "WARNING")
            
            # Use new TikTok uploader with cookies authentication
            tiktok = NewTikTokUploader(
                cookies_file=cookies_file,
                session_id=TIKTOK_SESSION_ID,
                headless=False
            )
            
            # Add hashtags to make the video more discoverable
            hashtags = ["#viral", "#fyp", "#trending"]
            
            result = tiktok.upload_video(
                video_path=video_info['file_path'],
                caption=caption,
                hashtags=hashtags
            )
            
            if result['status'] == 'success':
                self.log_message(f"Video uploaded to TikTok successfully!", "INFO")
                return {'url': 'TikTok upload completed', 'status': 'success'}
            else:
                raise Exception(f"Upload failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_message(f"Error uploading to TikTok: {str(e)}", "ERROR")
            return None
    
    def update_progress(self, current, total, status):
        """Update progress bar and status"""
        progress = (current / total) * 100
        self.progress_var.set(progress)
        self.status_var.set(status)
        self.root.update_idletasks()
    
    def log_message(self, message, level="INFO"):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.log_queue.put(log_entry)
    
    def check_log_queue(self):
        """Check for new log messages"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.check_log_queue)
    
    def clear_log(self):
        """Clear the log display"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def open_settings(self):
        """Open settings dialog"""
        SettingsDialog(self.root)
    
    # Batch Uploader Methods
    def refresh_batch_profiles(self):
        """Refresh the list of batch upload profiles"""
        if not self.batch_uploader:
            return
            
        self.batch_profiles_listbox.delete(0, tk.END)
        try:
            profiles = self.batch_uploader.get_profiles()
            for profile_name in profiles:
                self.batch_profiles_listbox.insert(tk.END, profile_name)
        except Exception as e:
            self.log_message(f"Error loading batch profiles: {str(e)}", "ERROR")
    
    def add_batch_profile(self):
        """Add a new batch upload profile"""
        if not self.batch_uploader:
            messagebox.showerror("Error", "Batch uploader not available")
            return
            
        profile_name = simpledialog.askstring("New Profile", "Enter profile name:")
        if profile_name and profile_name.strip():
            try:
                success = self.batch_uploader.add_profile(profile_name.strip())
                if success:
                    self.refresh_batch_profiles()
                    self.log_message(f"Added profile: {profile_name}", "INFO")
                    
                    # Open browser for manual login
                    if messagebox.askyesno("Login Required", 
                                          f"Profile '{profile_name}' created. Open browser for login?"):
                        success = self.batch_uploader.login(profile_name.strip())
                        if success:
                            self.log_message(f"Login successful for {profile_name}", "INFO")
                        else:
                            self.log_message(f"Login failed for {profile_name}", "ERROR")
                else:
                    messagebox.showwarning("Warning", f"Profile '{profile_name}' already exists")
            except Exception as e:
                self.log_message(f"Error adding profile: {str(e)}", "ERROR")
                messagebox.showerror("Error", f"Failed to add profile: {str(e)}")
    
    def delete_batch_profile(self):
        """Delete selected batch upload profile"""
        if not self.batch_uploader:
            messagebox.showerror("Error", "Batch uploader not available")
            return
            
        selection = self.batch_profiles_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile to delete")
            return
        
        profile_name = self.batch_profiles_listbox.get(selection[0])
        if messagebox.askyesno("Confirm Delete", f"Delete profile '{profile_name}'?"):
            try:
                success = self.batch_uploader.remove_profile(profile_name)
                if success:
                    self.refresh_batch_profiles()
                    self.log_message(f"Deleted profile: {profile_name}", "INFO")
                else:
                    messagebox.showerror("Error", "Failed to delete profile")
            except Exception as e:
                self.log_message(f"Error deleting profile: {str(e)}", "ERROR")
                messagebox.showerror("Error", f"Failed to delete profile: {str(e)}")
    
    def configure_batch_video(self):
        """Configure video for selected profile"""
        selection = self.batch_profiles_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile to configure")
            return
        
        profile_name = self.batch_profiles_listbox.get(selection[0])
        
        # Show config frame
        self.batch_config_frame.pack(fill='x', pady=10)
        
        # Update selected profile label
        self.batch_selected_profile_label.config(text=f"Configuring: {profile_name}")
        
        # Load existing config if available
        self.batch_video_path_var.set("")
        self.batch_caption_var.set("")
        self.batch_hashtags_var.set("")
    
    def browse_batch_video(self):
        """Browse for video file for batch upload"""
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv")]
        )
        if file_path:
            self.batch_video_path_var.set(file_path)
    
    def save_batch_config(self):
        """Save video configuration for selected profile"""
        profile_text = self.batch_selected_profile_label.cget("text")
        if not profile_text.startswith("Configuring:"):
            messagebox.showwarning("Warning", "No profile selected for configuration")
            return
        
        profile_name = profile_text.replace("Configuring: ", "")
        video_path = self.batch_video_path_var.get()
        caption = self.batch_caption_var.get()
        hashtags = self.batch_hashtags_var.get()
        
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Error", "Please select a valid video file")
            return
        
        # Store configuration
        self.batch_configs[profile_name] = {
            'video_path': video_path,
            'caption': caption,
            'hashtags': [tag.strip() for tag in hashtags.split(',') if tag.strip()]
        }
        
        messagebox.showinfo("Success", f"Configuration saved for {profile_name}")
        self.log_message(f"Video configuration saved for {profile_name}", "INFO")
        
        # Hide config frame
        self.batch_config_frame.pack_forget()
    
    def start_batch_upload_process(self):
        """Start batch upload process for selected profiles"""
        if not self.batch_uploader:
            messagebox.showerror("Error", "Batch uploader not available")
            return
            
        selection = self.batch_profiles_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select profiles to upload")
            return
        
        selected_profiles = [self.batch_profiles_listbox.get(idx) for idx in selection]
        
        # Check if all selected profiles have configurations
        unconfigured = [profile for profile in selected_profiles 
                       if profile not in self.batch_configs]
        
        if unconfigured:
            messagebox.showerror("Error", 
                               f"Please configure videos for these profiles first:\n{', '.join(unconfigured)}")
            return
        
        # Start upload in separate thread
        self.batch_upload_running = True
        threading.Thread(target=self.run_batch_upload_process, 
                        args=(selected_profiles,), daemon=True).start()
        
        self.log_message(f"Starting batch upload for {len(selected_profiles)} profiles", "INFO")
    
    def run_batch_upload_process(self, selected_profiles):
        """Run the batch upload process"""
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            # Update status
            self.batch_status_text.config(state=tk.NORMAL)
            self.batch_status_text.insert(tk.END, f"Starting batch upload for {len(selected_profiles)} profiles...\n")
            self.batch_status_text.see(tk.END)
            self.batch_status_text.config(state=tk.DISABLED)
            
            # Use ThreadPoolExecutor for parallel uploads
            max_workers = min(len(selected_profiles), 3)  # Max 3 concurrent uploads
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit upload tasks
                future_to_profile = {}
                for profile in selected_profiles:
                    if not self.batch_upload_running:
                        break
                    
                    config = self.batch_configs[profile]
                    future = executor.submit(
                        self.upload_single_profile,
                        profile,
                        config['video_path'],
                        config['caption'],
                        config['hashtags']
                    )
                    future_to_profile[future] = profile
                
                # Process results as they complete
                for future in as_completed(future_to_profile):
                    if not self.batch_upload_running:
                        break
                    
                    profile = future_to_profile[future]
                    try:
                        result = future.result()
                        status = "SUCCESS" if result.success else "FAILED"
                        message = f"Profile {profile}: {status} - {result.message}\n"
                        
                        self.batch_status_text.config(state=tk.NORMAL)
                        self.batch_status_text.insert(tk.END, message)
                        self.batch_status_text.see(tk.END)
                        self.batch_status_text.config(state=tk.DISABLED)
                        
                        self.log_message(f"Upload {status.lower()} for {profile}: {result.message}", 
                                       "INFO" if result.success else "ERROR")
                        
                    except Exception as e:
                        error_msg = f"Profile {profile}: ERROR - {str(e)}\n"
                        self.batch_status_text.config(state=tk.NORMAL)
                        self.batch_status_text.insert(tk.END, error_msg)
                        self.batch_status_text.see(tk.END)
                        self.batch_status_text.config(state=tk.DISABLED)
                        
                        self.log_message(f"Upload error for {profile}: {str(e)}", "ERROR")
            
            if self.batch_upload_running:
                completion_msg = "Batch upload process completed!\n"
                self.batch_status_text.config(state=tk.NORMAL)
                self.batch_status_text.insert(tk.END, completion_msg)
                self.batch_status_text.see(tk.END)
                self.batch_status_text.config(state=tk.DISABLED)
                
                self.log_message("Batch upload process completed", "INFO")
                messagebox.showinfo("Complete", "Batch upload process has finished!")
            
        except Exception as e:
            error_msg = f"Batch upload error: {str(e)}\n"
            self.batch_status_text.config(state=tk.NORMAL)
            self.batch_status_text.insert(tk.END, error_msg)
            self.batch_status_text.see(tk.END)
            self.batch_status_text.config(state=tk.DISABLED)
            
            self.log_message(f"Batch upload error: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Batch upload failed: {str(e)}")
        finally:
            self.batch_upload_running = False
    
    def upload_single_profile(self, profile_name, video_path, caption, hashtags):
        """Upload video for a single profile"""
        try:
            # Use the enhanced uploader for the upload
            result = self.batch_uploader.upload_video(
                video_path=video_path,
                caption=caption,
                hashtags=hashtags,
                profile_name=profile_name
            )
            return result
        except Exception as e:
            # Return a failed result
            from batch_uploader.tiktok_uploader.enhanced_uploader import UploadResult, UploadStatus
            return UploadResult(
                success=False,
                message=str(e),
                status=UploadStatus.FAILED,
                profile=profile_name,
                timestamp=time.time()
            )
    
    def stop_batch_upload(self):
        """Stop the batch upload process"""
        self.batch_upload_running = False
        self.log_message("Batch upload process stopped by user", "WARNING")
        
        status_msg = "Upload process stopped by user\n"
        self.batch_status_text.config(state=tk.NORMAL)
        self.batch_status_text.insert(tk.END, status_msg)
        self.batch_status_text.see(tk.END)
        self.batch_status_text.config(state=tk.DISABLED)


class APKLinkDialog:
    def __init__(self, parent):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add APK Link")
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Variables
        self.name_var = tk.StringVar()
        self.url_var = tk.StringVar()
        
        # Create widgets
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Link Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, pady=5)
        
        ttk.Label(main_frame, text="APK URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.url_var, width=40).grid(row=1, column=1, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)
        
        # Focus on name entry
        self.dialog.focus_set()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def ok_clicked(self):
        name = self.name_var.get().strip()
        url = self.url_var.get().strip()
        
        if not name or not url:
            messagebox.showwarning("Warning", "Please fill in both fields")
            return
        
        self.result = (name, url)
        self.dialog.destroy()
    
    def cancel_clicked(self):
        self.dialog.destroy()


class SettingsDialog:
    def __init__(self, parent):
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Directories tab
        dir_frame = ttk.Frame(notebook, padding="10")
        notebook.add(dir_frame, text="Directories")
        
        ttk.Label(dir_frame, text="Download Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(dir_frame, text=str(DOWNLOAD_DIR)).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(dir_frame, text="Temp Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(dir_frame, text=str(TEMP_DIR)).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # TikTok tab
        tiktok_frame = ttk.Frame(notebook, padding="10")
        notebook.add(tiktok_frame, text="TikTok")

        self.tiktok_session_id = tk.StringVar()

        ttk.Label(tiktok_frame, text="TikTok sessionid:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(tiktok_frame, textvariable=self.tiktok_session_id, width=60).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        # Configuration tab
        config_frame = ttk.Frame(notebook, padding="10")
        notebook.add(config_frame, text="Configuration")
        
        ttk.Label(config_frame, text="Configuration file: .env", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        ttk.Label(config_frame, text="Please edit the .env file directly to change API keys and credentials.").grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Button(config_frame, text="Open .env File", command=self.open_env_file).grid(
            row=2, column=0, pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

        self.load_settings()
    
    def load_settings(self):
        """Load settings from .env file"""
        from dotenv import get_key
        session_id = get_key('.env', 'TIKTOK_SESSION_ID')
        if session_id:
            self.tiktok_session_id.set(session_id)

    def save_settings(self):
        """Save settings to .env file"""
        from dotenv import set_key
        set_key('.env', 'TIKTOK_SESSION_ID', self.tiktok_session_id.get())
        messagebox.showinfo("Settings Saved", "Settings have been saved successfully.")
        self.dialog.destroy()
    
    def open_env_file(self):
        """Open .env file in default editor"""
        env_path = Path(".env")
        if env_path.exists():
            os.startfile(str(env_path))
        else:
            messagebox.showwarning("Warning", ".env file not found")


def main():
    """Main function to run the GUI"""
    root = tk.Tk()
    app = ContentDistributionGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
