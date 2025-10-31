#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test TikTok service as it would be called from GUI
"""
import sys
import os

# Fix Windows console encoding
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("Testing TikTok Service (GUI Mode)")
print("=" * 60)

# Test exactly as GUI does
print("\n1. Importing TikTokService...")
from services.tiktok import TikTokService

print("[OK] Import successful")

print("\n2. Creating TikTokService instance...")
tiktok_service = TikTokService()

print(f"[OK] Instance created")
print(f"    - is_available(): {tiktok_service.is_available()}")

if tiktok_service.is_available():
    print("\n[SUCCESS] TikTok service is AVAILABLE!")
    print("\nThis means the GUI should work correctly now.")
    print("Please restart your Qt application: python qt_main.py")

    accounts = tiktok_service.get_saved_accounts()
    print(f"\nFound {len(accounts)} account(s): {accounts}")
else:
    print("\n[ERROR] TikTok service is NOT available!")
    print("\nThis is why the GUI shows the error banner.")
    print("Troubleshooting:")
    print("1. Check if E:\\Workspace\\Tool\\TiktokAutoUploader exists")
    print("2. Check if E:\\Workspace\\Tool\\TiktokAutoUploader\\tiktok_uploader exists")
    print("3. Try running: pip install undetected-chromedriver moviepy==1.0.3")

print("\n" + "=" * 60)
