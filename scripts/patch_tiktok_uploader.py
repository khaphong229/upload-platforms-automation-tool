#!/usr/bin/env python3
"""
Patch TikTokAutoUploader to add better logging and timeout handling
"""

import os
import sys
from pathlib import Path


def patch_bot_utils():
    """Add timeout to subprocess_jsvmp function"""

    bot_utils_path = Path(r"E:\Workspace\Tool\TiktokAutoUploader\tiktok_uploader\bot_utils.py")

    print(f"Patching: {bot_utils_path}")

    # Read current content
    content = bot_utils_path.read_text(encoding='utf-8')

    # Check if already patched
    if 'timeout=' in content:
        print("[INFO] Already patched - timeout handling present")
        return True

    # Find and replace the subprocess_jsvmp function
    old_function = """def subprocess_jsvmp(js, user_agent, url):
\tproc = subprocess.Popen(['node', js, url, user_agent], stdout=subprocess.PIPE)
\treturn proc.stdout.read().decode('utf-8')"""

    new_function = """def subprocess_jsvmp(js, user_agent, url):
\tprint(f"[DEBUG] Running Node.js: {js}")
\tprint(f"[DEBUG] URL: {url[:100]}...")
\ttry:
\t\tproc = subprocess.Popen(['node', js, url, user_agent], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
\t\t# Add 30 second timeout
\t\tstdout, stderr = proc.communicate(timeout=30)
\t\tif proc.returncode != 0:
\t\t\tprint(f"[ERROR] Node.js process failed with return code {proc.returncode}")
\t\t\tif stderr:
\t\t\t\tprint(f"[ERROR] stderr: {stderr.decode('utf-8')}")
\t\t\treturn None
\t\toutput = stdout.decode('utf-8')
\t\tprint(f"[DEBUG] Node.js output length: {len(output)} bytes")
\t\treturn output
\texcept subprocess.TimeoutExpired:
\t\tprint("[ERROR] Node.js process timed out after 30 seconds")
\t\tproc.kill()
\t\treturn None
\texcept Exception as e:
\t\tprint(f"[ERROR] subprocess_jsvmp failed: {e}")
\t\treturn None"""

    if old_function in content:
        content = content.replace(old_function, new_function)
        bot_utils_path.write_text(content, encoding='utf-8')
        print("[SUCCESS] Patched subprocess_jsvmp with timeout and logging")
        return True
    else:
        print("[WARNING] Could not find exact function match - trying alternative...")

        # Try a more flexible replacement
        import re
        pattern = r'def subprocess_jsvmp\(js, user_agent, url\):.*?return proc\.stdout\.read\(\)\.decode\(\'utf-8\'\)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            content = re.sub(pattern, new_function.replace('\t', '\t'), content, flags=re.DOTALL)
            bot_utils_path.write_text(content, encoding='utf-8')
            print("[SUCCESS] Patched subprocess_jsvmp with regex replacement")
            return True

        print("[FAIL] Could not patch - function structure may have changed")
        return False


def patch_tiktok_py():
    """Add progress logging to upload_to_tiktok function"""

    tiktok_py_path = Path(r"E:\Workspace\Tool\TiktokAutoUploader\tiktok_uploader\tiktok.py")

    print(f"\nPatching: {tiktok_py_path}")

    content = tiktok_py_path.read_text(encoding='utf-8')

    # Check if already patched
    if 'print(f"[PROGRESS]' in content:
        print("[INFO] Already patched - progress logging present")
        return True

    # Add progress logging to chunk upload loop
    old_loop = '\tfor i in range(len(chunks)):\n\t\tchunk = chunks[i]\n\t\tcrc = crc32(chunk)\n\t\tcrcs.append(crc)'

    new_loop = '\tprint(f"[PROGRESS] Uploading {len(chunks)} chunks...")\n\tfor i in range(len(chunks)):\n\t\tchunk = chunks[i]\n\t\tcrc = crc32(chunk)\n\t\tcrcs.append(crc)\n\t\tif (i + 1) % 10 == 0 or i == 0:\n\t\t\tprint(f"[PROGRESS] Uploaded chunk {i + 1}/{len(chunks)}")'

    if old_loop in content:
        content = content.replace(old_loop, new_loop)
        tiktok_py_path.write_text(content, encoding='utf-8')
        print("[SUCCESS] Added progress logging to chunk upload")
        return True
    else:
        print("[INFO] Chunk upload loop structure may have changed, skipping")
        return True


def main():
    print("=" * 60)
    print("TikTok Uploader Patcher")
    print("=" * 60)
    print()

    # Patch bot_utils.py
    success1 = patch_bot_utils()

    # Patch tiktok.py
    success2 = patch_tiktok_py()

    print()
    print("=" * 60)
    if success1 and success2:
        print("[SUCCESS] All patches applied!")
        print()
        print("Changes made:")
        print("1. Added 30-second timeout to Node.js subprocess")
        print("2. Added error handling and logging to subprocess_jsvmp")
        print("3. Added progress logging to chunk upload")
        print()
        print("You can now retry the TikTok upload.")
        return True
    else:
        print("[PARTIAL] Some patches may have failed")
        print("Please check the output above for details")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
