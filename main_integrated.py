#!/usr/bin/env python3
"""
Integrated TikTok Upload Manager - Main GUI with Full Content Processing
"""
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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

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

# Import batch uploader
try:
    from batch_uploader.tiktok_uploader.enhanced_uploader import EnhancedTikTokUploader
    from batch_uploader.batch_gui import Dashboard as BatchDashboard
except ImportError as e:
    EnhancedTikTokUploader = None
    BatchDashboard = None
    print(f"Warning: Could not import batch uploader components: {e}")


class LogHandler(logging.Handler):
    """Custom logging handler for GUI"""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        log_entry = self.format(record)
        self.log_queue.put(log_entry)


class IntegratedContentGUI:
    """Enhanced Content Distribution GUI with integrated TikTok batch upload"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Content Distribution Tool - Integrated")
        self.root.geometry("1000x800")
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
        
        # Batch uploader variables
        self.batch_upload_running = False
        self.batch_configs = {}
        self.selected_tiktok_profiles = []
        
        # Initialize batch uploader
        self.batch_uploader = None
        if EnhancedTikTokUploader:
            try:
                self.batch_uploader = EnhancedTikTokUploader()
                print("Batch uploader initialized successfully")
            except Exception as e:
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
        title_label = ttk.Label(main_frame, text="Integrated Content Distribution Tool", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(1, weight=1)
        
        # Create tabs
        self.create_content_distribution_tab()
        self.create_tiktok_profiles_tab()
        self.create_standalone_batch_tab()
    
    def create_content_distribution_tab(self):
        """Create the enhanced content distribution tab"""
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
        
        # TikTok Profile Selection Section
        tiktok_frame = ttk.LabelFrame(tab, text="TikTok Upload Settings", padding="10")
        tiktok_frame.pack(fill='x', pady=10)
        tiktok_frame.columnconfigure(1, weight=1)
        
        ttk.Label(tiktok_frame, text="Select TikTok profiles for upload:", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Profile selection listbox
        profile_list_frame = ttk.Frame(tiktok_frame)
        profile_list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        profile_list_frame.columnconfigure(0, weight=1)
        
        self.tiktok_profiles_listbox = tk.Listbox(profile_list_frame, height=4, selectmode='multiple')
        self.tiktok_profiles_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        tiktok_scrollbar = ttk.Scrollbar(profile_list_frame, orient=tk.VERTICAL, command=self.tiktok_profiles_listbox.yview)
        tiktok_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tiktok_profiles_listbox.configure(yscrollcommand=tiktok_scrollbar.set)
        
        # Profile management buttons
        profile_btn_frame = ttk.Frame(tiktok_frame)
        profile_btn_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Button(profile_btn_frame, text="Refresh Profiles", command=self.refresh_tiktok_profiles).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(profile_btn_frame, text="Manage Profiles", command=self.switch_to_profiles_tab).grid(row=0, column=1, padx=(0, 5))
        
        # Upload method selection
        self.upload_method = tk.StringVar(value="single")
        ttk.Radiobutton(tiktok_frame, text="Single Profile Upload (original method)", 
                       variable=self.upload_method, value="single").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(tiktok_frame, text="Multi-Profile Upload (selected profiles)", 
                       variable=self.upload_method, value="multi").grid(row=4, column=0, sticky=tk.W, pady=2)
        
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
        self.refresh_tiktok_profiles()
    
    def create_tiktok_profiles_tab(self):
        """Create TikTok profiles management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="TikTok Profiles")
        
        # Check if batch uploader is available
        if not self.batch_uploader:
            error_label = ttk.Label(tab, text="Batch Uploader not available\nPlease check configuration", justify='center')
            error_label.pack(expand=True)
            return
        
        # Profile Management Frame
        profile_frame = ttk.LabelFrame(tab, text="TikTok Profile Management", padding="15")
        profile_frame.pack(fill='both', expand=True, pady=20)
        
        # Instructions
        instruction_text = """
        Manage your TikTok profiles for batch uploading:
        1. Add TikTok profiles using different browser profiles
        2. Test login for each profile to ensure they work
        3. Select profiles in Content Distribution tab for multi-upload
        """
        ttk.Label(profile_frame, text=instruction_text, 
                 justify='left', foreground='blue').pack(anchor='w', pady=10)
        
        # Profile list
        list_frame = ttk.Frame(profile_frame)
        list_frame.pack(fill='both', expand=True, pady=10)
        
        ttk.Label(list_frame, text="TikTok Profiles:", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        # Listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill='both', expand=True, pady=5)
        
        self.profile_listbox = tk.Listbox(list_container, height=10, selectmode='single')
        self.profile_listbox.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=self.profile_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.profile_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Buttons
        btn_frame = ttk.Frame(profile_frame)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="Add Profile", 
                  command=self.add_profile).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Remove Profile", 
                  command=self.remove_profile).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Test Login", 
                  command=self.test_profile_login).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Refresh List", 
                  command=self.refresh_profile_list).pack(side='left', padx=5)
        
        # Load existing profiles
        self.refresh_profile_list()
    
    def create_standalone_batch_tab(self):
        """Create standalone batch upload tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Standalone Batch Upload")
        
        try:
            if BatchDashboard is None:
                raise ImportError("BatchDashboard not available")
            
            # Create batch dashboard
            self.batch_gui = BatchDashboard(tab)
            
        except Exception as e:
            error_frame = ttk.Frame(tab)
            error_frame.pack(expand=True, fill='both', padx=20, pady=20)
            
            ttk.Label(error_frame,
                     text=f"Batch Upload Error\n\n{str(e)}\n\nPlease check your installation and dependencies.",
                     justify='center',
                     foreground='red',
                     wraplength=400).pack(expand=True)
    
    # ... (copy all the content processing methods from gui_main.py)
    
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
        
        # Validate TikTok upload settings if not skipping
        if not self.skip_tiktok.get() and self.upload_method.get() == "multi":
            selected_profiles = [self.tiktok_profiles_listbox.get(i) for i in self.tiktok_profiles_listbox.curselection()]
            if not selected_profiles:
                messagebox.showerror("Error", "Please select TikTok profiles for multi-upload or switch to single upload mode")
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
        """Main content processing function with integrated TikTok multi-upload"""
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
            
            # Step 4: Upload to TikTok (enhanced with multi-profile support)
            if not self.skip_tiktok.get() and video_info and self.is_processing:
                current_step += 1
                self.update_progress(current_step, total_steps, "Uploading to TikTok...")
                tiktok_result = self.upload_to_tiktok_enhanced(video_info, blog_post)
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
    
    def upload_to_tiktok_enhanced(self, video_info, blog_post):
        """Enhanced TikTok upload with single or multi-profile support"""
        if self.upload_method.get() == "multi":
            return self.upload_to_multiple_profiles(video_info, blog_post)
        else:
            return self.upload_to_tiktok_single(video_info, blog_post)
    
    def upload_to_tiktok_single(self, video_info, blog_post):
        """Upload video to TikTok using single profile (original method)"""
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
    
    def upload_to_multiple_profiles(self, video_info, blog_post):
        """Upload video to multiple selected TikTok profiles"""
        selected_indices = self.tiktok_profiles_listbox.curselection()
        if not selected_indices:
            self.log_message("No profiles selected for multi-upload", "WARNING")
            return None
        
        selected_profiles = [self.tiktok_profiles_listbox.get(i) for i in selected_indices]
        
        if not self.batch_uploader:
            self.log_message("Batch uploader not available for multi-profile upload", "ERROR")
            return None
        
        self.log_message(f"Starting multi-profile upload to {len(selected_profiles)} profiles", "INFO")
        
        # Generate caption
        caption = self.title.get()
        try:
            content_generator = ContentGenerator()
            
            if blog_post and blog_post.get('url'):
                caption = content_generator.generate_tiktok_caption(self.title.get(), blog_post['url'])
            else:
                caption = content_generator.generate_tiktok_caption(self.title.get(), None)
        except Exception as e:
            self.log_message(f"Error generating caption, using title: {e}", "WARNING")
        
        def batch_upload():
            success_count = 0
            results = []
            
            for profile_name in selected_profiles:
                if not self.is_processing:
                    break
                    
                try:
                    self.log_message(f"Uploading to profile: {profile_name}", "INFO")
                    
                    result = self.batch_uploader.upload_video(
                        video_path=video_info['file_path'],
                        caption=caption,
                        hashtags=['viral', 'fyp', 'trending'],
                        profile_name=profile_name
                    )
                    
                    if result.success:
                        success_count += 1
                        self.log_message(f"✓ Upload successful for {profile_name}", "INFO")
                    else:
                        self.log_message(f"✗ Upload failed for {profile_name}: {result.message}", "ERROR")
                    
                    results.append({
                        'profile': profile_name,
                        'success': result.success,
                        'message': result.message
                    })
                    
                except Exception as e:
                    self.log_message(f"✗ Upload error for {profile_name}: {str(e)}", "ERROR")
                    results.append({
                        'profile': profile_name,
                        'success': False,
                        'message': str(e)
                    })
            
            # Show summary
            total = len(selected_profiles)
            self.log_message(f"Multi-profile upload completed: {success_count}/{total} successful", "INFO")
            
            # Schedule GUI update in main thread
            if hasattr(self.root, 'after'):
                self.root.after(0, lambda: self.show_upload_summary(success_count, total))
        
        # Run in background thread
        threading.Thread(target=batch_upload, daemon=True).start()
        
        return {'status': 'processing', 'message': f'Multi-profile upload started for {len(selected_profiles)} profiles...'}
    
    def show_upload_summary(self, success_count, total):
        """Show upload summary in main thread"""
        if success_count > 0:
            messagebox.showinfo("Upload Complete", 
                              f"Multi-profile upload completed!\n"
                              f"Successful: {success_count}/{total} profiles\n"
                              f"Check log for details.")
        else:
            messagebox.showerror("Upload Failed", 
                               f"All uploads failed!\n"
                               f"Check log for details.")
    
    def refresh_tiktok_profiles(self):
        """Refresh TikTok profiles list in content distribution tab"""
        if not self.batch_uploader:
            return
            
        self.tiktok_profiles_listbox.delete(0, tk.END)
        try:
            profiles = self.batch_uploader.get_profiles()
            for profile_name in profiles:
                self.tiktok_profiles_listbox.insert(tk.END, profile_name)
        except Exception as e:
            self.log_message(f"Error loading TikTok profiles: {str(e)}", "ERROR")
    
    def switch_to_profiles_tab(self):
        """Switch to TikTok Profiles tab"""
        # Find the TikTok Profiles tab and select it
        for i in range(self.notebook.index("end")):
            tab_text = self.notebook.tab(i, "text")
            if "TikTok Profiles" in tab_text:
                self.notebook.select(i)
                break
    
    # TikTok Profile Management Methods
    def add_profile(self):
        """Add a new TikTok profile"""
        if not self.batch_uploader:
            messagebox.showerror("Error", "Batch uploader not available")
            return
        
        profile_name = simpledialog.askstring("Add Profile", "Enter profile name:")
        if profile_name and profile_name.strip():
            try:
                success = self.batch_uploader.add_profile(profile_name.strip())
                if success:
                    self.refresh_profile_list()
                    self.refresh_tiktok_profiles()
                    self.log_message(f"Profile '{profile_name}' added successfully", "INFO")
                    
                    # Ask if user wants to configure login immediately
                    if messagebox.askyesno("Setup Login", 
                                          f"Profile '{profile_name}' created.\n\nDo you want to setup login for this profile now?"):
                        self.setup_profile_login(profile_name.strip())
                else:
                    messagebox.showwarning("Warning", f"Profile '{profile_name}' already exists")
            except Exception as e:
                self.log_message(f"Error adding profile: {str(e)}", "ERROR")
                messagebox.showerror("Error", f"Failed to add profile: {str(e)}")
    
    def setup_profile_login(self, profile_name):
        """Setup login for a TikTok profile by opening Chrome and waiting for user confirmation"""
        try:
            self.log_message(f"Setting up login for profile: {profile_name}", "INFO")
            
            # Show instruction dialog
            instruction_msg = f"""Setting up login for profile: {profile_name}

