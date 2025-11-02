# Complete Content Distribution Workflow with TikTok Upload

## Overview

The **Content Distribution** tab now includes integrated TikTok upload functionality, allowing you to process a video through a complete workflow:

1. **Download/Select Video** (YouTube or local)
2. **Generate Blog Content** with AI
3. **Post to Blog** (Blogger or WordPress)
4. **Upload to TikTok** (NEW!)

All in one automated flow!

---

## Features Added

### Main Content Distribution Tab

- **TikTok Upload Section** (optional)
  - Enable/disable TikTok upload with checkbox
  - Account selection from saved accounts
  - Custom caption editor (2200 char limit)
  - Schedule options (now to 1 day)
  - Privacy controls (Comments, Duet, Stitch, Private)
  - Character counter with visual feedback

### Workflow Integration

- TikTok upload runs after blog post creation
- Uses the same video from YouTube download or local file
- Can use blog title as caption (if not specified)
- Non-blocking - failures don't stop the whole process
- Progress tracking with status updates

---

## How to Use

### Step-by-Step Guide

#### 1. Video Source
- **YouTube**: Enter URL, click "Get Info" (optional)
- **Local**: Browse to select video file

#### 2. Blog Settings
- Enter **blog title**
- Select **content language** (Vietnamese/English)
- Add **APK links** (optional)

#### 3. TikTok Upload (NEW!)
- ✅ Check **"Upload to TikTok"**
- Select **TikTok account** from dropdown
  - If no accounts, login via "TikTok Upload" tab first
  - Click 🔄 Refresh to reload accounts
