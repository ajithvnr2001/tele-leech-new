# Full Bot Development & Enhancement Progress

This document provides a comprehensive, technical record of all enhancements, refactors, and diagnostic work performed on the Tele-Leech bot.

---

## 🚀 1. Twitter/X Video Downloader (Advanced Scrapers)
We significantly improved the reliability and quality of Twitter/X video weight extraction by implementing a dual-source prioritized system.

### **Primary Source: TwitterVideoDownloader.com (TVD)**
- **Technical Implementation**: 
    - Implemented a custom scraper in `twitter.py` that handles a complex multi-step handshake.
    - **CSRF Token Handling**: Extracts `csrfmiddlewaretoken` from the landing page.
    - **GQL Token Extraction**: Dynamically parses the site's JavaScript assets to find the current `gql` authorization token required for their backend API.
    - **Session Persistence**: Uses a `requests.Session` to maintain cookies across the token-fetching and POST request phases.
- **Outcome**: Successfully extracts direct `*.twimg.com` CDN links, which are more stable and provide higher bandwidth than third-party proxies.

### **Fallback Source: SSSTwitter.com (SSS)**
- **Technical Implementation**:
    - Integrated as a secondary source using a payload-based scraping method.
    - Automatically extracts `tt` and `ts` tokens from the form to authenticate the POST request.
- **Outcome**: Provides a robust safety net in case TVD changes its structure or is temporarily down.

### **Multi-Quality Logic**
- **Detected Qualities**: Instead of just grabbing the highest resolution, the scraper now extracts **all** detected resolutions (e.g., 270p, 360p, 720p, 1080p).
- **Sorting**: URLs are sorted by resolution to ensure logical order during download.
- **Consistent Interface**: The `get_twitter_video_url` function acts as an orchestrator, returning an empty list `[]` on failure instead of a null value, preventing crashes in the caller.

---

## 🛠️ 2. Core Logic Refactor: Sequential Multi-Link Processing
This was a major architectural update to optimize the bot for Google Colab's 75GB disk limit and provide a better UX.

### **New Workflow: Download ➔ Process ➔ Upload ➔ Cleanup**
- **Old Behavior**: The bot would download *every* link in a multi-line message to the `Downloads/` folder first. Only after the last download finished would it start zipping or uploading. 
    - *Problem*: Downloading 5 links of 15GB each would hit 75GB and crash the Colab runtime before the first file was delivered.
- **New Behavior**: The loop was moved to the high-level task handlers (`Do_Leech` and `Do_Mirror`).
    - **Atomic Cycles**: Each link is now treated as an atomic task. Once Link 1 finishes its upload, its local files are deleted **immediately** before Link 2 begins downloading.
- **Component Changes**:
    - `task_manager.py`: Refactored `Do_Leech` and `Do_Mirror` to wrap the `downloadManager` call inside a per-link loop.
    - `manager.py`: Updated `downloadManager` to accept a `link_idx` parameter so the status message correctly says "Link 02/05" even though it's being called individually.

### **Supported Modes**
- **Regular Leech**: Files are uploaded to Telegram sequentially.
- **Zip Mode**: Each link is zipped into an individual archive and uploaded immediately.
- **Mirror Mode**: Files are copied to the mounted Google Drive sequentially, with timestamped subfolders for organization.
- **Cleanup**: Implemented `shutil.rmtree` on all temporary work directories (`Paths.temp_zpath`, `Paths.temp_unzip_path`, etc.) at the end of every link's cycle.

---

## 🔍 3. Diagnostic Research: Telegram Upload Errors
We performed a deep-dive into the `leech-log.txt` to solve user-reported failures.

- **The Symptoms**: Log showed infinite loops of `TimeoutError` and `Broken Pipe` during the `upload.SaveBigFilePart` operation.
- **Technical Finding**:
    - The connection to Telegram's `DC5 (media)` server was being reset by the host (Broken Pipe).
    - **Diagnosis**: This is a host-level network issue common in Google Colab when uploading large streams. It is not an error in the bot's logic but a limitation of the environment's network stability.
- **Recommended Mitigations**: 
    - Restarting the Colab runtime to get a fresh VM.
    - Using the bot's "Splitting" feature to keep parts smaller and less prone to timeout.
    - Using Mirror mode for files > 2GB.

---

## 💎 5. Subtitle Extractor Feature (/subex)
A new feature to extract internal subtitles from video files and upload them to Telegram.

### **Key Features**
- **FFmpeg Powered**: Uses `ffprobe` to detect subtitle tracks and `ffmpeg` to extract them
- **Smart Naming**: `filename_sub_lang.srt` (single) or `filename_sub_lang-N.srt` (multiple tracks)
- **Sequential Processing**:
  - **Links**: Download -> Extract -> Upload -> Delete video -> Next link
  - **Directories**: Copy one file at a time -> Extract -> Delete local copy -> Upload (source preserved)
- **Async Cancel Support**: Cancel button works during file operations via `asyncio.to_thread()`

### **Files Added/Modified**
- `colab_leecher/utility/sub_extractor.py` (NEW) - FFmpeg extraction logic
- `colab_leecher/__main__.py` - `/subex` command registration
- `colab_leecher/utility/task_manager.py` - `subex` mode handling
- `colab_leecher/utility/handler.py` - `SubLeech` function

---

## 📖 6. Documentation & Maintenance
- **Wiki Management**: Updated `INSTRUCTIONS.md` and `Home.md` in the `new_wiki` folder
- **README.md**: Added `/subex` feature to features list
- **GitHub Sync**: All changes committed and pushed to `main` branch

---
**Document Version**: 3.0 (Added /subex feature)
**Date**: 2026-01-12
