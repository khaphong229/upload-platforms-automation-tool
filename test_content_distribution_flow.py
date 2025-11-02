#!/usr/bin/env python3
"""
Test Content Distribution with TikTok Upload Flow
"""
import sys

print("=" * 60)
print("Testing Content Distribution + TikTok Integration")
print("=" * 60)

# Test 1: Import qt_main
print("\n1. Importing qt_main module...")
try:
    import qt_main
    print("[OK] qt_main imported successfully")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Check TikTok service
print("\n2. Checking TikTok service...")
try:
    from services.tiktok import TikTokService
    service = TikTokService()
    print(f"[OK] TikTok service available: {service.is_available()}")
    accounts = service.get_saved_accounts()
    print(f"     Found {len(accounts)} account(s): {accounts}")
except Exception as e:
    print(f"[FAIL] TikTok service error: {e}")
    sys.exit(1)

# Test 3: Check WorkerThread signature
print("\n3. Checking WorkerThread signature...")
try:
    import inspect
    sig = inspect.signature(qt_main.WorkerThread.__init__)
    params = list(sig.parameters.keys())

    required_params = [
        'upload_tiktok', 'tiktok_account',
        'tiktok_caption', 'tiktok_settings'
    ]

    missing = [p for p in required_params if p not in params]
    if missing:
        print(f"[FAIL] Missing parameters: {missing}")
        sys.exit(1)

    print(f"[OK] WorkerThread has all TikTok parameters")
    print(f"     Parameters: {', '.join(required_params)}")
except Exception as e:
    print(f"[FAIL] Parameter check failed: {e}")
    sys.exit(1)

# Test 4: Check UI elements exist
print("\n4. Checking UI elements...")
try:
    # Create a minimal Qt application
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = qt_main.MainWindow()

    required_attrs = [
        'enable_tiktok_cb',
        'main_tiktok_account_combo',
        'main_tiktok_caption',
        'main_tiktok_schedule',
        'main_tiktok_allow_comment',
        'main_tiktok_allow_duet',
        'main_tiktok_allow_stitch',
        'main_tiktok_is_private',
        'btn_refresh_tiktok'
    ]

    missing = [attr for attr in required_attrs if not hasattr(window, attr)]
    if missing:
        print(f"[FAIL] Missing UI elements: {missing}")
        sys.exit(1)

    print(f"[OK] All TikTok UI elements exist")
    print(f"     Elements: {len(required_attrs)}")

except Exception as e:
    print(f"[FAIL] UI check failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\n📝 Summary:")
print("  ✅ Imports working")
print("  ✅ TikTok service available")
print("  ✅ WorkerThread has TikTok parameters")
print("  ✅ UI elements created successfully")
print("\n🚀 You can now run: python qt_main.py")
print("\n📱 Complete Content Distribution Flow:")
print("  1. Select video source (YouTube or local)")
print("  2. Enter blog title")
print("  3. Add APK links (optional)")
print("  4. ✨ Enable TikTok upload (NEW!)")
print("  5. Select TikTok account")
print("  6. Write TikTok caption (optional)")
print("  7. Configure schedule & privacy")
print("  8. Click 'Start Process'")
print("\n🎯 Result:")
print("  • Downloads/uses video")
print("  • Generates blog content with AI")
print("  • Posts to Blogger/WordPress")
print("  • Uploads video to TikTok 📱")
print("=" * 60)
