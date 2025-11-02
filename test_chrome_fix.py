#!/usr/bin/env python3
"""Test Chrome and create simple TikTok upload"""
import os, sys
from pathlib import Path

# Change to TikTokAutoUploader directory
os.chdir(r"E:\Workspace\Tool\TiktokAutoUploader")
sys.path.insert(0, str(Path.cwd()))

print("Testing TikTok upload from TiktokAutoUploader directory...")
print(f"CWD: {os.getcwd()}")

from tiktok_uploader.tiktok import upload_video

# Test upload
video = "pre-processed.mp4"
account = "ppt_mod"
title = "Test from script"

print(f"\nUploading:")
print(f"  Video: {video}")
print(f"  Account: {account}")
print(f"  Title: {title}")
print()

result = upload_video(
    session_user=account,
    video=video,
    title=title,
    schedule_time=0,
    allow_comment=1,
    allow_duet=0,
    allow_stitch=0,
    visibility_type=0,
    brand_organic_type=0,
    branded_content_type=0,
    ai_label=0
)

print(f"\nResult: {result}")
sys.exit(0 if result else 1)
