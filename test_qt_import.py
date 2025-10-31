#!/usr/bin/env python3
"""
Test that qt_main.py can import without errors
"""
import sys

print("=" * 60)
print("Testing qt_main.py imports...")
print("=" * 60)

try:
    print("\n1. Importing qt_main module...")
    # This will trigger all imports including TikTokService
    import qt_main
    print("[OK] qt_main imported successfully!")

    print("\n2. Checking TikTokService...")
    from services.tiktok import TikTokService
    service = TikTokService()
    print(f"[OK] TikTokService available: {service.is_available()}")
    print(f"     Modules loaded: {service._modules_loaded}")
    print(f"     Accounts: {service.get_saved_accounts()}")

    print("\n" + "=" * 60)
    print("SUCCESS! qt_main.py can be imported without errors.")
    print("The TikTok integration is working with lazy loading.")
    print("\nYou can now run: python qt_main.py")
    print("=" * 60)

except ImportError as e:
    print(f"\n[FAIL] Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

except Exception as e:
    print(f"\n[FAIL] Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
