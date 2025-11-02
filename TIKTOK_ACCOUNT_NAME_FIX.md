# TikTok Account Name Bug Fix

## Problems

The TikTok login functionality had two critical issues:

### Issue 1: Account Names with Spaces/Special Characters

Account names with spaces or special characters (e.g., "ppt mod") caused a `FileNotFoundError` because:
1. The cookie file path contained spaces: `tiktok_session-ppt mod.cookie`
2. File systems may not handle spaces in filenames properly

### Issue 2: Wrong Cookie Directory

Cookies were being saved in the **wrong directory**:
- **Wrong**: `E:\Workspace\Tool\Tiktok\CookiesDir\` (this project)
- **Correct**: `E:\Workspace\Tool\TiktokAutoUploader\CookiesDir\` (TikTokAutoUploader directory)

This happened because the TikTokAutoUploader library uses relative paths (`./CookiesDir`), so cookies were saved relative to the current working directory.

### Error Message
```
FileNotFoundError: [Errno 2] No such file or directory:
'E:\\Workspace\\Tool\\Tiktok\\./CookiesDir\\tiktok_session-ppt mod.cookie'
```

## Solution

### 1. Account Name Sanitization

Added a `sanitize_account_name()` function that:
- Replaces spaces with underscores
- Removes special characters (keeps only alphanumeric, underscore, hyphen)
- Removes consecutive underscores
- Trims leading/trailing underscores

**Examples:**
- `"ppt mod"` → `"ppt_mod"`
- `"my account"` → `"my_account"`
- `"user@123"` → `"user_123"`
- `"test___multiple___spaces"` → `"test_multiple_spaces"`

### 2. Working Directory Management (Critical Fix!)

Updated `login_account()` and `upload()` to temporarily change the working directory:

```python
# Save current working directory
original_cwd = os.getcwd()

try:
    # Change to TikTokAutoUploader directory
    if self._uploader_path:
        os.chdir(str(self._uploader_path))

    # Now cookies are saved/loaded from the correct location!
    session_id = self.login(sanitized_name)

finally:
    # Always restore original directory
    os.chdir(original_cwd)
```

This ensures:
- Cookies are saved in `E:\Workspace\Tool\TiktokAutoUploader\CookiesDir\`
- Cookies are loaded from the same location during upload
- Working directory is always restored, even if errors occur

### 3. Directory Creation

Updated `get_cookies_dir()` to automatically create the `CookiesDir` directory if it doesn't exist.

### 4. Backward Compatibility

All methods now support both original and sanitized account names:
- `login_account()`: Sanitizes names before login, warns user if name was changed
- `upload()`: Tries both original and sanitized names
- `delete_account()`: Tries to delete both original and sanitized cookie files

## Files Modified

1. **services/tiktok.py**
   - Added `sanitize_account_name()` function
   - Updated `login_account()` to:
     - Sanitize account names
     - Change working directory to TikTokAutoUploader
     - Create CookiesDir if needed
     - Restore working directory after login (in finally block)
   - Updated `upload()` to:
     - Handle both original and sanitized names
     - Change working directory to TikTokAutoUploader
     - Restore working directory after upload (in finally block)
   - Updated `delete_account()` to handle both name formats
   - Updated `get_cookies_dir()` to auto-create directory
   - Updated `get_saved_accounts()` with better logging

2. **.gitignore**
   - Added `CookiesDir/` to ignore cookie files
   - Added `*.cookie` to ignore all cookie files

## Testing

### Test 1: Account Name Sanitization

```bash
python test_tiktok_account_sanitization.py
```

This verifies that account names are correctly sanitized.

### Test 2: Working Directory Management

```bash
python test_working_directory.py
```

This verifies:
- Working directory is correctly changed and restored
- Cookies are saved in the correct location (`TikTokAutoUploader/CookiesDir`)
- Lists any existing cookie files

**Expected Output:**
```
[PASS] Working directory correctly restored!
[PASS] TikTokAutoUploader directory exists
[INFO] CookiesDir exists at correct location
[INFO] Found X cookie file(s)
```

## Usage

### Login with Account Names Containing Spaces

When logging in with an account name containing spaces or special characters:

```python
# Before (would fail):
tiktok.login_account("ppt mod")  # Error!

# After (automatically sanitized):
tiktok.login_account("ppt mod")  # Works! Saved as "ppt_mod"
# User gets a warning: "Account name was sanitized from 'ppt mod' to 'ppt_mod'"
```

### Best Practices

1. **Use simple account names:** Use only letters, numbers, underscores, and hyphens
2. **Avoid spaces:** Use underscores instead of spaces
3. **Avoid special characters:** Stick to alphanumeric characters

**Good examples:**
- `my_account`
- `business-account`
- `user123`

**Bad examples (will be sanitized):**
- `my account` (has space)
- `user@work` (has @)
- `test#1` (has #)

## Migration

If you have existing accounts with spaces in the name, they will still work:
- Old cookie files remain unchanged
- New logins automatically use sanitized names
- Upload and delete operations check both original and sanitized names

## Security Note

Cookie files contain sensitive session information. The `.gitignore` file has been updated to prevent accidentally committing these files to version control.

## Summary

### Critical Fixes Applied

✅ **Account names with spaces now work correctly** - Automatically sanitized
✅ **Special characters handled safely** - Converted to underscores
✅ **Cookies saved in CORRECT location** - `TikTokAutoUploader/CookiesDir`
✅ **Working directory properly managed** - Always restored after operations
✅ **Directory created automatically** - No manual setup needed
✅ **Backward compatible** - Works with existing accounts
✅ **Cookie files protected** - Added to .gitignore
✅ **All tests pass** - Both sanitization and directory tests

### What Changed

**Before:**
- ❌ Account names with spaces caused FileNotFoundError
- ❌ Cookies saved in wrong directory (`Tiktok/CookiesDir`)
- ❌ Manual directory creation required

**After:**
- ✅ Account names automatically sanitized
- ✅ Cookies saved in correct directory (`TikTokAutoUploader/CookiesDir`)
- ✅ Automatic directory creation
- ✅ Working directory always restored
- ✅ Comprehensive error handling

### Verification

Run both test scripts to verify everything works:

```bash
# Test account name sanitization
python test_tiktok_account_sanitization.py

# Test working directory management
python test_working_directory.py
```

Both should show `All tests passed!`
