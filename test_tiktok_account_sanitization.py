#!/usr/bin/env python3
"""Test TikTok account name sanitization"""

from services.tiktok import sanitize_account_name


def test_sanitize_account_name():
    """Test various account names"""
    test_cases = [
        ("ppt mod", "ppt_mod"),
        ("my account", "my_account"),
        ("test-user", "test-user"),
        ("user@123", "user_123"),
        ("normal_name", "normal_name"),
        ("user with   spaces", "user_with_spaces"),
        ("user#$%^&*", "user"),
        ("_leading_underscore_", "leading_underscore"),
        ("test___multiple___underscores", "test_multiple_underscores"),
    ]

    print("Testing account name sanitization:\n")
    all_passed = True

    for original, expected in test_cases:
        result = sanitize_account_name(original)
        passed = result == expected
        status = "[PASS]" if passed else "[FAIL]"

        print(f"{status}: '{original}' -> '{result}' (expected: '{expected}')")

        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed!")
    else:
        print("Some tests failed!")

    return all_passed


if __name__ == "__main__":
    test_sanitize_account_name()
