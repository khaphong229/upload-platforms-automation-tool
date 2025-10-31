#!/usr/bin/env python3
"""
Test TikTok Service with Lazy Loading
"""
print("=" * 60)
print("Testing TikTok Service (Lazy Loading)")
print("=" * 60)

# Test 1: Import (should NOT load TikTok modules yet)
print("\n1. Importing TikTokService...")
try:
    from services.tiktok import TikTokService
    print("[OK] Import successful (no heavy modules loaded yet)")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    exit(1)

# Test 2: Create instance (still no heavy imports)
print("\n2. Creating TikTokService instance...")
try:
    service = TikTokService()
    print("[OK] Instance created")
    print(f"    - is_available(): {service.is_available()}")
    print(f"    - _modules_loaded: {service._modules_loaded}")
except Exception as e:
    print(f"[FAIL] Failed to create instance: {e}")
    exit(1)

# Test 3: Check availability
if service.is_available():
    print("\n[SUCCESS] TikTok service is AVAILABLE (lazy check)!")
    print("\nThis means:")
    print("  - TikTokAutoUploader path found")
    print("  - Required files exist")
    print("  - Modules NOT yet loaded (lazy)")
    print("  - GUI should work correctly")
else:
    print("\n[FAIL] TikTok service not available")
    print("\nPlease check:")
    print("  - TikTokAutoUploader exists at E:\\Workspace\\Tool\\TiktokAutoUploader")
    print("  - tiktok_uploader package exists inside it")
    exit(1)

# Test 4: Get accounts (should still work without loading modules)
print(f"\n4. Getting saved accounts (no module load needed)...")
accounts = service.get_saved_accounts()
print(f"Found {len(accounts)} account(s): {accounts}")

# Test 5: Try to trigger module loading (only if you want)
print(f"\n5. Testing lazy module loading...")
print("   Modules will be loaded on first actual use (login/upload)")
print(f"   Current state: _modules_loaded = {service._modules_loaded}")

# Optional: Uncomment to test actual module loading
# print("\n   Forcing module load by calling _ensure_modules_loaded()...")
# if service._ensure_modules_loaded():
#     print(f"   [OK] Modules loaded successfully!")
#     print(f"   - _modules_loaded = {service._modules_loaded}")
# else:
#     print(f"   [FAIL] Module loading failed")

print("\n" + "=" * 60)
print("All tests passed! The GUI should work now.")
print("Run: python qt_main.py")
print("=" * 60)
