#!/usr/bin/env python3
"""Debug TikTok upload process"""

import os
import sys
from pathlib import Path

# Add TikTokAutoUploader to path
tiktok_uploader_path = Path(r"E:\Workspace\Tool\TiktokAutoUploader")
if str(tiktok_uploader_path) not in sys.path:
    sys.path.insert(0, str(tiktok_uploader_path))

os.chdir(str(tiktok_uploader_path))
print(f"Working directory: {os.getcwd()}")

from services.tiktok import TikTokService


def test_upload_with_logging():
    """Test upload with detailed logging"""

    print("=" * 60)
    print("TikTok Upload Debug Test")
    print("=" * 60)

    # Initialize service
    print("\n[1/6] Initializing TikTok service...")
    tiktok = TikTokService()

    if not tiktok.is_available():
        print("[FAIL] TikTok service not available")
        print(tiktok.get_last_error())
        return False
    print("[PASS] Service available")

    # Load modules
    print("\n[2/6] Loading modules...")
    if not tiktok._ensure_modules_loaded():
        print("[FAIL] Failed to load modules")
        print(tiktok.get_last_error())
        return False
    print("[PASS] Modules loaded")

    # Check saved accounts
    print("\n[3/6] Checking saved accounts...")
    accounts = tiktok.get_saved_accounts()
    if not accounts:
        print("[FAIL] No accounts found. Please login first.")
        return False
    print(f"[PASS] Found {len(accounts)} account(s): {', '.join(accounts)}")

    # Select account
    account_name = accounts[0]
    print(f"\n[4/6] Using account: {account_name}")

    # Find a test video
    print("\n[5/6] Looking for test video...")
    videos_dir = tiktok.get_videos_dir()
    print(f"Videos directory: {videos_dir}")

    if not videos_dir.exists():
        print(f"[WARN] Videos directory doesn't exist, creating it...")
        videos_dir.mkdir(parents=True, exist_ok=True)

    # Look for any video file
    video_extensions = ['.mp4', '.avi', '.mov', '.webm', '.mkv', '.flv']
    video_files = []
    for ext in video_extensions:
        video_files.extend(list(videos_dir.glob(f"*{ext}")))

    if not video_files:
        print("[FAIL] No video files found in VideosDirPath")
        print(f"Please add a test video to: {videos_dir}")
        return False

    video_file = video_files[0]
    print(f"[PASS] Found video: {video_file.name}")
    print(f"       Size: {video_file.stat().st_size / (1024*1024):.2f} MB")

    # Test upload
    print("\n[6/6] Testing upload process...")
    print("="  * 60)

    test_title = f"Test Upload - {account_name}"
    print(f"Video: {video_file}")
    print(f"Account: {account_name}")
    print(f"Title: {test_title}")
    print(f"Settings: Public, Comments ON, Duet OFF, Stitch OFF")
    print()

    try:
        success, message = tiktok.upload(
            account_name=account_name,
            video_path=str(video_file),
            title=test_title,
            schedule_time=0,  # Post now
            allow_comment=True,
            allow_duet=False,
            allow_stitch=False,
            is_private=False
        )

        print("\n" + "=" * 60)
        if success:
            print("[SUCCESS] Upload completed!")
            # Handle Unicode encoding for Vietnamese messages
            safe_message = message.encode('ascii', errors='replace').decode('ascii') if message else ""
            print(f"Message: {safe_message}")
            return True
        else:
            print("[FAIL] Upload failed!")
            safe_error = message.encode('ascii', errors='replace').decode('ascii') if message else ""
            print(f"Error: {safe_error}")
            return False

    except Exception as e:
        print("\n" + "=" * 60)
        safe_error = str(e).encode('ascii', errors='replace').decode('ascii')
        print(f"[ERROR] Exception during upload: {safe_error}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_upload_with_logging()
    sys.exit(0 if success else 1)
