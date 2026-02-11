#!/usr/bin/env python3
"""Test that working directory is correctly managed"""

import os
from pathlib import Path


def test_working_directory_restoration():
    """Test that working directory is saved and restored"""

    print("Testing working directory management:\n")

    # Get initial working directory
    initial_cwd = os.getcwd()
    print(f"Initial working directory: {initial_cwd}")

    # Simulate what happens in the TikTokService methods
    try:
        # Save current directory
        original_cwd = os.getcwd()
        print(f"Saved working directory: {original_cwd}")

        # Change to a different directory
        tiktok_uploader_path = Path(r"E:\Workspace\Tool\TiktokAutoUploader")
        if tiktok_uploader_path.exists():
            os.chdir(str(tiktok_uploader_path))
            print(f"Changed to: {os.getcwd()}")

            # Simulate some work
            print(f"Working in TikTokAutoUploader directory...")
            print(f"CookiesDir would be at: {Path.cwd() / 'CookiesDir'}")
        else:
            print(f"TikTokAutoUploader directory not found: {tiktok_uploader_path}")

    finally:
        # Restore original directory
        os.chdir(original_cwd)
        print(f"Restored to: {os.getcwd()}")

    # Verify we're back to the initial directory
    final_cwd = os.getcwd()
    success = (final_cwd == initial_cwd)

    print("\n" + "=" * 60)
    if success:
        print("[PASS] Working directory correctly restored!")
    else:
        print(f"[FAIL] Working directory not restored: {final_cwd} != {initial_cwd}")

    return success


def test_cookies_dir_location():
    """Test where cookies directory would be created"""

    print("\n\nTesting CookiesDir location:\n")

    tiktok_project = Path(r"E:\Workspace\Tool\Tiktok")
    tiktok_uploader = Path(r"E:\Workspace\Tool\TiktokAutoUploader")

    print(f"This project:        {tiktok_project}")
    print(f"TikTokAutoUploader:  {tiktok_uploader}")
    print()

    # Where cookies SHOULD be saved
    correct_location = tiktok_uploader / "CookiesDir"
    print(f"Correct location:    {correct_location}")

    # Where cookies were being saved (wrong)
    wrong_location = tiktok_project / "CookiesDir"
    print(f"Wrong location:      {wrong_location}")
    print()

    # Check if TikTokAutoUploader exists
    if tiktok_uploader.exists():
        print("[PASS] TikTokAutoUploader directory exists")

        # Check if CookiesDir exists there
        if correct_location.exists():
            print(f"[INFO] CookiesDir exists at correct location")

            # List any cookie files
            cookie_files = list(correct_location.glob("*.cookie"))
            if cookie_files:
                print(f"[INFO] Found {len(cookie_files)} cookie file(s):")
                for cf in cookie_files:
                    print(f"  - {cf.name}")
            else:
                print("[INFO] No cookie files found yet")
        else:
            print("[INFO] CookiesDir doesn't exist yet (will be created on first login)")
    else:
        print("[FAIL] TikTokAutoUploader directory not found!")
        print("       Please ensure it exists at the correct path")
        return False

    return True


if __name__ == "__main__":
    test1 = test_working_directory_restoration()
    test2 = test_cookies_dir_location()

    print("\n" + "=" * 60)
    if test1 and test2:
        print("All tests passed!")
    else:
        print("Some tests failed!")
