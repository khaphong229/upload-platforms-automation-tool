# AI Configuration & Prompt Management Guide

## Overview

The TikTok Content Distribution Tool now includes advanced AI configuration and prompt management features that allow you to:

- **Configure multiple AI providers** (Google Gemini, OpenAI GPT, Anthropic Claude, or Custom APIs)
- **Manage custom prompts** for blog post and TikTok caption generation
- **Fine-tune AI parameters** (temperature, max tokens, models)
- **Create and organize prompt templates** for different content styles

---

## Features

### 1. AI Provider Configuration

#### Supported Providers

| Provider | Models Available | Notes |
|----------|-----------------|-------|
| **Google Gemini** | gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash | Default provider, optimized for speed |
| **OpenAI GPT** | gpt-4, gpt-4-turbo, gpt-3.5-turbo | High-quality content generation |
| **Anthropic Claude** | claude-3-opus, claude-3-sonnet, claude-3-haiku | Advanced reasoning capabilities |
| **Custom API** | User-defined | Connect to any OpenAI-compatible API |

#### Provider Settings

For each provider, you can configure:

- **API Key**: Your authentication key for the AI service
- **Model**: The specific model variant to use
- **Temperature**: Controls creativity (0.0 = deterministic, 1.0 = very creative)
- **Max Tokens**: Maximum length of generated content
- **Enabled**: Toggle provider on/off

---

### 2. Prompt Management System

#### Prompt Types

1. **Blog Post Prompts** - Templates for generating blog article content
2. **TikTok Caption Prompts** - Templates for short-form social media captions

#### Default Prompts

The system includes pre-configured prompt templates:

**Blog Prompts:**
- `default_blog` - Standard blog post format
- `gaming_blog` - Optimized for gaming apps
- `app_review_blog` - Review-style format with pros/cons

**TikTok Prompts:**
- `default_tiktok` - Standard engaging caption
- `viral_tiktok` - Viral-style with FOMO elements

#### Creating Custom Prompts

Custom prompts support template variables:

**For Blog Posts:**
- `{title}` - Blog post title
- `{video_title}` - YouTube video title
- `{video_description}` - YouTube video description
- `{apk_links_text}` - Formatted list of APK download links

**For TikTok Captions:**
- `{title}` - Video/content title
- `{blog_url}` - URL to the blog post
- `{max_length}` - Maximum caption length

**Example Blog Prompt:**
```
Write a comprehensive blog post about the following video and app:

TITLE: {title}

VIDEO INFORMATION:
Title: {video_title}
Description: {video_description}

APK DOWNLOAD LINKS:
{apk_links_text}

The blog post should:
1. Have an engaging introduction about the app/game
2. Describe key features and benefits
3. Include the download links prominently
4. Have a clear call-to-action
5. Be SEO-friendly with appropriate headings and structure
6. Be between 500-800 words

Format the blog post in HTML with appropriate tags (h1, h2, p, ul, li, etc.)
```

**Example TikTok Prompt:**
```
Create a short, engaging TikTok caption (maximum {max_length} characters) for a video about '{title}'.
Include emojis and make it attention-grabbing. The caption should encourage viewers to check out
the blog post at {blog_url} for download links.
```

---

## How to Use

### Accessing AI Settings

**In PyQt5 GUI (qt_main.py):**
1. Launch the application: `python qt_main.py`
2. Navigate to the **"AI Settings"** tab
3. Click **"Open AI Settings"** button

**In Tkinter GUI (gui_main.py):**
1. Launch the application: `python gui_main.py`
2. Click the **"Settings"** button
3. Navigate to the **"AI Configuration"** tab

---

### Configuring an AI Provider

1. Open AI Settings
2. Go to **"AI Provider"** tab
3. Select a provider from the dropdown
4. Enable the provider with the checkbox
5. Enter your **API Key**
6. Select your preferred **Model**
7. Adjust **Temperature** (0.0-1.0) and **Max Tokens**
8. Click **"Save Provider Settings"**

#### Getting API Keys

- **Google Gemini**: https://makersuite.google.com/app/apikey
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys

---

### Creating a Custom Prompt

1. Open AI Settings
2. Go to **"Prompt Management"** tab
3. Select prompt type (Blog Post or TikTok Caption)
4. Click **"New Prompt"**
5. Enter a name for your prompt
6. Write your template using the available placeholders
7. Click **"Save"**

---

### Editing or Deleting Prompts

- **Edit**: Select a prompt from the list, click **"Edit Prompt"**
- **Delete**: Select a prompt, click **"Delete Prompt"**
- **Set as Default**: Select a prompt, click **"Set as Default"**

**Note:** Default prompts (marked with ★) cannot be edited or deleted.

---

## Configuration Files

The AI settings are stored in JSON files in your project directory:

### `ai_config.json`
Stores AI provider configurations and selected prompts:

```json
{
  "active_provider": "gemini",
  "providers": {
    "gemini": {
      "api_key": "YOUR_API_KEY",
      "model": "gemini-2.0-flash",
      "temperature": 0.7,
      "max_tokens": 1000,
      "enabled": true
    }
  },
  "prompts": {
    "blog_post": "default_blog",
    "tiktok_caption": "default_tiktok"
  }
}
```

### `prompts.json`
Stores all prompt templates:

```json
{
  "default_blog": {
    "name": "Default Blog Post",
    "template": "Write a comprehensive blog post...",
    "type": "blog",
    "is_default": true,
    "created_at": "2025-01-15T10:30:00"
  }
}
```

---

## Best Practices

### Temperature Settings

| Use Case | Recommended Temperature |
|----------|------------------------|
| Factual content | 0.1 - 0.3 |
| Balanced creativity | 0.5 - 0.7 |
| Creative writing | 0.8 - 1.0 |

### Max Tokens

| Content Type | Recommended Tokens |
|--------------|-------------------|
| Short captions | 100 - 200 |
| Blog posts | 800 - 1500 |
| Long articles | 2000 - 4000 |

### Prompt Engineering Tips

1. **Be Specific**: Clearly define the desired output format
2. **Use Examples**: Include sample output in your prompt
3. **Set Constraints**: Specify word count, tone, style
4. **Include Context**: Provide relevant background information
5. **Test and Iterate**: Refine prompts based on results

---

## Troubleshooting

### API Key Errors

**Problem**: "API key not configured for provider"

**Solution**:
1. Open AI Settings
2. Ensure the provider is enabled
3. Verify API key is correctly entered
4. Check API key validity on the provider's website

### Empty or Poor Quality Output

**Problem**: Generated content is low quality

**Solutions**:
- Increase temperature for more creativity
- Increase max tokens for longer content
- Try a different model (e.g., GPT-4 instead of GPT-3.5)
- Refine your prompt template with more specific instructions

### Prompt Variable Errors

**Problem**: "Missing variable {X} for prompt template"

**Solution**: Ensure your prompt uses only the supported variables for that prompt type:
- Blog: `{title}`, `{video_title}`, `{video_description}`, `{apk_links_text}`
- TikTok: `{title}`, `{blog_url}`, `{max_length}`

---

## Advanced: Custom API Provider

To use a custom OpenAI-compatible API:

1. Select **"custom"** as the provider
2. Enter your **API URL** (e.g., `https://api.example.com/v1/chat/completions`)
3. Enter your **API Key**
4. Specify a **Model name**
5. Configure temperature and max tokens
6. Enable and save

---

## API Usage and Costs

Be aware of API usage costs:

| Provider | Pricing Model | Approximate Cost (1000 tokens) |
|----------|--------------|-------------------------------|
| Google Gemini | Pay per token | ~$0.00025 - $0.001 |
| OpenAI GPT-3.5 | Pay per token | ~$0.002 |
| OpenAI GPT-4 | Pay per token | ~$0.03 - $0.06 |
| Anthropic Claude | Pay per token | ~$0.008 - $0.024 |

**Tip**: Monitor your API usage through the provider's dashboard to avoid unexpected charges.

---

## Examples

### Example 1: Gaming Blog Prompt

```
Create an exciting blog post about the following gaming app:

TITLE: {title}

VIDEO INFORMATION:
Title: {video_title}
Description: {video_description}

DOWNLOAD LINKS:
{apk_links_text}

Write a blog post that:
1. Opens with a hook about why this game is trending
2. Describes gameplay mechanics and unique features
3. Highlights graphics, controls, and user experience
4. Includes download links with clear installation instructions
5. Has sections: Introduction, Features, Gameplay, Download Guide
6. Uses gaming-related keywords for SEO
7. Length: 600-900 words
8. Format in HTML with proper heading tags
```

### Example 2: Viral TikTok Caption

```
Create a viral-style TikTok caption (max {max_length} chars) for '{title}'.

Requirements:
- Use trending emojis (🔥💯⚡)
- Create FOMO (fear of missing out)
- Include a question to boost engagement
- Mention: "Download link in bio! {blog_url}"
- Keep it energetic and exciting
```

---

## Support

For issues or questions:
1. Check the main README.md
2. Review the logs in `app.log`
3. Verify API keys and configuration in `.env` file
4. Test with default prompts first before using custom ones

---

## Future Enhancements

Planned features:
- [ ] Support for additional AI providers (Cohere, AI21, etc.)
- [ ] Prompt versioning and history
- [ ] A/B testing for prompts
- [ ] Batch prompt testing
- [ ] Prompt marketplace/sharing

---

*Last Updated: January 2025*