Steps:
1. Chrome will open with TikTok login page
2. Log in to your TikTok account
3. Complete any 2FA or verification if required
4. Once logged in successfully, click 'Confirm Login' below
5. Profile data will be saved automatically

Note: Keep the Chrome window open until you confirm the login."""
            
            # Create login confirmation dialog
            login_dialog = LoginConfirmationDialog(self.root, profile_name, instruction_msg)
            
            # Open Chrome with TikTok login in a separate thread
            threading.Thread(target=self.open_tiktok_login, args=(profile_name,), daemon=True).start()
            
            # Wait for user confirmation
            if login_dialog.confirmed:
                # Save profile data
                success = self.save_profile_login_data(profile_name)
                if success:
                    self.log_message(f"Login setup completed for profile: {profile_name}", "INFO")
                    messagebox.showinfo("Success", f"Login setup completed for '{profile_name}'!")
                else:
                    self.log_message(f"Failed to save login data for profile: {profile_name}", "ERROR")
                    messagebox.showerror("Error", f"Failed to save login data for '{profile_name}'")
            else:
                self.log_message(f"Login setup cancelled for profile: {profile_name}", "WARNING")
                
        except Exception as e:
            self.log_message(f"Error setting up login for {profile_name}: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Failed to setup login: {str(e)}")
    
    def open_tiktok_login(self, profile_name):
        """Open Chrome with TikTok login page using the profile"""
        try:
            # TikTok login URL
            tiktok_url = "https://www.tiktok.com/login"
            
            # Try to get Chrome executable path
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME')),
            ]
            
            chrome_exe = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_exe = path
                    break
            
            if not chrome_exe:
                # Fallback to default browser
                self.log_message("Chrome not found, opening in default browser", "WARNING")
                import webbrowser
                webbrowser.open(tiktok_url)
                return
            
            # Create profile directory for Chrome
            profile_dir = Path(f"./chrome_profiles/{profile_name}")
            profile_dir.mkdir(parents=True, exist_ok=True)
            
            # Chrome arguments
            chrome_args = [
                chrome_exe,
                f"--user-data-dir={profile_dir.absolute()}",
                f"--profile-directory={profile_name}",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--no-first-run",
                "--no-default-browser-check",
                tiktok_url
            ]
            
            # Launch Chrome
            import subprocess
            subprocess.Popen(chrome_args)
            self.log_message(f"Chrome opened for profile {profile_name} at {tiktok_url}", "INFO")
            
        except Exception as e:
            self.log_message(f"Error opening Chrome for {profile_name}: {str(e)}", "ERROR")
            # Fallback to default browser
            import webbrowser
            webbrowser.open("https://www.tiktok.com/login")
    
    def save_profile_login_data(self, profile_name):
        """Save the profile login data after successful login"""
        try:
            if not self.batch_uploader:
                return False
            
            # Update profile data in batch uploader
            # This method should be implemented in the batch uploader to mark profile as logged in
            if hasattr(self.batch_uploader, 'update_profile_login_status'):
                success = self.batch_uploader.update_profile_login_status(profile_name, True)
            else:
                # Fallback - just mark as successful
                success = True
            
            if success:
                self.log_message(f"Profile login data saved for: {profile_name}", "INFO")
                
                # Refresh profile lists
                self.refresh_profile_list()
                self.refresh_tiktok_profiles()
                
                return True
            else:
                self.log_message(f"Failed to save profile data for: {profile_name}", "ERROR")
                return False
                
        except Exception as e:
            self.log_message(f"Error saving profile data for {profile_name}: {str(e)}", "ERROR")
            return False
    
    def test_profile_login(self):
        """Test login for selected profile with Chrome browser"""
        if not self.batch_uploader or not hasattr(self, 'profile_listbox'):
            return
        
        selected = self.profile_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a profile to test")
            return
        
        profile_name = self.profile_listbox.get(selected[0])
        
        # Ask user what kind of test they want
        test_choice = messagebox.askyesnocancel(
            "Test Login Method",
            f"Test login for '{profile_name}':\n\n"
            "Yes: Open Chrome browser for manual login test\n"
            "No: Automated login test (existing method)\n"
            "Cancel: Cancel test"
        )
        
        if test_choice is None:  # Cancel
            return
        elif test_choice:  # Yes - Chrome browser test
            self.test_profile_login_chrome(profile_name)
        else:  # No - Automated test
            self.test_profile_login_automated(profile_name)
    
    def test_profile_login_chrome(self, profile_name):
        """Test profile login using Chrome browser"""
        try:
            self.log_message(f"Testing login for profile (Chrome): {profile_name}", "INFO")
            
            # Show instruction dialog
            instruction_msg = f"""Testing login for profile: {profile_name}

