#!/usr/bin/env python3
import sys
import os
from pathlib import Path
from functools import partial
from typing import Dict, List, Tuple

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QTabWidget, QRadioButton, QGroupBox,
    QTextEdit, QListWidget, QListWidgetItem, QMessageBox, QCheckBox, QProgressBar,
    QFormLayout, QDialog, QDialogButtonBox, QStyle, QComboBox, QButtonGroup
)
from PyQt5.QtGui import QPalette, QColor

# Project imports
from config import validate_config
from services.youtube import YouTubeDownloader
from services.shortener import URLShortener
from services.ai import ContentGenerator
from services.blogger import BloggerPublisher, WordPressPublisher
from services.tiktok import TikTokService
from utils import sanitize_filename, clean_temp_dir
from qt_ai_settings import AISettingsDialog


class APKLinkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add APK Link")
        self.setModal(True)
        self.name_edit = QLineEdit(self)
        self.url_edit = QLineEdit(self)

        form = QFormLayout()
        form.addRow("Link Name:", self.name_edit)
        form.addRow("APK URL:", self.url_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_result(self) -> Tuple[str, str]:
        return self.name_edit.text().strip(), self.url_edit.text().strip()


class ContentPreviewDialog(QDialog):
    """Dialog to preview and approve/regenerate AI-generated content before posting"""

    def __init__(self, title: str, content: str, parent=None, language: str = "vietnamese", images: list = None):
        super().__init__(parent)
        self.setWindowTitle("Preview Blog Content")
        self.setModal(True)
        self.resize(900, 700)
        self.approved = False
        self.regenerate = False
        self.images = images or []

        # Create layout
        layout = QVBoxLayout()

        # Language indicator
        lang_flag = "🇻🇳 Vietnamese" if language == "vietnamese" else "🇺🇸 English"
        image_info = f" | 🖼️ {len(self.images)} image(s)" if self.images else ""

        # Title section
        title_label = QLabel(f"<h2>📝 Preview: {title}</h2><p style='color: #8ecae6;'>Language: {lang_flag}{image_info}</p>")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Info label
        info_label = QLabel("Review the AI-generated content below. You can approve it to proceed with posting, or regenerate to create new content.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #8ecae6; padding: 10px; background-color: rgba(142, 202, 230, 0.1); border-radius: 4px;")
        layout.addWidget(info_label)

        # Tab widget for HTML and Rendered view
        tabs = QTabWidget()

        # HTML source tab
        html_tab = QWidget()
        html_layout = QVBoxLayout(html_tab)
        self.content_edit = QTextEdit()
        self.content_edit.setPlainText(content)
        self.content_edit.setFont(__import__('PyQt5.QtGui', fromlist=['QFont']).QFont("Consolas", 10))
        html_layout.addWidget(self.content_edit)
        tabs.addTab(html_tab, "HTML Source")

        # Rendered preview tab
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        self.preview_browser = QTextEdit()
        self.preview_browser.setReadOnly(True)
        self.preview_browser.setHtml(content)
        preview_layout.addWidget(self.preview_browser)
        tabs.addTab(preview_tab, "Preview")

        layout.addWidget(tabs)

        # Character count
        char_count = len(content)
        word_count = len(content.split())
        stats_label = QLabel(f"📊 Stats: {char_count} characters, {word_count} words")
        stats_label.setStyleSheet("color: #aaa; font-style: italic;")
        layout.addWidget(stats_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.regenerate_btn = QPushButton("🔄 Regenerate")
        self.regenerate_btn.setStyleSheet("background-color: #ffd166; color: black; padding: 10px 20px; font-weight: bold;")
        self.regenerate_btn.clicked.connect(self._on_regenerate)

        self.approve_btn = QPushButton("✓ Approve & Post")
        self.approve_btn.setStyleSheet("background-color: #80ed99; color: black; padding: 10px 20px; font-weight: bold;")
        self.approve_btn.clicked.connect(self._on_approve)

        self.cancel_btn = QPushButton("✗ Cancel")
        self.cancel_btn.setStyleSheet("padding: 10px 20px;")
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.regenerate_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.approve_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _on_approve(self):
        """User approved the content"""
        self.approved = True
        self.regenerate = False
        self.accept()

    def _on_regenerate(self):
        """User wants to regenerate the content"""
        self.approved = False
        self.regenerate = True
        self.accept()

    def get_content(self) -> str:
        """Get the (possibly edited) content"""
        return self.content_edit.toPlainText()

    def get_result(self) -> Tuple[bool, bool]:
        """Returns (approved, regenerate)"""
        return self.approved, self.regenerate


class WorkerThread(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(bool, str)
    step_done = pyqtSignal(str)
    content_generated = pyqtSignal(str, str, list)  # (title, content, images)

    def __init__(self, *, video_source: str, youtube_url: str, local_path: str,
                 title: str, apk_links: List[Tuple[str, str]],
                 skip_download: bool, skip_blog: bool, draft_mode: bool,
                 blog_platform: str = "blogger", wordpress_config: dict = None,
                 language: str = "vietnamese", generate_images: bool = True,
                 upload_tiktok: bool = False, tiktok_account: str = "",
                 tiktok_caption: str = "", tiktok_settings: dict = None):
        super().__init__()
        self.video_source = video_source
        self.youtube_url = youtube_url
        self.local_path = local_path
        self.title = title
        self.apk_links = apk_links
        self.skip_download = skip_download
        self.skip_blog = skip_blog
        self.draft_mode = draft_mode
        self.blog_platform = blog_platform
        self.wordpress_config = wordpress_config or {}
        self.language = language
        self.generate_images = generate_images
        self.approved_content = None
        self.should_regenerate = False
        self.user_approved = False
        # TikTok upload options
        self.upload_tiktok = upload_tiktok
        self.tiktok_account = tiktok_account
        self.tiktok_caption = tiktok_caption
        self.tiktok_settings = tiktok_settings or {}

    def safe_log(self, level: str, message: str):
        self.log.emit(f"[{level}] {message}")

    def run(self):
        try:
            clean_temp_dir(older_than_days=1)
            total_steps = 3
            step = 0

            # Step 1: Get video
            self.safe_log("STEP", "Prepare video source")
            video_info = None
            if not self.skip_download:
                step += 1
                self.progress.emit(int(step/total_steps*100), "Preparing video...")
                if self.video_source == "youtube":
                    try:
                        self.safe_log("STEP", "Download video from YouTube")
                        self.safe_log("INFO", "Downloading YouTube video...")
                        filename = sanitize_filename(self.title)
                        downloader = YouTubeDownloader()
                        video_info = downloader.download_video(self.youtube_url, f"{filename}.mp4")
                        self.safe_log("INFO", f"Video downloaded: {video_info['file_path']}")
                    except Exception as e:
                        self.safe_log("ERROR", f"Error downloading video: {str(e)}")
                        self.completed.emit(False, str(e))
                        return
                else:
                    self.safe_log("STEP", "Use local video file")
                    path = Path(self.local_path)
                    if not path.exists():
                        self.safe_log("ERROR", f"Local video not found: {path}")
                        self.completed.emit(False, f"Local video not found: {path}")
                        return
                    video_info = {
                        'file_path': str(path),
                        'title': self.title,
                        'filename': path.name,
                        'duration': None,
                        'size': path.stat().st_size
                    }
                    self.safe_log("INFO", f"Using local video: {path}")
            self.step_done.emit("Video ready")

            # Step 2: Shorten APK links
            self.safe_log("STEP", "Shorten APK links")
            step += 1
            self.progress.emit(int(step/total_steps*100), "Shortening links...")
            shortened_links: Dict[str, str] = {}
            try:
                if self.apk_links:
                    shortener = URLShortener()
                    for name, url in self.apk_links:
                        s = shortener.shorten_url(url)
                        shortened_links[name] = s
                        self.safe_log("INFO", f"Shortened: {name} - {s}")
            except Exception as e:
                self.safe_log("ERROR", f"Error shortening links: {str(e)}")
                # Fallback to original links
                shortened_links = {name: url for name, url in self.apk_links}
            self.step_done.emit("Links shortened")

            # Step 3: Generate and preview blog content
            self.safe_log("STEP", "Generate blog content with AI")
            blog_post = None
            if not self.skip_blog:
                step += 1
                self.progress.emit(int(step/total_steps*100), "Generating blog content...")

                # Content generation loop (allows regeneration)
                content_approved = False
                blog_content = None

                while not content_approved:
                    try:
                        # Generate content
                        lang_name = "Vietnamese" if self.language == "vietnamese" else "English"
                        img_status = "with images" if self.generate_images else "without images"
                        self.safe_log("INFO", f"Generating blog content with AI ({lang_name}, {img_status})...")
                        content_generator = ContentGenerator()
                        blog_content, generated_images = content_generator.generate_blog_post(
                            self.title, video_info, shortened_links,
                            language=self.language,
                            generate_images=self.generate_images,
                            image_count=1 if self.generate_images else 0
                        )

                        # Emit signal to show preview dialog in main thread
                        self.safe_log("INFO", f"Content generated with {len(generated_images)} image(s), waiting for user approval...")
                        self.user_approved = False
                        self.should_regenerate = False
                        self.content_generated.emit(self.title, blog_content, generated_images)

                        # Wait for user decision
                        while not self.user_approved and not self.should_regenerate:
                            self.msleep(100)  # Sleep for 100ms
                            if not self.isRunning():
                                self.safe_log("WARNING", "Process interrupted")
                                self.completed.emit(False, "Process interrupted by user")
                                return

                        if self.user_approved:
                            content_approved = True
                            if self.approved_content:
                                blog_content = self.approved_content
                            self.safe_log("INFO", "Content approved by user")
                        elif self.should_regenerate:
                            self.safe_log("INFO", "Regenerating content...")
                            self.progress.emit(int(step/total_steps*100), "Regenerating content...")
                            continue
                    except Exception as e:
                        self.safe_log("ERROR", f"Error generating blog content: {str(e)}")
                        self.completed.emit(False, str(e))
                        return

                # Step 4: Post to blog platform
                self.safe_log("STEP", f"Posting to {self.blog_platform.title()}")
                self.progress.emit(int(step/total_steps*100), f"Posting to {self.blog_platform}...")

                try:
                    # Select platform
                    if self.blog_platform == "wordpress":
                        self.safe_log("INFO", "Posting to WordPress...")
                        wordpress = WordPressPublisher(
                            site_url=self.wordpress_config.get('url'),
                            username=self.wordpress_config.get('username'),
                            password=self.wordpress_config.get('password')
                        )
                        blog_post = wordpress.create_post(
                            title=self.title,
                            content=blog_content,
                            status="draft" if self.draft_mode else "publish",
                            categories=["APK", "Download"],
                            tags=["Mobile App", "Android"]
                        )
                    else:  # blogger
                        self.safe_log("INFO", "Posting to Blogger...")
                        blogger = BloggerPublisher()
                        blog_post = blogger.create_post(
                            title=self.title,
                            content=blog_content,
                            labels=["APK", "Download", "Mobile App"],
                            is_draft=self.draft_mode
                        )

                    self.safe_log("INFO", f"Blog post created: {blog_post['url']}")
                except Exception as e:
                    self.safe_log("ERROR", f"Error creating blog post: {str(e)}")
                    self.completed.emit(False, str(e))
                    return
            self.step_done.emit("Blog created")

            # Step 5: Upload to TikTok (if enabled)
            if self.upload_tiktok and video_info:
                self.safe_log("STEP", "Uploading to TikTok")
                self.progress.emit(90, "Uploading to TikTok...")

                try:
                    from services.tiktok import TikTokService
                    tiktok_service = TikTokService()

                    if not tiktok_service.is_available():
                        self.safe_log("WARNING", "TikTok service not available, skipping upload")
                    elif not self.tiktok_account:
                        self.safe_log("WARNING", "No TikTok account selected, skipping upload")
                    else:
                        video_path = video_info.get('file_path')
                        caption = self.tiktok_caption or self.title

                        self.safe_log("INFO", f"Uploading to TikTok account: {self.tiktok_account}")
                        self.safe_log("INFO", f"Video: {Path(video_path).name}")
                        self.safe_log("INFO", f"Caption: {caption[:50]}...")

                        success, message = tiktok_service.upload(
                            account_name=self.tiktok_account,
                            video_path=video_path,
                            title=caption,
                            schedule_time=self.tiktok_settings.get('schedule_time', 0),
                            allow_comment=self.tiktok_settings.get('allow_comment', True),
                            allow_duet=self.tiktok_settings.get('allow_duet', False),
                            allow_stitch=self.tiktok_settings.get('allow_stitch', False),
                            is_private=self.tiktok_settings.get('is_private', False)
                        )

                        if success:
                            self.safe_log("INFO", f"TikTok upload successful: {message}")
                            self.step_done.emit("TikTok upload complete")
                        else:
                            self.safe_log("ERROR", f"TikTok upload failed: {message}")
                            # Don't fail the whole process, just log the error

                except Exception as e:
                    self.safe_log("ERROR", f"TikTok upload error: {str(e)}")
                    # Don't fail the whole process

            self.progress.emit(100, "Completed")
            self.step_done.emit("All tasks completed")
            self.completed.emit(True, "Success")

        except Exception as e:
            self.safe_log("ERROR", f"Unexpected error: {str(e)}")
            self.completed.emit(False, str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Content Distribution Tool (Qt)")
        self.resize(1000, 800)
        self.session_path = Path("last_session.json")
        self.shorteners = []  # list of dicts: {name, template, headers_text, keys}
        self.apk_links_data = []  # list of dicts: {name, original, short}

        # Blog platform configuration
        self.blog_platform = "blogger"  # "blogger" or "wordpress"
        self.wordpress_url = ""
        self.wordpress_username = ""
        self.wordpress_password = ""

        # TikTok service
        self.tiktok_service = TikTokService()
        self.tiktok_accounts_list = QListWidget()
        self.tiktok_video_edit = FileDropLineEdit()
        self.tiktok_video_edit.setReadOnly(True)
        self.tiktok_title_edit = QTextEdit()
        self.tiktok_title_edit.setPlaceholderText("Video caption (max 2200 characters)...")
        self.tiktok_schedule_hours = QComboBox()
        self.tiktok_allow_comment = QCheckBox("Allow Comments")
        self.tiktok_allow_comment.setChecked(True)
        self.tiktok_allow_duet = QCheckBox("Allow Duet")
        self.tiktok_allow_stitch = QCheckBox("Allow Stitch")
        self.tiktok_is_private = QCheckBox("Private Video")
        self.tiktok_worker = None

        self.youtube_url_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.local_video_edit = FileDropLineEdit()
        self.local_video_edit.setReadOnly(True)
        self.source_youtube = QRadioButton("YouTube URL")
        self.source_local = QRadioButton("Local Video File")
        self.source_youtube.setChecked(True)

        self.apk_list = QListWidget()
        self.skip_download_cb = QCheckBox("Skip Download")
        self.skip_blog_cb = QCheckBox("Skip Blog Creation")
        self.draft_cb = QCheckBox("Save as Draft")
        self.generate_images_cb = QCheckBox("Generate AI Images")
        self.generate_images_cb.setChecked(True)  # Default: enabled

        self.progress = QProgressBar()
        self.status_label = QLabel("Ready")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        self.worker: WorkerThread = None
        self._build_ui()
        self._wire_events()
        self._validate_config()
        self._load_session()

    def _build_ui(self):
        tabs = QTabWidget()
        content_tab = QWidget()
        tabs.addTab(content_tab, "Content Distribution")
        shortener_tab = QWidget()
        tabs.addTab(shortener_tab, "Link Shorteners")

        # Add Blog Platform Configuration tab
        blog_platform_tab = QWidget()
        tabs.addTab(blog_platform_tab, "Blog Platform")

        # Add AI Settings tab
        ai_settings_tab = QWidget()
        tabs.addTab(ai_settings_tab, "AI Settings")

        # Add TikTok Upload tab
        tiktok_tab = QWidget()
        tabs.addTab(tiktok_tab, "TikTok Upload")

        outer = QVBoxLayout(content_tab)

        # Source group
        source_group = QGroupBox("🎬 Video Source")
        source_layout = QVBoxLayout()
        row1 = QHBoxLayout()
        row1.addWidget(self.source_youtube)
        row1.addWidget(self.source_local)
        row1.addStretch(1)
        source_layout.addLayout(row1)

        # YouTube
        yt_row = QHBoxLayout()
        yt_row.addWidget(QLabel("YouTube URL:"))
        yt_row.addWidget(self.youtube_url_edit)
        self.btn_get_info = QPushButton("Get Info")
        yt_row.addWidget(self.btn_get_info)
        source_layout.addLayout(yt_row)

        # Local file
        local_row = QHBoxLayout()
        local_row.addWidget(QLabel("Video File:"))
        local_row.addWidget(self.local_video_edit)
        self.btn_browse = QPushButton("Browse")
        local_row.addWidget(self.btn_browse)
        source_layout.addLayout(local_row)
        source_group.setLayout(source_layout)

        # Title group
        title_group = QGroupBox("📝 Blog Post Settings")
        t_layout = QVBoxLayout()

        # Title row
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Blog Title:"))
        title_row.addWidget(self.title_edit)
        t_layout.addLayout(title_row)

        # Language selection row
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Content Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("🇻🇳 Vietnamese", "vietnamese")
        self.language_combo.addItem("🇺🇸 English", "english")
        self.language_combo.setCurrentIndex(0)  # Default to Vietnamese
        lang_row.addWidget(self.language_combo)
        lang_row.addStretch(1)
        t_layout.addLayout(lang_row)

        title_group.setLayout(t_layout)

        # APK links group
        apk_group = QGroupBox("🔗 APK Links")
        apk_layout = QVBoxLayout()
        # Shortener selection
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Shortener:"))
        self.shortener_combo = QComboBox()
        sel_row.addWidget(self.shortener_combo)
        sel_row.addStretch(1)
        apk_layout.addLayout(sel_row)
        apk_layout.addWidget(self.apk_list)
        apk_btn_row = QHBoxLayout()
        self.btn_add_apk = QPushButton("Add APK Link")
        self.btn_remove_apk = QPushButton("Remove Selected")
        self.btn_clear_apk = QPushButton("Clear All")
        apk_btn_row.addWidget(self.btn_add_apk)
        apk_btn_row.addWidget(self.btn_remove_apk)
        apk_btn_row.addWidget(self.btn_clear_apk)
        apk_btn_row.addStretch(1)
        apk_layout.addLayout(apk_btn_row)
        apk_group.setLayout(apk_layout)

        # TikTok Upload Group
        tiktok_group = QGroupBox("📱 TikTok Upload (Optional)")
        tiktok_layout = QVBoxLayout()

        # Enable TikTok checkbox
        self.enable_tiktok_cb = QCheckBox("Upload to TikTok")
        self.enable_tiktok_cb.setChecked(False)
        tiktok_layout.addWidget(self.enable_tiktok_cb)

        # TikTok settings container
        self.tiktok_settings_widget = QWidget()
        tiktok_settings_layout = QVBoxLayout()
        tiktok_settings_layout.setContentsMargins(20, 0, 0, 0)  # Indent

        # Account selection
        account_row = QHBoxLayout()
        account_row.addWidget(QLabel("Account:"))
        self.main_tiktok_account_combo = QComboBox()
        self.main_tiktok_account_combo.setMinimumWidth(200)
        account_row.addWidget(self.main_tiktok_account_combo)
        self.btn_refresh_tiktok = QPushButton("🔄 Refresh")
        self.btn_refresh_tiktok.setMaximumWidth(100)
        account_row.addWidget(self.btn_refresh_tiktok)
        account_row.addStretch(1)
        tiktok_settings_layout.addLayout(account_row)

        # Caption
        caption_label = QLabel("Caption:")
        tiktok_settings_layout.addWidget(caption_label)
        self.main_tiktok_caption = QTextEdit()
        self.main_tiktok_caption.setPlaceholderText("TikTok caption (leave empty to use blog title, max 2200 chars)...")
        self.main_tiktok_caption.setMaximumHeight(80)
        tiktok_settings_layout.addWidget(self.main_tiktok_caption)

        # Character count
        self.main_tiktok_char_label = QLabel("0 / 2200 characters")
        self.main_tiktok_char_label.setStyleSheet("color: #aaa; font-style: italic;")
        tiktok_settings_layout.addWidget(self.main_tiktok_char_label)

        # Privacy and schedule options
        tiktok_options_row = QHBoxLayout()
        self.main_tiktok_schedule = QComboBox()
        self.main_tiktok_schedule.addItem("Post Now", 0)
        self.main_tiktok_schedule.addItem("1 hour", 3600)
        self.main_tiktok_schedule.addItem("3 hours", 10800)
        self.main_tiktok_schedule.addItem("12 hours", 43200)
        self.main_tiktok_schedule.addItem("1 day", 86400)
        self.main_tiktok_allow_comment = QCheckBox("Comments")
        self.main_tiktok_allow_comment.setChecked(True)
        self.main_tiktok_allow_duet = QCheckBox("Duet")
        self.main_tiktok_allow_stitch = QCheckBox("Stitch")
        self.main_tiktok_is_private = QCheckBox("Private")

        tiktok_options_row.addWidget(QLabel("Schedule:"))
        tiktok_options_row.addWidget(self.main_tiktok_schedule)
        tiktok_options_row.addWidget(self.main_tiktok_allow_comment)
        tiktok_options_row.addWidget(self.main_tiktok_allow_duet)
        tiktok_options_row.addWidget(self.main_tiktok_allow_stitch)
        tiktok_options_row.addWidget(self.main_tiktok_is_private)
        tiktok_options_row.addStretch(1)
        tiktok_settings_layout.addLayout(tiktok_options_row)

        self.tiktok_settings_widget.setLayout(tiktok_settings_layout)
        self.tiktok_settings_widget.setEnabled(False)  # Disabled by default
        tiktok_layout.addWidget(self.tiktok_settings_widget)

        tiktok_group.setLayout(tiktok_layout)

        # Options
        options_group = QGroupBox("⚙️ Processing Options")
        opt_row = QHBoxLayout()
        opt_row.addWidget(self.skip_download_cb)
        opt_row.addWidget(self.skip_blog_cb)
        opt_row.addWidget(self.draft_cb)
        opt_row.addWidget(self.generate_images_cb)
        opt_row.addStretch(1)
        options_group.setLayout(opt_row)

        # Controls
        ctrl_row = QHBoxLayout()
        self.btn_start = QPushButton("Start Process")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_clear_log = QPushButton("Clear Log")
        ctrl_row.addWidget(self.btn_start)
        ctrl_row.addWidget(self.btn_stop)
        ctrl_row.addStretch(1)
        ctrl_row.addWidget(self.btn_clear_log)

        # Progress / Log
        prog_row = QHBoxLayout()
        prog_row.addWidget(self.progress)
        prog_row.addWidget(self.status_label)

        outer.addWidget(source_group)
        outer.addWidget(title_group)
        outer.addWidget(apk_group)
        outer.addWidget(tiktok_group)
        outer.addWidget(options_group)
        outer.addLayout(ctrl_row)
        outer.addLayout(prog_row)
        outer.addWidget(self.log_text)

        wrap = QWidget()
        w_layout = QVBoxLayout()
        w_layout.addWidget(tabs)
        wrap.setLayout(w_layout)
        self.setCentralWidget(wrap)

        self._on_source_changed()
        self._apply_dark_theme()
        self._apply_icons()

        # Build shorteners tab UI
        s_outer = QVBoxLayout(shortener_tab)
        s_form = QFormLayout()
        self.s_name = QLineEdit()
        self.s_template = QLineEdit()
        self.s_headers = QTextEdit()
        self.s_keys = QLineEdit()
        self.s_headers.setPlaceholderText("Header-Name: value\nAuthorization: Bearer TOKEN")
        self.s_template.setPlaceholderText("https://api.example.com/shorten?api_key=XXX&url={url}")
        self.s_keys.setPlaceholderText("shortenedUrl,short_url,result_url")
        s_form.addRow("Name", self.s_name)
        s_form.addRow("Template URL", self.s_template)
        s_form.addRow("Headers (key: value per line)", self.s_headers)
        s_form.addRow("Response keys (comma)", self.s_keys)
        s_outer.addLayout(s_form)
        # Shortener list
        s_list_row = QHBoxLayout()
        from PyQt5.QtWidgets import QListWidget
        self.shortener_list = QListWidget()
        s_list_btns = QVBoxLayout()
        self.btn_shortener_edit = QPushButton("Edit")
        self.btn_shortener_delete = QPushButton("Delete")
        s_list_btns.addWidget(self.btn_shortener_edit)
        s_list_btns.addWidget(self.btn_shortener_delete)
        s_list_btns.addStretch(1)
        s_list_row.addWidget(self.shortener_list, 1)
        s_list_row.addLayout(s_list_btns)
        s_outer.addLayout(s_list_row)
        # Add/Update controls
        s_btns = QHBoxLayout()
        self.btn_add_shortener = QPushButton("Add/Update Shortener")
        self.btn_remove_shortener = QPushButton("Remove Selected Shortener")
        s_btns.addWidget(self.btn_add_shortener)
        s_btns.addWidget(self.btn_remove_shortener)
        s_btns.addStretch(1)
        s_outer.addLayout(s_btns)

        # Quick Link Shortener section
        quick_shorten_group = QGroupBox("🔗 Quick Link Shortener")
        quick_layout = QVBoxLayout()

        # API selection
        api_row = QHBoxLayout()
        api_row.addWidget(QLabel("Select API:"))
        self.quick_shortener_combo = QComboBox()
        api_row.addWidget(self.quick_shortener_combo, 1)
        quick_layout.addLayout(api_row)

        # Original URL input
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("Original URL:"))
        self.quick_url_input = QLineEdit()
        self.quick_url_input.setPlaceholderText("https://example.com/your-long-url-here")
        url_row.addWidget(self.quick_url_input, 1)
        quick_layout.addLayout(url_row)

        # Shorten button and result
        result_row = QHBoxLayout()
        self.btn_quick_shorten = QPushButton("🔗 Shorten URL")
        self.btn_quick_shorten.setStyleSheet("background-color: #80ed99; color: black; font-weight: bold; padding: 8px;")
        result_row.addWidget(self.btn_quick_shorten)

        self.quick_result_label = QLabel("Shortened URL will appear here")
        self.quick_result_label.setStyleSheet("color: #8ecae6; padding: 8px; background-color: rgba(142, 202, 230, 0.1); border-radius: 4px;")
        self.quick_result_label.setWordWrap(True)
        result_row.addWidget(self.quick_result_label, 1)

        self.btn_copy_short_url = QPushButton("📋 Copy")
        self.btn_copy_short_url.setEnabled(False)
        result_row.addWidget(self.btn_copy_short_url)

        quick_layout.addLayout(result_row)
        quick_shorten_group.setLayout(quick_layout)
        s_outer.addWidget(quick_shorten_group)

        # Shortened links history
        hist_group = QGroupBox("📚 Shortened Links History")
        h_layout = QVBoxLayout()
        self.shortened_history = QListWidget()
        h_btns = QHBoxLayout()
        self.btn_hist_edit = QPushButton("Edit")
        self.btn_hist_delete = QPushButton("Delete")
        self.btn_hist_refresh = QPushButton("Refresh")
        h_btns.addWidget(self.btn_hist_edit)
        h_btns.addWidget(self.btn_hist_delete)
        h_btns.addWidget(self.btn_hist_refresh)
        h_btns.addStretch(1)
        h_layout.addWidget(self.shortened_history)
        h_layout.addLayout(h_btns)
        hist_group.setLayout(h_layout)
        s_outer.addWidget(hist_group)

        # Build Blog Platform Configuration tab UI
        self._build_blog_platform_tab(blog_platform_tab)

        # Build AI Settings tab UI
        self._build_ai_settings_tab(ai_settings_tab)

        # Build TikTok Upload tab UI
        self._build_tiktok_tab(tiktok_tab)

    def _build_blog_platform_tab(self, parent):
        """Build the Blog Platform Configuration tab"""
        layout = QVBoxLayout(parent)

        # Title
        title_label = QLabel("<h2>📝 Blog Platform Configuration</h2>")
        layout.addWidget(title_label)

        # Platform selection group
        platform_group = QGroupBox("Select Blog Platform")
        platform_layout = QVBoxLayout()

        self.platform_button_group = QButtonGroup()
        self.blogger_radio = QRadioButton("Google Blogger")
        self.wordpress_radio = QRadioButton("WordPress")

        self.platform_button_group.addButton(self.blogger_radio)
        self.platform_button_group.addButton(self.wordpress_radio)

        self.blogger_radio.setChecked(True)
        self.blogger_radio.toggled.connect(self._on_platform_changed)

        platform_layout.addWidget(self.blogger_radio)
        platform_layout.addWidget(self.wordpress_radio)
        platform_group.setLayout(platform_layout)
        layout.addWidget(platform_group)

        # Blogger configuration
        self.blogger_config_group = QGroupBox("Google Blogger Settings")
        blogger_layout = QVBoxLayout()

        blogger_info = QLabel(
            "Blogger configuration is managed through the .env file.\n\n"
            "Required environment variables:\n"
            "• BLOGGER_BLOG_ID\n"
            "• GOOGLE_CLIENT_ID\n"
            "• GOOGLE_CLIENT_SECRET\n"
            "• GOOGLE_REFRESH_TOKEN\n\n"
            "See .env.example for details."
        )
        blogger_info.setWordWrap(True)
        blogger_layout.addWidget(blogger_info)

        open_env_btn = QPushButton("Open .env File")
        open_env_btn.clicked.connect(self._open_env_file)
        blogger_layout.addWidget(open_env_btn)

        self.blogger_config_group.setLayout(blogger_layout)
        layout.addWidget(self.blogger_config_group)

        # WordPress configuration
        self.wordpress_config_group = QGroupBox("WordPress Settings")
        wordpress_layout = QFormLayout()

        # WordPress URL
        self.wordpress_url_edit = QLineEdit()
        self.wordpress_url_edit.setPlaceholderText("https://yoursite.com")
        wordpress_layout.addRow("WordPress URL:", self.wordpress_url_edit)

        # WordPress Username
        self.wordpress_username_edit = QLineEdit()
        self.wordpress_username_edit.setPlaceholderText("your-username")
        wordpress_layout.addRow("Username:", self.wordpress_username_edit)

        # WordPress Password/App Password
        password_layout = QHBoxLayout()
        self.wordpress_password_edit = QLineEdit()
        self.wordpress_password_edit.setPlaceholderText("Application Password")
        self.wordpress_password_edit.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.wordpress_password_edit)

        show_pass_btn = QPushButton("Show")
        show_pass_btn.setCheckable(True)
        show_pass_btn.toggled.connect(
            lambda checked: self.wordpress_password_edit.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        password_layout.addWidget(show_pass_btn)
        wordpress_layout.addRow("App Password:", password_layout)

        # Test connection button
        test_btn = QPushButton("Test WordPress Connection")
        test_btn.clicked.connect(self._test_wordpress_connection)
        wordpress_layout.addRow("", test_btn)

        # Save button
        save_btn = QPushButton("Save WordPress Settings")
        save_btn.clicked.connect(self._save_wordpress_config)
        wordpress_layout.addRow("", save_btn)

        self.wordpress_config_group.setLayout(wordpress_layout)
        self.wordpress_config_group.setVisible(False)  # Hide by default
        layout.addWidget(self.wordpress_config_group)

        # Info section
        info_group = QGroupBox("ℹ️ Information")
        info_layout = QVBoxLayout()

        info_text = QLabel(
            "<b>Google Blogger:</b><br>"
            "• Free blogging platform by Google<br>"
            "• Requires OAuth2 authentication<br>"
            "• Configure via .env file<br><br>"
            "<b>WordPress:</b><br>"
            "• Self-hosted or WordPress.com<br>"
            "• Requires WordPress REST API enabled<br>"
            "• Use Application Passwords for authentication<br>"
            "• Create Application Password: Settings → Users → Application Passwords"
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()

    def _on_platform_changed(self):
        """Handle blog platform selection change"""
        if self.blogger_radio.isChecked():
            self.blog_platform = "blogger"
            self.blogger_config_group.setVisible(True)
            self.wordpress_config_group.setVisible(False)
        else:
            self.blog_platform = "wordpress"
            self.blogger_config_group.setVisible(False)
            self.wordpress_config_group.setVisible(True)

        self._save_session()
        self._log("INFO", f"Blog platform changed to: {self.blog_platform}")

    def _open_env_file(self):
        """Open .env file in default editor"""
        env_path = Path(".env")
        if env_path.exists():
            import os
            os.startfile(str(env_path))
        else:
            QMessageBox.warning(self, "Warning", ".env file not found")

    def _test_wordpress_connection(self):
        """Test WordPress connection"""
        url = self.wordpress_url_edit.text().strip()
        username = self.wordpress_username_edit.text().strip()
        password = self.wordpress_password_edit.text().strip()

        if not all([url, username, password]):
            QMessageBox.warning(self, "Warning",
                "Please fill in all WordPress credentials")
            return

        try:
            self._log("INFO", "Testing WordPress connection...")
            wordpress = WordPressPublisher(url, username, password)
            success, message = wordpress.test_connection()

            if success:
                QMessageBox.information(self, "Success", message)
                self._log("INFO", f"WordPress connection: {message}")
            else:
                QMessageBox.warning(self, "Connection Failed", message)
                self._log("ERROR", f"WordPress connection failed: {message}")

        except Exception as e:
            error_msg = f"Error testing connection: {str(e)}"
            QMessageBox.critical(self, "Error", error_msg)
            self._log("ERROR", error_msg)

    def _save_wordpress_config(self):
        """Save WordPress configuration"""
        self.wordpress_url = self.wordpress_url_edit.text().strip()
        self.wordpress_username = self.wordpress_username_edit.text().strip()
        self.wordpress_password = self.wordpress_password_edit.text().strip()

        if all([self.wordpress_url, self.wordpress_username, self.wordpress_password]):
            self._save_session()
            QMessageBox.information(self, "Success",
                "WordPress settings saved successfully!")
            self._log("INFO", "WordPress settings saved")
        else:
            QMessageBox.warning(self, "Warning",
                "Please fill in all WordPress credentials")

    def _build_ai_settings_tab(self, parent):
        """Build the AI Settings tab with button to open settings dialog"""
        layout = QVBoxLayout(parent)

        # Info label
        info_label = QLabel(
            "<h2>AI Configuration & Prompt Management</h2>"
            "<p>Configure your AI provider settings and manage custom prompts for content generation.</p>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Open settings button
        open_settings_btn = QPushButton("Open AI Settings")
        open_settings_btn.setMinimumHeight(50)
        open_settings_btn.clicked.connect(self._open_ai_settings_dialog)
        layout.addWidget(open_settings_btn)

        # Current settings display
        settings_group = QGroupBox("Current AI Configuration")
        settings_layout = QFormLayout()

        from services.ai import AIConfig, PromptManager
        ai_config = AIConfig()
        prompt_manager = PromptManager()

        active_provider = ai_config.get_active_provider()
        provider_config = ai_config.get_provider_config()

        settings_layout.addRow("Active Provider:", QLabel(active_provider.title()))
        settings_layout.addRow("Model:", QLabel(provider_config.get('model', 'N/A')))
        settings_layout.addRow("Temperature:", QLabel(str(provider_config.get('temperature', 0.7))))
        settings_layout.addRow("Max Tokens:", QLabel(str(provider_config.get('max_tokens', 1000))))

        # Selected prompts
        blog_prompt_id = ai_config.get_selected_prompt('blog_post')
        blog_prompt = prompt_manager.get_prompt(blog_prompt_id)
        settings_layout.addRow("Blog Prompt:",
            QLabel(blog_prompt['name'] if blog_prompt else 'N/A'))

        tiktok_prompt_id = ai_config.get_selected_prompt('tiktok_caption')
        tiktok_prompt = prompt_manager.get_prompt(tiktok_prompt_id)
        settings_layout.addRow("TikTok Prompt:",
            QLabel(tiktok_prompt['name'] if tiktok_prompt else 'N/A'))

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Tips
        tips_group = QGroupBox("Tips")
        tips_layout = QVBoxLayout()
        tips_text = QLabel(
            "• Configure your preferred AI provider (Gemini, OpenAI, Claude, or Custom)\n"
            "• Set API keys and model parameters\n"
            "• Create custom prompts for blog posts and TikTok captions\n"
            "• Manage and select different prompt templates\n"
            "• Default prompts cannot be edited or deleted"
        )
        tips_text.setWordWrap(True)
        tips_layout.addWidget(tips_text)
        tips_group.setLayout(tips_layout)
        layout.addWidget(tips_group)

        layout.addStretch()

    def _open_ai_settings_dialog(self):
        """Open the AI settings dialog"""
        dialog = AISettingsDialog(self)
        dialog.exec_()

        # Refresh the AI settings tab display after dialog closes
        # Find the AI Settings tab and rebuild it
        tabs = self.centralWidget().findChild(QTabWidget)
        if tabs:
            for i in range(tabs.count()):
                if tabs.tabText(i) == "AI Settings":
                    # Remove old tab
                    old_widget = tabs.widget(i)
                    tabs.removeTab(i)

                    # Create new tab with updated settings
                    ai_settings_tab = QWidget()
                    self._build_ai_settings_tab(ai_settings_tab)
                    tabs.insertTab(i, ai_settings_tab, "AI Settings")
                    break

    def _build_tiktok_tab(self, parent):
        """Build the TikTok Upload tab"""
        layout = QVBoxLayout(parent)

        # Header
        header = QLabel("<h2>📱 TikTok Video Uploader</h2>")
        layout.addWidget(header)

        # Status banner
        if not self.tiktok_service.is_available():
            error_label = QLabel(
                "⚠️ TikTok Uploader not available.\n\n"
                "Expected path: E:\\Workspace\\Tool\\TiktokAutoUploader\n\n"
                "Required packages:\n"
                "• undetected-chromedriver\n"
                "• moviepy==1.0.3\n"
                "• beautifulsoup4\n"
                "• requests\n\n"
                "If you've just installed packages, click 'Refresh' or restart the application."
            )
            error_label.setWordWrap(True)
            error_label.setStyleSheet("background-color: #ff6b6b; color: white; padding: 15px; border-radius: 4px;")
            layout.addWidget(error_label)

            # Add refresh button
            refresh_btn = QPushButton("🔄 Refresh / Retry")
            refresh_btn.setMaximumWidth(200)
            refresh_btn.clicked.connect(self._refresh_tiktok_service)
            layout.addWidget(refresh_btn)

            layout.addStretch()
            return

        # Account Management Group
        account_group = QGroupBox("👤 Account Management")
        account_layout = QVBoxLayout()

        # Account list
        account_layout.addWidget(QLabel("Saved Accounts:"))
        account_layout.addWidget(self.tiktok_accounts_list)

        # Account buttons
        account_btns = QHBoxLayout()
        self.btn_tiktok_login = QPushButton("Login New Account")
        self.btn_tiktok_refresh = QPushButton("Refresh List")
        self.btn_tiktok_delete = QPushButton("Delete Selected")
        account_btns.addWidget(self.btn_tiktok_login)
        account_btns.addWidget(self.btn_tiktok_refresh)
        account_btns.addWidget(self.btn_tiktok_delete)
        account_btns.addStretch()
        account_layout.addLayout(account_btns)

        account_group.setLayout(account_layout)
        layout.addWidget(account_group)

        # Video Upload Group
        upload_group = QGroupBox("🎬 Video Upload")
        upload_layout = QVBoxLayout()

        # Video file selection
        video_row = QHBoxLayout()
        video_row.addWidget(QLabel("Video File:"))
        video_row.addWidget(self.tiktok_video_edit)
        self.btn_tiktok_browse = QPushButton("Browse")
        video_row.addWidget(self.btn_tiktok_browse)
        upload_layout.addLayout(video_row)

        # Caption/Title
        upload_layout.addWidget(QLabel("Caption:"))
        self.tiktok_title_edit.setMaximumHeight(100)
        upload_layout.addWidget(self.tiktok_title_edit)

        # Character counter
        self.tiktok_char_label = QLabel("0 / 2200 characters")
        self.tiktok_char_label.setStyleSheet("color: #aaa; font-style: italic;")
        upload_layout.addWidget(self.tiktok_char_label)

        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)

        # Settings Group
        settings_group = QGroupBox("⚙️ Upload Settings")
        settings_layout = QVBoxLayout()

        # Privacy options
        privacy_row = QHBoxLayout()
        privacy_row.addWidget(self.tiktok_allow_comment)
        privacy_row.addWidget(self.tiktok_allow_duet)
        privacy_row.addWidget(self.tiktok_allow_stitch)
        privacy_row.addWidget(self.tiktok_is_private)
        privacy_row.addStretch()
        settings_layout.addLayout(privacy_row)

        # Schedule time
        schedule_row = QHBoxLayout()
        schedule_row.addWidget(QLabel("Schedule:"))
        self.tiktok_schedule_hours.addItem("Post Now", 0)
        self.tiktok_schedule_hours.addItem("15 minutes", 900)
        self.tiktok_schedule_hours.addItem("1 hour", 3600)
        self.tiktok_schedule_hours.addItem("3 hours", 10800)
        self.tiktok_schedule_hours.addItem("6 hours", 21600)
        self.tiktok_schedule_hours.addItem("12 hours", 43200)
        self.tiktok_schedule_hours.addItem("1 day", 86400)
        self.tiktok_schedule_hours.addItem("2 days", 172800)
        self.tiktok_schedule_hours.addItem("3 days", 259200)
        self.tiktok_schedule_hours.addItem("7 days", 604800)
        schedule_row.addWidget(self.tiktok_schedule_hours)
        schedule_row.addStretch()
        settings_layout.addLayout(schedule_row)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Upload button
        button_row = QHBoxLayout()
        self.btn_tiktok_upload = QPushButton("Upload to TikTok")
        self.btn_tiktok_upload.setMinimumHeight(40)
        self.btn_tiktok_upload.setStyleSheet("background-color: #80ed99; color: black; font-weight: bold; font-size: 14px;")
        button_row.addWidget(self.btn_tiktok_upload)
        layout.addLayout(button_row)

        # Info section
        info_group = QGroupBox("ℹ️ Information")
        info_layout = QVBoxLayout()
        info_text = QLabel(
            "<b>How to use:</b><br>"
            "1. Login to your TikTok account (opens browser)<br>"
            "2. Select the saved account from the list<br>"
            "3. Choose a video file (MP4, WebM, MOV, etc.)<br>"
            "4. Write your caption (max 2200 characters)<br>"
            "5. Configure privacy and schedule settings<br>"
            "6. Click 'Upload to TikTok'<br><br>"
            "<b>Notes:</b><br>"
            "• Login is done through browser (handles 2FA)<br>"
            "• Private videos cannot be scheduled<br>"
            "• Schedule time: 15 min to 10 days in future<br>"
            "• Max video size: ~1800MB<br>"
            "• Supports hashtags (#) and mentions (@) in caption"
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()

        # Load accounts
        self._refresh_tiktok_accounts()

    def _wire_events(self):
        self.source_youtube.toggled.connect(self._on_source_changed)
        self.source_youtube.toggled.connect(self._save_session)
        self.source_local.toggled.connect(self._save_session)
        self.btn_browse.clicked.connect(self._browse_video)
        self.btn_get_info.clicked.connect(self._get_video_info)
        self.btn_add_apk.clicked.connect(self._add_apk_link)
        self.btn_remove_apk.clicked.connect(self._remove_selected_apk)
        self.btn_clear_apk.clicked.connect(self.apk_list.clear)
        self.btn_start.clicked.connect(self._start_process)
        self.btn_stop.clicked.connect(self._stop_process)
        self.btn_clear_log.clicked.connect(self.log_text.clear)
        self.youtube_url_edit.textChanged.connect(self._save_session)
        self.local_video_edit.textChanged.connect(self._save_session)
        self.title_edit.textChanged.connect(self._save_session)
        self.skip_download_cb.stateChanged.connect(self._save_session)
        self.skip_blog_cb.stateChanged.connect(self._save_session)
        self.draft_cb.stateChanged.connect(self._save_session)
        self.generate_images_cb.stateChanged.connect(self._save_session)
        self.btn_add_shortener.clicked.connect(self._add_or_update_shortener)
        self.btn_remove_shortener.clicked.connect(self._remove_selected_shortener)
        self.shortener_list.itemSelectionChanged.connect(self._on_shortener_list_selected)
        self.btn_shortener_edit.clicked.connect(self._on_shortener_edit)
        self.btn_shortener_delete.clicked.connect(self._on_shortener_delete)
        self.shortener_combo.currentIndexChanged.connect(self._save_session)
        self.btn_hist_refresh.clicked.connect(self._refresh_shortened_history)
        self.btn_hist_edit.clicked.connect(self._edit_shortened_item)
        self.btn_hist_delete.clicked.connect(self._remove_shortened_item)
        self.language_combo.currentIndexChanged.connect(self._save_session)

        # Quick shortener events
        self.btn_quick_shorten.clicked.connect(self._on_quick_shorten)
        self.btn_copy_short_url.clicked.connect(self._on_copy_short_url)
        self.quick_shortener_combo.currentIndexChanged.connect(self._on_quick_shortener_changed)

        # Main tab TikTok events
        self.enable_tiktok_cb.stateChanged.connect(self._on_enable_tiktok_changed)
        self.btn_refresh_tiktok.clicked.connect(self._refresh_main_tiktok_accounts)
        self.main_tiktok_caption.textChanged.connect(self._on_main_tiktok_caption_changed)
        self.enable_tiktok_cb.stateChanged.connect(self._save_session)
        self.main_tiktok_account_combo.currentIndexChanged.connect(self._save_session)
        self.main_tiktok_schedule.currentIndexChanged.connect(self._save_session)

        # TikTok tab events
        if self.tiktok_service.is_available():
            self.btn_tiktok_login.clicked.connect(self._on_tiktok_login)
            self.btn_tiktok_refresh.clicked.connect(self._refresh_tiktok_accounts)
            self.btn_tiktok_delete.clicked.connect(self._on_tiktok_delete_account)
            self.btn_tiktok_browse.clicked.connect(self._on_tiktok_browse_video)
            self.btn_tiktok_upload.clicked.connect(self._on_tiktok_upload)
            self.tiktok_title_edit.textChanged.connect(self._on_tiktok_caption_changed)

    def _validate_config(self):
        try:
            validate_config()
            self._log("INFO", "Configuration validated successfully")
        except ValueError as e:
            self._log("ERROR", f"Configuration error: {str(e)}")
            QMessageBox.critical(self, "Configuration Error", f"{str(e)}\n\nPlease check your .env file.")

    def _on_source_changed(self):
        is_yt = self.source_youtube.isChecked()
        self.youtube_url_edit.setEnabled(is_yt)
        self.btn_get_info.setEnabled(is_yt)
        self.local_video_edit.setEnabled(not is_yt)
        self.btn_browse.setEnabled(not is_yt)

    def _browse_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm)")
        if path:
            self.local_video_edit.setText(path)
            if not self.title_edit.text().strip():
                name = Path(path).stem.replace("_", " ").replace("-", " ")
                self.title_edit.setText(name.title())

    def _get_video_info(self):
        url = self.youtube_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a YouTube URL first")
            return
        try:
            self.status_label.setText("Fetching video info...")
            downloader = YouTubeDownloader()
            info = downloader.get_video_info(url)
            suggested_title = info.get('title', '')
            if suggested_title:
                self.title_edit.setText(suggested_title)
                self._log("INFO", f"Auto-filled blog title: {suggested_title}")
            self._log("INFO", f"Video found: {info.get('title', 'Unknown')}")
            self.status_label.setText("Video info fetched successfully")
        except Exception as e:
            self._log("ERROR", f"Error fetching video info: {str(e)}")
            self.status_label.setText("Error fetching video info")

    def _add_apk_link(self):
        dlg = APKLinkDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            name, url = dlg.get_result()
            if not name or not url:
                QMessageBox.warning(self, "Warning", "Please fill in both fields")
                return
            short = self._shorten_now(url)
            if short and short != url:
                item_text = f"{name}: {short}"
                tooltip = f"Original: {url}"
                self._log("STEP", f"Shortened ✓ <a href='{short}' style='color:#8ecae6;'>{short}</a>")
                self._show_toast(f"Shortened ✓ {short}")
            else:
                item_text = f"{name}: {url}"
                tooltip = ""
                self._log("WARNING", "Shorten failed, using original URL")
                self._show_toast("Shorten failed, using original")
            item = QListWidgetItem(item_text)
            if tooltip:
                item.setToolTip(tooltip)
            self.apk_list.addItem(item)
            self.apk_links_data.append({"name": name, "original": url, "short": short or url})
            self._log("INFO", f"Added APK link: {name}")
            self._save_session()

    def _remove_selected_apk(self):
        for item in list(self.apk_list.selectedItems()):
            row = self.apk_list.row(item)
            self.apk_list.takeItem(row)
            if 0 <= row < len(self.apk_links_data):
                del self.apk_links_data[row]
        self._save_session()
        self._refresh_shortened_history()

    def _collect_apk_links(self) -> List[Tuple[str, str]]:
        if self.apk_links_data:
            return [(d["name"], d.get("short") or d.get("original")) for d in self.apk_links_data]
        # fallback if loaded older session format
        links: List[Tuple[str, str]] = []
        for i in range(self.apk_list.count()):
            text = self.apk_list.item(i).text()
            if ":" in text:
                name, url = text.split(":", 1)
                links.append((name.strip(), url.strip()))
        return links

    def _add_or_update_shortener(self):
        name = self.s_name.text().strip()
        template = self.s_template.text().strip()
        headers_text = self.s_headers.toPlainText()
        keys = [k.strip() for k in self.s_keys.text().split(',') if k.strip()]
        if not name or not template:
            QMessageBox.warning(self, "Warning", "Please provide Name and Template URL")
            return
        # update existing
        existing = next((s for s in self.shorteners if s['name'] == name), None)
        data = {"name": name, "template": template, "headers_text": headers_text, "keys": keys}
        if existing:
            existing.update(data)
        else:
            self.shorteners.append(data)
            self.shortener_combo.addItem(name)
            self.shortener_list.addItem(name)
            self.quick_shortener_combo.addItem(name)
        self._save_session()
        self._show_toast("Shortener saved")

    def _remove_selected_shortener(self):
        idx = self.shortener_combo.currentIndex()
        if idx < 0:
            return
        name = self.shortener_combo.currentText()
        self.shortener_combo.removeItem(idx)
        self.shorteners = [s for s in self.shorteners if s['name'] != name]
        # remove from list widget
        for i in range(self.shortener_list.count()):
            if self.shortener_list.item(i).text() == name:
                self.shortener_list.takeItem(i)
                break
        # remove from quick shortener combo
        quick_idx = self.quick_shortener_combo.findText(name)
        if quick_idx >= 0:
            self.quick_shortener_combo.removeItem(quick_idx)
        self._save_session()
        self._show_toast("Shortener removed")

    def _shorten_now(self, url: str) -> str:
        # Use the selected shortener's base_url as the API endpoint
        cfg = None
        idx = self.shortener_combo.currentIndex()
        if idx >= 0 and idx < len(self.shorteners):
            cfg = self.shorteners[idx]
        if not cfg:
            return url
        try:
            from services.shortener import URLShortener
            shortener = URLShortener()
            base_url = cfg.get('template', '')  # template now is just the API endpoint up to 'url='
            return shortener.shorten_url(base_url, url)
        except Exception as e:
            self._log('ERROR', f'Shorten failed: {e}')
            return url

    def _on_quick_shorten(self):
        """Handle quick URL shortening"""
        original_url = self.quick_url_input.text().strip()

        if not original_url:
            QMessageBox.warning(self, "Warning", "Please enter a URL to shorten")
            return

        if not original_url.startswith(('http://', 'https://')):
            QMessageBox.warning(self, "Warning", "URL must start with http:// or https://")
            return

        # Get selected shortener
        idx = self.quick_shortener_combo.currentIndex()
        if idx < 0 or idx >= len(self.shorteners):
            QMessageBox.warning(self, "Warning", "Please select a shortener API first")
            return

        cfg = self.shorteners[idx]

        # Update UI
        self.btn_quick_shorten.setEnabled(False)
        self.btn_quick_shorten.setText("⏳ Shortening...")
        self.quick_result_label.setText("Processing...")
        self.quick_result_label.setStyleSheet("color: #ffd166; padding: 8px; background-color: rgba(255, 209, 102, 0.1); border-radius: 4px;")
        QApplication.processEvents()

        try:
            from services.shortener import URLShortener
            shortener = URLShortener()
            base_url = cfg.get('template', '')

            self._log("INFO", f"Shortening URL with {cfg.get('name')}...")
            shortened_url = shortener.shorten_url(base_url, original_url)

            if shortened_url and shortened_url != original_url:
                # Success
                self.quick_result_label.setText(f"✓ {shortened_url}")
                self.quick_result_label.setStyleSheet("color: #80ed99; padding: 8px; background-color: rgba(128, 237, 153, 0.1); border-radius: 4px;")
                self.btn_copy_short_url.setEnabled(True)
                self._log("STEP", f"Shortened ✓ <a href='{shortened_url}' style='color:#8ecae6;'>{shortened_url}</a>")
                self._show_toast(f"URL shortened successfully!")
            else:
                # Failed
                self.quick_result_label.setText("✗ Shortening failed. API may be unavailable or incorrect.")
                self.quick_result_label.setStyleSheet("color: #ff6b6b; padding: 8px; background-color: rgba(255, 107, 107, 0.1); border-radius: 4px;")
                self.btn_copy_short_url.setEnabled(False)
                self._log("ERROR", "URL shortening failed")

        except Exception as e:
            self.quick_result_label.setText(f"✗ Error: {str(e)}")
            self.quick_result_label.setStyleSheet("color: #ff6b6b; padding: 8px; background-color: rgba(255, 107, 107, 0.1); border-radius: 4px;")
            self.btn_copy_short_url.setEnabled(False)
            self._log("ERROR", f"Shortening error: {str(e)}")

        finally:
            self.btn_quick_shorten.setEnabled(True)
            self.btn_quick_shorten.setText("🔗 Shorten URL")

    def _on_copy_short_url(self):
        """Copy shortened URL to clipboard"""
        result_text = self.quick_result_label.text()

        # Extract URL from "✓ shortened_url" format
        if result_text.startswith("✓ "):
            url = result_text[2:].strip()

            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(url)

            self._show_toast("URL copied to clipboard!")
            self._log("INFO", f"Copied to clipboard: {url}")
        else:
            QMessageBox.warning(self, "Warning", "No shortened URL to copy")

    def _on_quick_shortener_changed(self):
        """Handle shortener API selection change"""
        idx = self.quick_shortener_combo.currentIndex()
        if idx >= 0 and idx < len(self.shorteners):
            cfg = self.shorteners[idx]
            self._log("INFO", f"Selected shortener: {cfg.get('name')}")

    def _start_process(self):
        # Validate
        is_yt = self.source_youtube.isChecked()
        if is_yt:
            if not self.youtube_url_edit.text().strip():
                QMessageBox.critical(self, "Error", "Please enter a YouTube URL")
                return
        else:
            p = self.local_video_edit.text().strip()
            if not p:
                QMessageBox.critical(self, "Error", "Please select a video file")
                return
            if not Path(p).exists():
                QMessageBox.critical(self, "Error", "Selected video file does not exist")
                return
        if not self.title_edit.text().strip():
            QMessageBox.critical(self, "Error", "Please enter a blog title")
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress.setValue(0)
        self.status_label.setText("Starting...")

        # Get selected language
        selected_language = self.language_combo.currentData()

        # Validate TikTok settings if enabled
        upload_tiktok = self.enable_tiktok_cb.isChecked()
        tiktok_account = ""
        tiktok_caption = ""
        tiktok_settings = {}

        if upload_tiktok:
            if self.main_tiktok_account_combo.currentIndex() < 0:
                QMessageBox.warning(self, "Warning", "Please select a TikTok account or disable TikTok upload")
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)
                return

            tiktok_account = self.main_tiktok_account_combo.currentText()
            tiktok_caption = self.main_tiktok_caption.toPlainText().strip()

            if len(tiktok_caption) > 2200:
                QMessageBox.warning(self, "Warning", "TikTok caption is too long (max 2200 characters)")
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)
                return

            tiktok_settings = {
                'schedule_time': self.main_tiktok_schedule.currentData(),
                'allow_comment': self.main_tiktok_allow_comment.isChecked(),
                'allow_duet': self.main_tiktok_allow_duet.isChecked(),
                'allow_stitch': self.main_tiktok_allow_stitch.isChecked(),
                'is_private': self.main_tiktok_is_private.isChecked()
            }

        self.worker = WorkerThread(
            video_source="youtube" if is_yt else "local",
            youtube_url=self.youtube_url_edit.text().strip(),
            local_path=self.local_video_edit.text().strip(),
            title=self.title_edit.text().strip(),
            apk_links=self._collect_apk_links(),
            skip_download=self.skip_download_cb.isChecked(),
            skip_blog=self.skip_blog_cb.isChecked(),
            draft_mode=self.draft_cb.isChecked(),
            blog_platform=self.blog_platform,
            wordpress_config={
                'url': self.wordpress_url,
                'username': self.wordpress_username,
                'password': self.wordpress_password
            },
            language=selected_language,
            generate_images=self.generate_images_cb.isChecked(),
            upload_tiktok=upload_tiktok,
            tiktok_account=tiktok_account,
            tiktok_caption=tiktok_caption,
            tiktok_settings=tiktok_settings
        )
        self.worker.log.connect(lambda m: self._log("INFO" if m.startswith("[INFO]") else "LOG", m))
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
        self.worker.step_done.connect(self._show_toast)
        self.worker.content_generated.connect(self._on_content_generated)
        self.worker.start()

    def _stop_process(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Process stopped by user")
        self._log("WARNING", "Process stopped by user")

    def _on_progress(self, value: int, status: str):
        self.progress.setValue(max(0, min(100, value)))
        self.status_label.setText(status)

    def _on_content_generated(self, title: str, content: str, images: list):
        """Handle content generation and show preview dialog"""
        image_count = len(images) if images else 0
        self._log("STEP", f"Content generated with {image_count} image(s), showing preview...")
        self.status_label.setText("Reviewing content...")

        # Get current language for display
        current_language = self.language_combo.currentData()

        # Show preview dialog
        dialog = ContentPreviewDialog(title, content, self, language=current_language, images=images)
        result = dialog.exec_()

        if result == QDialog.Accepted:
            approved, regenerate = dialog.get_result()

            if approved:
                # User approved the content
                self._log("INFO", "✓ Content approved by user")
                self._show_toast("Content approved ✓")
                self.worker.approved_content = dialog.get_content()
                self.worker.user_approved = True
                self.worker.should_regenerate = False
            elif regenerate:
                # User wants to regenerate
                self._log("INFO", "🔄 Regenerating content...")
                self._show_toast("Regenerating content...")
                self.worker.user_approved = False
                self.worker.should_regenerate = True
        else:
            # User cancelled
            self._log("WARNING", "Content preview cancelled by user")
            self._stop_process()

    def _on_completed(self, success: bool, message: str):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if success:
            self.status_label.setText("Process completed successfully!")
            self._log("STEP", "All tasks completed successfully!")
            QMessageBox.information(self, "Success", "Content distribution completed successfully!")
        else:
            self.status_label.setText("Error")
            self._log("ERROR", message)
            QMessageBox.critical(self, "Error", f"An error occurred: {message}")
        self._save_session()
        self._refresh_shortened_history()

    def _log(self, level: str, message: str):
        color = "#c8c8c8"
        if level == "ERROR":
            color = "#ff6b6b"
        elif level == "WARNING":
            color = "#ffd166"
        elif level == "INFO":
            color = "#8ecae6"
        elif level == "STEP":
            color = "#80ed99"
        if level == "STEP":
            html = f"<div style='margin:4px 0;'><span style='color:{color};'>●</span> <b>{message}</b></div>"
        else:
            html = f"<div style='margin:2px 0;color:{color};'>{message}</div>"
        self.log_text.append(html)

    def _show_toast(self, message: str):
        toast = Toast(self, message)
        toast.show_for(2000)

    def _refresh_shortener_list(self):
        self.shortener_list.clear()
        for s in self.shorteners:
            self.shortener_list.addItem(s.get('name', ''))

    def _on_shortener_list_selected(self):
        items = self.shortener_list.selectedItems()
        if not items:
            return
        name = items[0].text()
        s = next((x for x in self.shorteners if x['name'] == name), None)
        if not s:
            return
        self.s_name.setText(s.get('name', ''))
        self.s_template.setText(s.get('template', ''))
        self.s_headers.setText(s.get('headers_text', ''))
        self.s_keys.setText(','.join(s.get('keys', [])))

    def _on_shortener_edit(self):
        # Same as selecting and editing fields then Add/Update
        self._on_shortener_list_selected()
        self._show_toast("Edit fields then click Add/Update")

    def _on_shortener_delete(self):
        items = self.shortener_list.selectedItems()
        if not items:
            return
        name = items[0].text()
        # remove from combo
        idx = self.shortener_combo.findText(name)
        if idx >= 0:
            self.shortener_combo.removeItem(idx)
        # remove from storage and list
        self.shorteners = [s for s in self.shorteners if s['name'] != name]
        self._refresh_shortener_list()
        self._save_session()
        self._show_toast("Shortener removed")

    def _refresh_shortened_history(self):
        self.shortened_history.clear()
        for d in self.apk_links_data:
            name = d.get('name', '')
            original = d.get('original', '')
            short = d.get('short') or original
            item = QListWidgetItem(f"{name}: {short}")
            if original and short != original:
                item.setToolTip(f"Original: {original}")
            self.shortened_history.addItem(item)

    def _edit_shortened_item(self):
        items = self.shortened_history.selectedItems()
        if not items:
            return
        row = self.shortened_history.row(items[0])
        if row < 0 or row >= len(self.apk_links_data):
            return
        cur = self.apk_links_data[row]
        dlg = APKLinkDialog(self)
        dlg.name_edit.setText(cur.get('name', ''))
        dlg.url_edit.setText(cur.get('original', ''))
        if dlg.exec_() == QDialog.Accepted:
            name, url = dlg.get_result()
            if not name or not url:
                return
            short = self._shorten_now(url)
            self.apk_links_data[row] = {"name": name, "original": url, "short": short or url}
            # Update content tab list accordingly
            if row < self.apk_list.count():
                self.apk_list.item(row).setText(f"{name}: {short or url}")
                tooltip = f"Original: {url}" if short and short != url else ""
                self.apk_list.item(row).setToolTip(tooltip)
            if short and short != url:
                self._log("STEP", f"Shortened ✓ <a href='{short}' style='color:#8ecae6;'>{short}</a>")
                self._show_toast(f"Shortened ✓ {short}")
            else:
                self._log("WARNING", "Shorten failed, using original URL")
                self._show_toast("Shorten failed, using original")
            self._refresh_shortened_history()
            self._save_session()

    def _remove_shortened_item(self):
        items = list(self.shortened_history.selectedItems())
        for it in items:
            row = self.shortened_history.row(it)
            self.shortened_history.takeItem(row)
            if 0 <= row < len(self.apk_links_data):
                del self.apk_links_data[row]
                if row < self.apk_list.count():
                    self.apk_list.takeItem(row)
        self._save_session()

    def _save_session(self):
        try:
            data = {
                "source": "youtube" if self.source_youtube.isChecked() else "local",
                "youtube_url": self.youtube_url_edit.text().strip(),
                "local_path": self.local_video_edit.text().strip(),
                "title": self.title_edit.text().strip(),
                "apk_links": [(d.get("name"), d.get("original")) for d in self.apk_links_data] if self.apk_links_data else self._collect_apk_links(),
                "skip_download": self.skip_download_cb.isChecked(),
                "skip_blog": self.skip_blog_cb.isChecked(),
                "draft": self.draft_cb.isChecked(),
                "shorteners": self.shorteners,
                "selected_shortener": self.shortener_combo.currentText() if self.shortener_combo.currentIndex() >= 0 else "",
                "blog_platform": self.blog_platform,
                "wordpress_url": self.wordpress_url,
                "wordpress_username": self.wordpress_username,
                "wordpress_password": self.wordpress_password,
                "language": self.language_combo.currentData() if self.language_combo.currentIndex() >= 0 else "vietnamese",
                "generate_images": self.generate_images_cb.isChecked(),
                "enable_tiktok": self.enable_tiktok_cb.isChecked(),
                "tiktok_account": self.main_tiktok_account_combo.currentText() if self.main_tiktok_account_combo.currentIndex() >= 0 else "",
                "tiktok_caption": self.main_tiktok_caption.toPlainText().strip()
            }
            self.session_path.write_text(__import__("json").dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_session(self):
        try:
            if not self.session_path.exists():
                return
            data = __import__("json").loads(self.session_path.read_text(encoding="utf-8"))
            if data.get("source") == "youtube":
                self.source_youtube.setChecked(True)
            else:
                self.source_local.setChecked(True)
            self.youtube_url_edit.setText(data.get("youtube_url", ""))
            self.local_video_edit.setText(data.get("local_path", ""))
            self.title_edit.setText(data.get("title", ""))
            self.apk_list.clear()
            self.apk_links_data = []
            for name, url in data.get("apk_links", []):
                item = QListWidgetItem(f"{name}: {url}")
                self.apk_list.addItem(item)
                self.apk_links_data.append({"name": name, "original": url, "short": url})
            self.skip_download_cb.setChecked(bool(data.get("skip_download", False)))
            self.skip_blog_cb.setChecked(bool(data.get("skip_blog", False)))
            self.draft_cb.setChecked(bool(data.get("draft", False)))
            self.generate_images_cb.setChecked(bool(data.get("generate_images", True)))
            # load shorteners
            self.shorteners = data.get("shorteners", []) or []
            self.shortener_combo.clear()
            self.shortener_list.clear()
            self.quick_shortener_combo.clear()
            for s in self.shorteners:
                name = s.get('name', '')
                self.shortener_combo.addItem(name)
                self.shortener_list.addItem(name)
                self.quick_shortener_combo.addItem(name)
            sel = data.get("selected_shortener", "")
            if sel:
                idx = self.shortener_combo.findText(sel)
                if idx >= 0:
                    self.shortener_combo.setCurrentIndex(idx)
                # Also set for quick shortener
                quick_idx = self.quick_shortener_combo.findText(sel)
                if quick_idx >= 0:
                    self.quick_shortener_combo.setCurrentIndex(quick_idx)
            # Load blog platform configuration
            self.blog_platform = data.get("blog_platform", "blogger")
            if self.blog_platform == "wordpress":
                self.wordpress_radio.setChecked(True)
            else:
                self.blogger_radio.setChecked(True)
            self.wordpress_url = data.get("wordpress_url", "")
            self.wordpress_username = data.get("wordpress_username", "")
            self.wordpress_password = data.get("wordpress_password", "")
            # Update WordPress form fields
            self.wordpress_url_edit.setText(self.wordpress_url)
            self.wordpress_username_edit.setText(self.wordpress_username)
            self.wordpress_password_edit.setText(self.wordpress_password)

            # Load language preference
            saved_language = data.get("language", "vietnamese")
            for i in range(self.language_combo.count()):
                if self.language_combo.itemData(i) == saved_language:
                    self.language_combo.setCurrentIndex(i)
                    break

            # Load TikTok settings
            self.enable_tiktok_cb.setChecked(bool(data.get("enable_tiktok", False)))
            self.main_tiktok_caption.setPlainText(data.get("tiktok_caption", ""))

            # Refresh TikTok accounts
            self._refresh_main_tiktok_accounts()

            # Set selected TikTok account
            saved_tiktok_account = data.get("tiktok_account", "")
            if saved_tiktok_account:
                idx = self.main_tiktok_account_combo.findText(saved_tiktok_account)
                if idx >= 0:
                    self.main_tiktok_account_combo.setCurrentIndex(idx)

            self._refresh_shortened_history()
        except Exception:
            pass

    # TikTok Methods
    def _refresh_tiktok_service(self):
        """Refresh TikTok service and rebuild tab"""
        try:
            from services.tiktok import TikTokService
            self.tiktok_service = TikTokService()

            if self.tiktok_service.is_available():
                self._log("INFO", "TikTok service loaded successfully!")
                self._show_toast("TikTok service available!")
                QMessageBox.information(
                    self, "Success",
                    "TikTok service is now available!\n\nThe tab will be rebuilt automatically."
                )
            else:
                self._log("WARNING", "TikTok service still not available")
                QMessageBox.warning(
                    self, "Still Not Available",
                    "TikTok service could not be loaded.\n\n"
                    "Please check:\n"
                    "1. TikTokAutoUploader exists at E:\\Workspace\\Tool\\TiktokAutoUploader\n"
                    "2. Required packages are installed\n"
                    "3. Try restarting the application"
                )

            # Rebuild the TikTok tab
            tabs = self.centralWidget().findChild(QTabWidget)
            if tabs:
                for i in range(tabs.count()):
                    if tabs.tabText(i) == "TikTok Upload":
                        old_widget = tabs.widget(i)
                        tabs.removeTab(i)

                        tiktok_tab = QWidget()
                        self._build_tiktok_tab(tiktok_tab)
                        tabs.insertTab(i, tiktok_tab, "TikTok Upload")
                        tabs.setCurrentIndex(i)
                        break
        except Exception as e:
            self._log("ERROR", f"Error refreshing TikTok service: {e}")
            QMessageBox.critical(self, "Error", f"Failed to refresh:\n{str(e)}")

    def _refresh_tiktok_accounts(self):
        """Refresh the list of TikTok accounts"""
        if not self.tiktok_service.is_available():
            return

        self.tiktok_accounts_list.clear()
        accounts = self.tiktok_service.get_saved_accounts()

        if not accounts:
            item = QListWidgetItem("No accounts saved. Click 'Login New Account' to start.")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            self.tiktok_accounts_list.addItem(item)
        else:
            for account in accounts:
                self.tiktok_accounts_list.addItem(account)

        self._log("INFO", f"Found {len(accounts)} TikTok account(s)")

    def _on_enable_tiktok_changed(self):
        """Handle TikTok upload checkbox state change"""
        enabled = self.enable_tiktok_cb.isChecked()
        self.tiktok_settings_widget.setEnabled(enabled)

        if enabled:
            # Load TikTok accounts
            self._refresh_main_tiktok_accounts()

    def _refresh_main_tiktok_accounts(self):
        """Refresh TikTok account list in main tab"""
        self.main_tiktok_account_combo.clear()

        if not self.tiktok_service.is_available():
            self.main_tiktok_account_combo.addItem("TikTok service not available")
            self.main_tiktok_account_combo.setEnabled(False)
            return

        accounts = self.tiktok_service.get_saved_accounts()

        if not accounts:
            self.main_tiktok_account_combo.addItem("No accounts (login in TikTok tab)")
            self.main_tiktok_account_combo.setEnabled(False)
        else:
            self.main_tiktok_account_combo.setEnabled(True)
            for account in accounts:
                self.main_tiktok_account_combo.addItem(account)

    def _on_main_tiktok_caption_changed(self):
        """Update character count for main tab TikTok caption"""
        text = self.main_tiktok_caption.toPlainText()
        char_count = len(text)
        self.main_tiktok_char_label.setText(f"{char_count} / 2200 characters")

        if char_count > 2200:
            self.main_tiktok_char_label.setStyleSheet("color: #ff6b6b; font-style: italic; font-weight: bold;")
        else:
            self.main_tiktok_char_label.setStyleSheet("color: #aaa; font-style: italic;")

    def _on_tiktok_login(self):
        """Handle TikTok login"""
        if not self.tiktok_service.is_available():
            QMessageBox.warning(self, "Warning", "TikTok service not available")
            return

        # Ask for account name
        from PyQt5.QtWidgets import QInputDialog
        account_name, ok = QInputDialog.getText(
            self, "Login to TikTok",
            "Enter a name for this account:\n(e.g., 'my_account', 'business_account')"
        )

        if not ok or not account_name.strip():
            return

        account_name = account_name.strip()

        # Check if account already exists
        if account_name in self.tiktok_service.get_saved_accounts():
            reply = QMessageBox.question(
                self, "Account Exists",
                f"Account '{account_name}' already exists. Do you want to re-login?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self._log("INFO", f"Starting TikTok login for: {account_name}")
        self._log("INFO", "Browser will open - please login manually...")

        QMessageBox.information(
            self, "TikTok Login",
            f"A browser window will open.\n\n"
            f"Please login to TikTok account: {account_name}\n\n"
            f"After successful login, the browser will close automatically.\n"
            f"This may take a few moments..."
        )

        try:
            # Run login in separate thread to prevent GUI freeze
            from PyQt5.QtCore import QThread, pyqtSignal

            class LoginWorker(QThread):
                finished = pyqtSignal(bool, str)

                def __init__(self, service, account):
                    super().__init__()
                    self.service = service
                    self.account = account

                def run(self):
                    success, message = self.service.login_account(self.account)
                    self.finished.emit(success, message)

            self.login_worker = LoginWorker(self.tiktok_service, account_name)
            self.login_worker.finished.connect(lambda success, msg: self._on_login_completed(success, msg, account_name))
            self.login_worker.start()

            self.status_label.setText(f"Logging in to {account_name}...")
            self._show_toast("Browser opening...")

        except Exception as e:
            error_msg = f"Login error: {str(e)}"
            self._log("ERROR", error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    def _on_login_completed(self, success: bool, message: str, account_name: str):
        """Handle login completion"""
        if success:
            self._log("INFO", f"✓ Login successful: {account_name}")
            self._show_toast(f"Login successful: {account_name}")
            QMessageBox.information(self, "Success", message)
            self._refresh_tiktok_accounts()
            self.status_label.setText("Ready")
        else:
            self._log("ERROR", f"✗ Login failed: {message}")
            QMessageBox.critical(self, "Login Failed", message)
            self.status_label.setText("Login failed")

    def _on_tiktok_delete_account(self):
        """Handle account deletion"""
        selected = self.tiktok_accounts_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select an account to delete")
            return

        account_name = selected[0].text()

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete account '{account_name}'?\n\n"
            "This will remove the saved session cookies.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        success, message = self.tiktok_service.delete_account(account_name)

        if success:
            self._log("INFO", message)
            self._show_toast(f"Deleted: {account_name}")
            self._refresh_tiktok_accounts()
        else:
            self._log("ERROR", message)
            QMessageBox.critical(self, "Error", message)

    def _on_tiktok_browse_video(self):
        """Browse for TikTok video file"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.avi *.mov *.webm *.mkv *.flv);;All Files (*.*)"
        )

        if path:
            self.tiktok_video_edit.setText(path)

            # Validate video
            valid, message = self.tiktok_service.validate_video(path)
            if valid:
                self._log("INFO", f"Video selected: {message}")
            else:
                self._log("WARNING", f"Video warning: {message}")
                QMessageBox.warning(self, "Video Warning", message)

    def _on_tiktok_caption_changed(self):
        """Update character count for caption"""
        text = self.tiktok_title_edit.toPlainText()
        char_count = len(text)
        self.tiktok_char_label.setText(f"{char_count} / 2200 characters")

        if char_count > 2200:
            self.tiktok_char_label.setStyleSheet("color: #ff6b6b; font-style: italic; font-weight: bold;")
        else:
            self.tiktok_char_label.setStyleSheet("color: #aaa; font-style: italic;")

    def _on_tiktok_upload(self):
        """Handle TikTok video upload"""
        if not self.tiktok_service.is_available():
            QMessageBox.warning(self, "Warning", "TikTok service not available")
            return

        # Validate inputs
        selected_accounts = self.tiktok_accounts_list.selectedItems()
        if not selected_accounts:
            QMessageBox.warning(self, "Warning", "Please select an account")
            return

        account_name = selected_accounts[0].text()
        if account_name.startswith("No accounts"):
            QMessageBox.warning(self, "Warning", "Please login to an account first")
            return

        video_path = self.tiktok_video_edit.text().strip()
        if not video_path:
            QMessageBox.warning(self, "Warning", "Please select a video file")
            return

        caption = self.tiktok_title_edit.toPlainText().strip()
        if not caption:
            reply = QMessageBox.question(
                self, "No Caption",
                "Upload without a caption?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        if len(caption) > 2200:
            QMessageBox.warning(self, "Warning", "Caption is too long (max 2200 characters)")
            return

        # Get settings
        schedule_time = self.tiktok_schedule_hours.currentData()
        is_private = self.tiktok_is_private.isChecked()

        if is_private and schedule_time > 0:
            QMessageBox.warning(self, "Warning", "Private videos cannot be scheduled")
            return

        # Confirm upload
        schedule_text = "now" if schedule_time == 0 else f"in {self.tiktok_schedule_hours.currentText()}"
        privacy_text = "private" if is_private else "public"

        reply = QMessageBox.question(
            self, "Confirm Upload",
            f"Upload video to TikTok?\n\n"
            f"Account: {account_name}\n"
            f"Video: {Path(video_path).name}\n"
            f"Caption: {caption[:50]}{'...' if len(caption) > 50 else ''}\n"
            f"Privacy: {privacy_text}\n"
            f"Schedule: {schedule_text}\n"
            f"Comments: {'allowed' if self.tiktok_allow_comment.isChecked() else 'disabled'}\n"
            f"Duet: {'allowed' if self.tiktok_allow_duet.isChecked() else 'disabled'}\n"
            f"Stitch: {'allowed' if self.tiktok_allow_stitch.isChecked() else 'disabled'}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Start upload worker
        self._log("STEP", f"Starting TikTok upload to account: {account_name}")
        self.btn_tiktok_upload.setEnabled(False)
        self.status_label.setText("Uploading to TikTok...")

        from PyQt5.QtCore import QThread, pyqtSignal

        class TikTokUploadWorker(QThread):
            finished = pyqtSignal(bool, str)
            log = pyqtSignal(str, str)

            def __init__(self, service, account, video, caption, settings):
                super().__init__()
                self.service = service
                self.account = account
                self.video = video
                self.caption = caption
                self.settings = settings

            def run(self):
                try:
                    self.log.emit("INFO", "Starting TikTok upload...")
                    success, message = self.service.upload(
                        account_name=self.account,
                        video_path=self.video,
                        title=self.caption,
                        **self.settings
                    )
                    self.finished.emit(success, message)
                except Exception as e:
                    self.finished.emit(False, f"Upload error: {str(e)}")

        settings = {
            'schedule_time': schedule_time,
            'allow_comment': self.tiktok_allow_comment.isChecked(),
            'allow_duet': self.tiktok_allow_duet.isChecked(),
            'allow_stitch': self.tiktok_allow_stitch.isChecked(),
            'is_private': is_private
        }

        self.tiktok_worker = TikTokUploadWorker(
            self.tiktok_service, account_name, video_path, caption, settings
        )
        self.tiktok_worker.log.connect(self._log)
        self.tiktok_worker.finished.connect(self._on_tiktok_upload_completed)
        self.tiktok_worker.start()

    def _on_tiktok_upload_completed(self, success: bool, message: str):
        """Handle upload completion"""
        self.btn_tiktok_upload.setEnabled(True)

        if success:
            self._log("STEP", f"✓ TikTok upload successful!")
            self._log("INFO", message)
            self._show_toast("Upload successful!")
            self.status_label.setText("Upload completed")
            QMessageBox.information(self, "Success", message)

            # Clear form
            self.tiktok_video_edit.clear()
            self.tiktok_title_edit.clear()
        else:
            self._log("ERROR", f"✗ TikTok upload failed: {message}")
            self.status_label.setText("Upload failed")
            QMessageBox.critical(self, "Upload Failed", message)

    def closeEvent(self, event):
        self._save_session()
        super().closeEvent(event)

    def _apply_dark_theme(self):
        app = QApplication.instance()
        if not app:
            return
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, QColor(64, 128, 255))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)
        app.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #444; border-radius: 6px; margin-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QPushButton { padding: 6px 10px; }
            QLineEdit, QTextEdit, QListWidget { border: 1px solid #555; border-radius: 4px; }
        """)

    def _apply_icons(self):
        style = self.style()
        self.btn_browse.setIcon(style.standardIcon(QStyle.SP_DirOpenIcon))
        self.btn_get_info.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        self.btn_start.setIcon(style.standardIcon(QStyle.SP_MediaPlay))
        self.btn_stop.setIcon(style.standardIcon(QStyle.SP_MediaStop))
        self.btn_clear_log.setIcon(style.standardIcon(QStyle.SP_DialogResetButton))
        self.btn_add_apk.setIcon(style.standardIcon(QStyle.SP_FileDialogNewFolder))
        self.btn_remove_apk.setIcon(style.standardIcon(QStyle.SP_TrashIcon))
        self.btn_clear_apk.setIcon(style.standardIcon(QStyle.SP_DialogResetButton))


class FileDropLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for url in urls:
            local = url.toLocalFile()
            if local:
                p = Path(local)
                if p.suffix.lower() in {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}:
                    self.setText(local)
                    mw = self.window()
                    if hasattr(mw, 'title_edit') and isinstance(mw.title_edit, QLineEdit):
                        if not mw.title_edit.text().strip():
                            name = p.stem.replace('_', ' ').replace('-', ' ')
                            mw.title_edit.setText(name.title())
                    break
        super().dropEvent(event)


class Toast(QWidget):
    def __init__(self, parent: QMainWindow, message: str):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.label = QLabel(message)
        self.label.setStyleSheet(
            "background-color: rgba(30,30,30,200); color: white; padding: 10px 14px;"
            "border-radius: 6px;"
        )
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.adjustSize()

        # position bottom-right
        parent_geom = parent.geometry()
        x = parent_geom.x() + parent_geom.width() - self.width() - 24
        y = parent_geom.y() + parent_geom.height() - self.height() - 24
        self.move(QPoint(x, y))

    def show_for(self, msec: int = 2000):
        self.show()
        QTimer.singleShot(msec, self.close)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