- Write **caption** (optional)
  - Leave empty to use blog title
  - Max 2200 characters
  - Supports hashtags (#) and mentions (@)
- Configure **settings**:
  - Schedule: Post Now / 1 hour / 3 hours / 12 hours / 1 day
  - ✅ Comments (allow comments)
  - ✅ Duet (allow duets)
  - ✅ Stitch (allow stitch)
  - ✅ Private (private video)

#### 4. Processing Options
- ☐ Skip Download (use existing video)
- ☐ Skip Blog Creation (only TikTok)
- ☐ Save as Draft (blog draft mode)
- ✅ Generate AI Images (for blog)

#### 5. Start Process
- Click **"Start Process"**
- Monitor progress in status bar and log
- Wait for completion

---

## Workflow Steps

### Complete Flow (All Enabled)

```
1. 🎬 Download/Prepare Video
   ↓
2. 🔗 Shorten APK Links
   ↓
3. 🤖 Generate Blog Content with AI
   ↓
4. 👀 Preview & Approve Content
   ↓
5. 📝 Post to Blogger/WordPress
   ↓
6. 📱 Upload to TikTok (NEW!)
   ↓
7. ✅ Done!
```

### Flexible Options

**Blog Only:**
- Uncheck "Upload to TikTok"
- Process stops after blog post

**TikTok Only:**
- Check "Skip Blog Creation"
- Check "Upload to TikTok"
- Goes straight to TikTok upload

**Video + Blog:**
- Check "Upload to TikTok"
- Uploads video after blog post

---

## UI Components

### TikTok Upload Section

```
┌─────────────────────────────────────────────┐
│ 📱 TikTok Upload (Optional)                │
├─────────────────────────────────────────────┤
│ ☐ Upload to TikTok                         │
│                                             │
│   Account: [test ▼] [🔄 Refresh]           │
│                                             │
│   Caption:                                  │
│   ┌───────────────────────────────────────┐│
│   │ TikTok caption...                     ││
│   │                                       ││
│   └───────────────────────────────────────┘│
│   0 / 2200 characters                       │
│                                             │
│   Schedule: [Post Now ▼]                   │
│   ☑ Comments  ☐ Duet  ☐ Stitch  ☐ Private │
└─────────────────────────────────────────────┘
```

### Status Messages

During TikTok upload, you'll see:

- `[STEP] Uploading to TikTok`
- `[INFO] Uploading to TikTok account: test`
- `[INFO] Video: my_video.mp4`
- `[INFO] Caption: My awesome video...`
- `[INFO] TikTok upload successful: Video uploaded successfully!`
- `● TikTok upload complete`

---

## Example Use Cases

### Case 1: Full Distribution
**Goal:** Download YouTube video, create blog post, upload to TikTok

```
1. Video Source: YouTube URL
2. Title: "Best Android App 2025"
3. APK Links: Add download links
4. Enable TikTok: ✅
5. TikTok Account: my_account
6. TikTok Caption: "Check out this amazing app! #android #app"
7. Schedule: 3 hours
8. Click "Start Process"
```

**Result:**
- ✅ Video downloaded
- ✅ Blog post created
- ✅ Uploaded to TikTok (scheduled for 3 hours)

### Case 2: Local Video to TikTok Only
**Goal:** Upload existing video to TikTok without blog

```
1. Video Source: Local file
2. Browse: my_video.mp4
3. Title: "Sample Title"
4. Skip Blog Creation: ✅
5. Enable TikTok: ✅
6. TikTok Account: test
7. TikTok Caption: "New video! 🎬"
8. Click "Start Process"
```

**Result:**
- ✅ Used local video
- ⏭️ Skipped blog
- ✅ Uploaded to TikTok immediately

### Case 3: Blog First, TikTok Later
**Goal:** Create blog post now, schedule TikTok for later

```
1. Video Source: YouTube
2. Blog settings configured
3. Enable TikTok: ✅
4. Schedule: 1 day
5. Click "Start Process"
```

**Result:**
- ✅ Blog posted immediately
- ⏰ TikTok scheduled for tomorrow

---

## Technical Details

### WorkerThread Parameters

```python
WorkerThread(
    # Video source
    video_source="youtube",  # or "local"
    youtube_url="https://...",
    local_path="/path/to/video.mp4",
    title="My Video Title",

    # Blog settings
    apk_links=[("App Name", "https://...")],
    skip_download=False,
    skip_blog=False,
    draft_mode=False,
    blog_platform="blogger",  # or "wordpress"
    wordpress_config={...},
    language="vietnamese",  # or "english"
    generate_images=True,

    # TikTok settings (NEW!)
    upload_tiktok=True,
    tiktok_account="test",
    tiktok_caption="My caption",
    tiktok_settings={
        'schedule_time': 3600,  # seconds
        'allow_comment': True,
        'allow_duet': False,
        'allow_stitch': False,
        'is_private': False
    }
)
```

### Workflow Logic

```python
# Step 5: TikTok Upload (if enabled)
if self.upload_tiktok and video_info:
    # Get video path from previous step
    video_path = video_info.get('file_path')

    # Use caption or fallback to title
    caption = self.tiktok_caption or self.title

    # Upload via TikTok service
    service = TikTokService()
    success, message = service.upload(
        account_name=self.tiktok_account,
        video_path=video_path,
        title=caption,
        **self.tiktok_settings
    )
```

---

## Error Handling

### TikTok Service Not Available
- Shows warning message
- Continues with blog post
- Doesn't fail entire process

### No Account Selected
- Validation at start
- Prompts to select account or disable TikTok

### Caption Too Long
- Validates before starting
- Max 2200 characters
- Shows error message

### Upload Fails
- Logs error message
- Doesn't stop workflow
- Blog post still created

---

## Settings Persistence

The following TikTok settings are saved in `last_session.json`:

```json
{
  "enable_tiktok": true,
  "tiktok_account": "test",
  "tiktok_caption": "My caption",
  ...
}
```

Restored on app restart for convenience.

---

## Benefits

### 1. **Unified Workflow**
- One process for all platforms
- No manual video uploads
- Consistent publishing

### 2. **Time Saving**
- Automated end-to-end
- Scheduled posting
- Batch processing possible

### 3. **Flexibility**
- Enable/disable platforms
- Custom captions per platform
- Schedule independently

### 4. **Professional**
- Error handling
- Progress tracking
- Status logging

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Start Process | Alt+S |
| Stop Process | Alt+T |
| Clear Log | Alt+C |
| Refresh TikTok | Alt+R |

---

## Tips & Tricks

### 1. **Pre-Login to TikTok**
Login to your TikTok accounts in the "TikTok Upload" tab before using Content Distribution. This ensures accounts are ready.

### 2. **Test with Local Videos**
Use local video files first to test the workflow without downloading from YouTube.

### 3. **Use Scheduling**
Schedule TikTok posts for optimal engagement times while creating blog posts immediately.

### 4. **Caption Strategy**
- Leave caption empty to reuse blog title
- Write custom caption for TikTok-specific hashtags
- Include calls-to-action

### 5. **Monitor Progress**
Watch the log for detailed status updates and any errors.

---

## Troubleshooting

### Issue: TikTok account dropdown empty

**Solution:**
1. Go to "TikTok Upload" tab
2. Click "Login New Account"
3. Complete login in browser
4. Return to "Content Distribution" tab
5. Click 🔄 Refresh button

### Issue: TikTok upload fails

**Possible causes:**
- Video file too large (max 1800MB)
- Caption too long (max 2200 chars)
- Account session expired
- Network connection issues

**Solution:**
1. Check error message in log
2. Verify video file size
3. Re-login if session expired
4. Retry upload

### Issue: Can't schedule private videos

**Explanation:**
TikTok doesn't allow scheduling private videos. Either:
- Uncheck "Private" to allow scheduling
- Set schedule to "Post Now" for private videos

---

## Workflow Comparison

### Before (Manual):
```
1. Download video from YouTube
2. Open browser
3. Create blog post manually
4. Upload video
5. Open TikTok
6. Upload video again
7. Write caption
8. Schedule post
```
**Time:** 30-45 minutes

### After (Automated):
```
1. Enter YouTube URL
2. Configure settings
3. Click "Start Process"
4. ☕ Wait
```
**Time:** 5-10 minutes (mostly automated)

---

## Coming Soon

Potential future enhancements:
- ✨ Auto-generate TikTok captions with AI
- ✨ Multi-account batch upload
- ✨ Video editing/trimming
- ✨ Thumbnail generation
- ✨ Analytics tracking
- ✨ More social platforms

---

## Summary

The **Content Distribution** workflow now provides:

✅ Complete automation from video → blog → TikTok
✅ Flexible options for each platform
✅ Scheduling and privacy controls
✅ Progress tracking and error handling
✅ Session persistence
✅ Professional UI with validations

**Start using it today for effortless content distribution across all your platforms!**

---

**Last Updated:** 2025-11-01
**Version:** 2.0
**Status:** ✅ Production Ready