Steps:
1. Chrome will open with your saved profile
2. Navigate to TikTok and verify you're logged in
3. If not logged in, please log in again
4. Click 'Confirm Test' when ready

This will verify if the profile login is working correctly."""
            
            # Create test confirmation dialog
            test_dialog = LoginConfirmationDialog(
                self.root, 
                profile_name, 
                instruction_msg,
                title="Test Profile Login",
                confirm_text="Confirm Test"
            )
            
            # Open Chrome with the profile
            threading.Thread(target=self.open_chrome_with_profile, args=(profile_name,), daemon=True).start()
            
            # Handle result
            if test_dialog.confirmed:
                self.log_message(f"Login test confirmed for profile: {profile_name}", "INFO")
                messagebox.showinfo("Test Complete", f"Login test completed for '{profile_name}'")
            else:
                self.log_message(f"Login test cancelled for profile: {profile_name}", "WARNING")
                
        except Exception as e:
            self.log_message(f"Error testing login for {profile_name}: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Failed to test login: {str(e)}")
    
    def open_chrome_with_profile(self, profile_name):
        """Open Chrome with existing profile data"""
        try:
            # Try to get Chrome executable path
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME')),
            ]
            
            chrome_exe = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_exe = path
                    break
            
            if not chrome_exe:
                self.log_message("Chrome not found", "ERROR")
                return
            
            # Profile directory
            profile_dir = Path(f"./chrome_profiles/{profile_name}")
            
            # Chrome arguments
            chrome_args = [
                chrome_exe,
                f"--user-data-dir={profile_dir.absolute()}",
                f"--profile-directory={profile_name}",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--no-first-run",
                "--no-default-browser-check",
                "https://www.tiktok.com"
            ]
            
            # Launch Chrome
            import subprocess
            subprocess.Popen(chrome_args)
            self.log_message(f"Chrome opened with profile: {profile_name}", "INFO")
            
        except Exception as e:
            self.log_message(f"Error opening Chrome with profile {profile_name}: {str(e)}", "ERROR")
    
    def test_profile_login_automated(self, profile_name):
        """Test profile login using automated method (original)"""
        def test_login():
            try:
                self.log_message(f"Testing login for profile (automated): {profile_name}", "INFO")
                success = self.batch_uploader.login(profile_name)
                
                # Schedule GUI update in main thread
                if hasattr(self.root, 'after'):
                    self.root.after(0, lambda: self.handle_login_result(profile_name, success))
                else:
                    self.handle_login_result(profile_name, success)
                
            except Exception as e:
                error_msg = str(e)
                if hasattr(self.root, 'after'):
                    self.root.after(0, lambda: self.handle_login_error(profile_name, error_msg))
                else:
                    self.handle_login_error(profile_name, error_msg)
            finally:
                if self.batch_uploader and hasattr(self.batch_uploader, 'driver') and self.batch_uploader.driver:
                    self.batch_uploader.close()
        
        # Run in thread to avoid blocking GUI
        threading.Thread(target=test_login, daemon=True).start()

    def handle_login_result(self, profile_name, success):
        """Handle login test result in main thread"""
        if success:
            self.log_message(f"Login successful for profile: {profile_name}", "INFO")
            messagebox.showinfo("Success", f"Login successful for '{profile_name}'")
        else:
            self.log_message(f"Login failed for profile: {profile_name}", "ERROR")
            messagebox.showerror("Error", f"Login failed for '{profile_name}'\n\nPlease log in manually in the browser window.")
    
    def handle_login_error(self, profile_name, error_msg):
        """Handle login test error in main thread"""
        self.log_message(f"Login error for {profile_name}: {error_msg}", "ERROR")
        messagebox.showerror("Error", f"Login error for '{profile_name}':\n{error_msg}")
    
    def remove_profile(self):
        """Remove selected TikTok profile"""
        if not self.batch_uploader or not hasattr(self, 'profile_listbox'):
            return
        
        selected = self.profile_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a profile to remove")
            return
        
        profile_name = self.profile_listbox.get(selected[0])
        if messagebox.askyesno("Confirm", f"Remove profile '{profile_name}'?"):
            try:
                success = self.batch_uploader.remove_profile(profile_name)
                if success:
                    self.refresh_profile_list()
                    self.refresh_tiktok_profiles()
                    self.log_message(f"Profile '{profile_name}' removed", "INFO")
                    messagebox.showinfo("Success", f"Profile '{profile_name}' removed")
                else:
                    messagebox.showerror("Error", "Failed to remove profile")
            except Exception as e:
                self.log_message(f"Error removing profile: {str(e)}", "ERROR")
                messagebox.showerror("Error", f"Failed to remove profile: {str(e)}")
    
    def refresh_profile_list(self):
        """Refresh the profile list in profiles tab"""
        if not self.batch_uploader or not hasattr(self, 'profile_listbox'):
            return
        
        self.profile_listbox.delete(0, tk.END)
        try:
            profiles = self.batch_uploader.get_profiles()
            for profile in profiles:
                self.profile_listbox.insert(tk.END, profile)
        except Exception as e:
            self.log_message(f"Error loading profiles: {e}", "ERROR")
    
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


class LoginConfirmationDialog:
    """Dialog for confirming TikTok login completion"""
    
    def __init__(self, parent, profile_name, instruction_text, title="Setup TikTok Login", confirm_text="Confirm Login"):
        self.confirmed = False
        self.profile_name = profile_name
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        # Create main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Profile name label
        profile_label = ttk.Label(main_frame, text=f"Profile: {profile_name}", 
                                 font=('Arial', 12, 'bold'), foreground='blue')
        profile_label.pack(pady=(0, 10))
        
        # Instruction text
        instruction_label = ttk.Label(main_frame, text=instruction_text, 
                                     justify='left', wraplength=450)
        instruction_label.pack(pady=(0, 20), fill='x')
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.pack(fill='x', pady=(0, 20))
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=6, state=tk.DISABLED)
        self.status_text.pack(fill='both', expand=True)
        
        # Add initial status
        self.add_status("Waiting for Chrome to open...")
        self.add_status("Please complete the login process in Chrome")
        self.add_status("Click 'Confirm Login' when you're successfully logged in")
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=(10, 0))
        
        # Confirm button
        self.confirm_btn = ttk.Button(btn_frame, text=confirm_text, 
                                     command=self.confirm_login, style='Accent.TButton')
        self.confirm_btn.pack(side='left', padx=(0, 10))
        
        # Cancel button
        ttk.Button(btn_frame, text="Cancel", command=self.cancel_login).pack(side='left')
        
        # Help button
        ttk.Button(btn_frame, text="Help", command=self.show_help).pack(side='right')
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel_login)
        
        # Focus on confirm button
        self.confirm_btn.focus_set()
        
        # Update status periodically
        self.update_status_timer()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def add_status(self, message):
        """Add status message to the status text"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_msg = f"[{timestamp}] {message}\n"
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, status_msg)
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def update_status_timer(self):
        """Update status periodically"""
        if self.dialog.winfo_exists():
            # Check if Chrome process is running (optional)
            # You could add logic here to check Chrome process status
            
            # Schedule next update
            self.dialog.after(5000, self.update_status_timer)  # Update every 5 seconds
    
    def confirm_login(self):
        """Handle login confirmation"""
        # Ask for final confirmation
        confirm = messagebox.askyesno(
            "Confirm Login",
            f"Are you sure you have successfully logged in to TikTok for profile '{self.profile_name}'?\n\n"
            "This will save the current browser session data for future uploads.",
            parent=self.dialog
        )
        
        if confirm:
            self.add_status("Login confirmed by user")
            self.add_status("Saving profile data...")
            self.confirmed = True
            self.dialog.destroy()
    
    def cancel_login(self):
        """Handle login cancellation"""
        confirm = messagebox.askyesno(
            "Cancel Setup",
            f"Are you sure you want to cancel the login setup for profile '{self.profile_name}'?",
            parent=self.dialog
        )
        
        if confirm:
            self.add_status("Login setup cancelled")
            self.confirmed = False
            self.dialog.destroy()
    
    def show_help(self):
        """Show help information"""
        help_text = """TikTok Login Setup Help:

1. Chrome Browser Window:
   - A Chrome window should have opened automatically
   - If not, check if Chrome is installed correctly

2. Login Process:
   - Go to TikTok login page (should open automatically)
   - Enter your TikTok username and password
   - Complete any 2FA verification if prompted
   - Make sure you see your TikTok profile/dashboard

3. Common Issues:
   - If Chrome doesn't open: Check Chrome installation
   - If login fails: Try clearing browser cache
   - For 2FA: Use your phone app or SMS verification

4. After Successful Login:
   - You should see your TikTok homepage
   - Your profile picture should be visible
   - Click 'Confirm Login' in this dialog

5. Security Note:
   - This saves your login session locally
   - Data is stored only on your computer
   - Used for automated video uploads"""
        
        messagebox.showinfo("Help - TikTok Login Setup", help_text, parent=self.dialog)

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
        try:
            from dotenv import get_key
            session_id = get_key('.env', 'TIKTOK_SESSION_ID')
            if session_id:
                self.tiktok_session_id.set(session_id)
        except:
            pass

    def save_settings(self):
        """Save settings to .env file"""
        try:
            from dotenv import set_key
            set_key('.env', 'TIKTOK_SESSION_ID', self.tiktok_session_id.get())
            messagebox.showinfo("Settings Saved", "Settings have been saved successfully.")
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def open_env_file(self):
        """Open .env file in default editor"""
        env_path = Path(".env")
        if env_path.exists():
            os.startfile(str(env_path))
        else:
            messagebox.showwarning("Warning", ".env file not found")


def main():
    """Main entry point"""
    try:
        root = tk.Tk()
        app = IntegratedContentGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"Error starting integrated GUI: {e}")
        messagebox.showerror("Error", f"Failed to start GUI: {e}")


if __name__ == "__main__":
    main()
