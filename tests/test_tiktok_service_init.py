#!/usr/bin/env python3
"""Test TikTok service initialization and config loading"""

from services.tiktok import TikTokService


def test_tiktok_service_initialization():
    """Test that TikTok service can be initialized without errors"""

    print("Testing TikTok service initialization:\n")

    try:
        # Create TikTok service instance
        print("[1/4] Creating TikTokService instance...")
        tiktok = TikTokService()
        print("      [PASS] Instance created")

        # Check if service is available
        print("\n[2/4] Checking if TikTok service is available...")
        is_available = tiktok.is_available()
        if is_available:
            print("      [PASS] TikTok service is available")
        else:
            print("      [FAIL] TikTok service not available")
            print(f"      Error: {tiktok.get_last_error()}")
            return False

        # Try to load modules (this is where the Config error was happening)
        print("\n[3/4] Loading TikTok modules and config...")
        modules_loaded = tiktok._ensure_modules_loaded()
        if modules_loaded:
            print("      [PASS] Modules loaded successfully")

            # Check if config was loaded
            if tiktok.config is not None:
                print("      [INFO] Config loaded successfully")
            else:
                print("      [WARN] Config not loaded (using defaults)")
        else:
            print("      [FAIL] Failed to load modules")
            print(f"      Error: {tiktok.get_last_error()}")
            return False

        # Get saved accounts
        print("\n[4/4] Getting saved accounts...")
        accounts = tiktok.get_saved_accounts()
        print(f"      [PASS] Found {len(accounts)} saved account(s)")
        if accounts:
            for account in accounts:
                print(f"      - {account}")

        print("\n" + "=" * 60)
        print("[SUCCESS] All tests passed!")
        print("TikTok service is working correctly!")
        return True

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"[FAIL] Error during initialization: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_tiktok_service_initialization()
    exit(0 if success else 1)
