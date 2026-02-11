#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test script to verify TikTok integration
"""
import sys
import os
from pathlib import Path

# Fix Windows console encoding
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Test 1: Import TikTok service
print("=" * 50)
print("Test 1: Importing TikTok service...")
try:
    from services.tiktok import TikTokService
    print("[OK] TikTok service imported successfully")
except ImportError as e:
    print(f"[FAIL] Failed to import TikTok service: {e}")
    sys.exit(1)

# Test 2: Initialize TikTok service
print("\n" + "=" * 50)
print("Test 2: Initializing TikTok service...")
try:
    tiktok_service = TikTokService()
    print(f"[OK] TikTok service initialized")
    print(f"  - Available: {tiktok_service.is_available()}")
except Exception as e:
    print(f"[FAIL] Failed to initialize TikTok service: {e}")
    sys.exit(1)

# Test 3: Check TikTokAutoUploader path
print("\n" + "=" * 50)
print("Test 3: Checking TikTokAutoUploader path...")
uploader_path = Path(__file__).parent.parent / "TiktokAutoUploader"
print(f"  - Path: {uploader_path}")
print(f"  - Exists: {uploader_path.exists()}")

if uploader_path.exists():
    print(f"  - Contents:")
    for item in sorted(uploader_path.iterdir())[:10]:
        print(f"    - {item.name}")
else:
    print("  [WARN] TikTokAutoUploader not found at expected location")

# Test 4: Get saved accounts
print("\n" + "=" * 50)
print("Test 4: Getting saved TikTok accounts...")
try:
    accounts = tiktok_service.get_saved_accounts()
    print(f"[OK] Found {len(accounts)} saved account(s)")
    if accounts:
        for acc in accounts:
            print(f"  - {acc}")
    else:
        print("  (No accounts saved)")
except Exception as e:
    print(f"[FAIL] Failed to get accounts: {e}")

# Test 5: Check directories
print("\n" + "=" * 50)
print("Test 5: Checking required directories...")
try:
    cookies_dir = tiktok_service.get_cookies_dir()
    videos_dir = tiktok_service.get_videos_dir()
    print(f"  - Cookies dir: {cookies_dir} (exists: {cookies_dir.exists()})")
    print(f"  - Videos dir: {videos_dir} (exists: {videos_dir.exists()})")
except Exception as e:
    print(f"[FAIL] Error checking directories: {e}")

# Test 6: Validate a dummy video path
print("\n" + "=" * 50)
print("Test 6: Testing video validation...")
test_video = "test_video.mp4"
valid, message = tiktok_service.validate_video(test_video)
print(f"  - Result: {message}")

print("\n" + "=" * 50)
print("[OK] All tests completed!")
print("=" * 50)
