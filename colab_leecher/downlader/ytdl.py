# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


import os
import glob
import logging
import yt_dlp
import subprocess
from asyncio import sleep
from threading import Thread
from os import makedirs, path as ospath
from colab_leecher.utility.handler import cancelTask
from colab_leecher.utility.variables import BOT, YTDL, MSG, Messages, Paths
from colab_leecher.utility.helper import getTime, keyboard, sizeUnit, status_bar, sysINFO


async def YTDL_Status(link, num):
    global Messages, YTDL
    name = await get_YT_Name(link)
    
    # Use different status header for hardcode mode
    if BOT.Mode.ytdl_hard:
        Messages.status_head = f"<b>📥 HARDCODE DOWNLOAD » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<code>{name}</code>\n"
    else:
        Messages.status_head = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<code>{name}</code>\n"

    YTDL_Thread = Thread(target=YouTubeDL, name="YouTubeDL", args=(link,))
    YTDL_Thread.start()

    while YTDL_Thread.is_alive():  # Until ytdl is downloading
        if YTDL.header:
            sys_text = sysINFO()
            message = YTDL.header
            try:
                await MSG.status_msg.edit_text(text=Messages.task_msg + Messages.status_head + message + sys_text, reply_markup=keyboard())
            except Exception:
                pass
        else:
            try:
                await status_bar(
                    down_msg=Messages.status_head,
                    speed=YTDL.speed,
                    percentage=float(YTDL.percentage),
                    eta=YTDL.eta,
                    done=YTDL.done,
                    left=YTDL.left,
                    engine="Xr-YtDL 🏮",
                )
            except Exception:
                pass

        await sleep(2.5)
    
    # Post-processing for hardcode mode
    if BOT.Mode.ytdl_hard:
        await hardcode_subtitles(Paths.down_path)


async def hardcode_subtitles(folder_path):
    """
    Find video files in the download folder and burn subtitles into them.
    Converts output to MKV format.
    """
    global Messages, MSG
    
    video_extensions = ('.mp4', '.mkv', '.webm', '.avi', '.mov')
    sub_extensions = ('.srt', '.vtt', '.ass')
    
    # Find all video files
    video_files = []
    for ext in video_extensions:
        video_files.extend(glob.glob(ospath.join(folder_path, f"*{ext}")))
        video_files.extend(glob.glob(ospath.join(folder_path, "**", f"*{ext}"), recursive=True))
    
    for video_path in video_files:
        video_dir = ospath.dirname(video_path)
        video_name = ospath.splitext(ospath.basename(video_path))[0]
        
        # Find matching subtitle file
        sub_path = None
        for sub_ext in sub_extensions:
            # Try exact match
            potential_sub = ospath.join(video_dir, f"{video_name}{sub_ext}")
            if ospath.exists(potential_sub):
                sub_path = potential_sub
                break
            # Try with language suffix (e.g., video.en.srt)
            for lang_sub in glob.glob(ospath.join(video_dir, f"{video_name}.*{sub_ext}")):
                if ospath.exists(lang_sub):
                    sub_path = lang_sub
                    break
            if sub_path:
                break
        
        if not sub_path:
            logging.warning(f"No subtitle found for: {video_name}")
            continue
        
        # Prepare output path (always MKV)
        output_path = ospath.join(video_dir, f"{video_name}_hardcoded.mkv")
        
        # Update status
        Messages.status_head = f"<b>🔥 BURNING SUBTITLES » </b>\n\n<code>{video_name}</code>\n"
        try:
            await MSG.status_msg.edit_text(
                text=Messages.task_msg + Messages.status_head + "\n⏳ __Processing with FFmpeg...__" + sysINFO(),
                reply_markup=keyboard()
            )
        except Exception:
            pass
        
        logging.info(f"Hardcoding subtitles: {video_path} + {sub_path}")
        
        # FFmpeg command to burn subtitles
        # Using subtitles filter for soft subs or hardcode
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', f"subtitles='{sub_path}'",
            '-c:v', 'libx264',
            '-crf', '23',
            '-preset', 'fast',
            '-c:a', 'copy',
            output_path
        ]
        
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)  # 2 hour timeout
            
            if process.returncode == 0 and ospath.exists(output_path) and ospath.getsize(output_path) > 0:
                # Success - remove original files
                os.remove(video_path)
                os.remove(sub_path)
                # Rename output to final name
                final_path = ospath.join(video_dir, f"{video_name}.mkv")
                os.rename(output_path, final_path)
                logging.info(f"Hardcode complete: {final_path}")
            else:
                logging.error(f"FFmpeg failed: {process.stderr}")
                # Cleanup failed output
                if ospath.exists(output_path):
                    os.remove(output_path)
        except subprocess.TimeoutExpired:
            logging.error(f"FFmpeg timeout for: {video_name}")
        except Exception as e:
            logging.error(f"Hardcode error: {e}")
    
    # Cleanup any remaining subtitle files
    for sub_ext in sub_extensions:
        for sub_file in glob.glob(ospath.join(folder_path, f"*{sub_ext}")):
            try:
                os.remove(sub_file)
            except Exception:
                pass


class MyLogger:
    def __init__(self):
        pass

    def debug(self, msg):
        global YTDL
        if "item" in str(msg):
            msgs = msg.split(" ")
            YTDL.header = f"\n⏳ __Getting Video Information {msgs[-3]} of {msgs[-1]}__"

    @staticmethod
    def warning(msg):
        pass

    @staticmethod
    def error(msg):
        # if msg != "ERROR: Cancelling...":
        # print(msg)
        pass


def YouTubeDL(url):
    global YTDL

    def my_hook(d):
        global YTDL

        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes", 0)  # Use 0 as default if total_bytes is None
            dl_bytes = d.get("downloaded_bytes", 0)
            percent = d.get("downloaded_percent", 0)
            speed = d.get("speed", "N/A")
            eta = d.get("eta", 0)

            if total_bytes:
                percent = round((float(dl_bytes) * 100 / float(total_bytes)), 2)

            YTDL.header = ""
            YTDL.speed = sizeUnit(speed) if speed else "N/A"
            YTDL.percentage = percent
            YTDL.eta = getTime(eta) if eta else "N/A"
            YTDL.done = sizeUnit(dl_bytes) if dl_bytes else "N/A"
            YTDL.left = sizeUnit(total_bytes) if total_bytes else "N/A"

        elif d["status"] == "downloading fragment":
            # log_str = d["message"]
            # print(log_str, end="")
            pass
        else:
            logging.info(d)

    # Base options
    ydl_opts = {
        "allow_multiple_video_streams": True,
        "allow_multiple_audio_streams": True,
        "writethumbnail": True,
        "--concurrent-fragments": 4 , # Set the maximum number of concurrent fragments
        "allow_playlist_files": True,
        "overwrites": True,
        "progress_hooks": [my_hook],
        "logger": MyLogger(),
    }
    
    # Configure based on mode
    if BOT.Mode.ytdl_hard:
        # Hardcode mode: best quality, download subtitles, no conversion (we'll do mkv later)
        ydl_opts.update({
            "format": "bestvideo+bestaudio/best",
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-US", "en-GB", "en.*"],
            "subtitlesformat": "srt/vtt/best",
            "postprocessors": [
                {"key": "FFmpegSubtitlesConvertor", "format": "srt"},
            ],
        })
    else:
        # Normal mode
        ydl_opts.update({
            "format": "best",
            "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
            "writesubtitles": "srt",
            "extractor_args": {"subtitlesformat": "srt"},
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if not ospath.exists(Paths.thumbnail_ytdl):
            makedirs(Paths.thumbnail_ytdl)
        try:
            info_dict = ydl.extract_info(url, download=False)
            YTDL.header = "⌛ __Please WAIT a bit...__"
            
            # In hardcode mode, playlists are pre-expanded, so treat everything as single video
            is_playlist = "_type" in info_dict and info_dict["_type"] == "playlist"
            
            if is_playlist and not BOT.Mode.ytdl_hard:
                # Normal mode: handle playlist internally
                playlist_name = info_dict["title"] 
                if not ospath.exists(ospath.join(Paths.down_path, playlist_name)):
                    makedirs(ospath.join(Paths.down_path, playlist_name))
                # Always use title-based naming
                ydl_opts["outtmpl"] = {
                    "default": f"{Paths.down_path}/{playlist_name}/%(title)s.%(ext)s",
                    "thumbnail": f"{Paths.thumbnail_ytdl}/%(id)s.%(ext)s",
                }
                for entry in info_dict["entries"]:
                    if entry is None:
                        continue
                    video_url = entry.get("webpage_url") or entry.get("url")
                    if not video_url:
                        continue
                    try:
                        ydl.download([video_url])
                    except yt_dlp.utils.DownloadError as e:
                        logging.error(f"Playlist video download error: {e}")
                        # Fallback to ID-based naming if title is too long
                        if hasattr(e, 'exc_info') and e.exc_info and e.exc_info[0] == 36:
                            ydl_opts["outtmpl"] = {
                                "default": f"{Paths.down_path}/{playlist_name}/%(id)s.%(ext)s",
                                "thumbnail": f"{Paths.thumbnail_ytdl}/%(id)s.%(ext)s",
                            }
                            ydl.download([video_url])
            else:
                # Single video (or hardcode mode with pre-expanded playlist)
                YTDL.header = ""
                # Use title-based naming for single videos too
                ydl_opts["outtmpl"] = {
                    "default": f"{Paths.down_path}/%(title)s.%(ext)s",
                    "thumbnail": f"{Paths.thumbnail_ytdl}/%(id)s.%(ext)s",
                }
                try:
                    ydl.download([url])
                except yt_dlp.utils.DownloadError as e:
                    logging.error(f"Single video download error: {e}")
                    # Fallback to ID-based naming if title is too long
                    if hasattr(e, 'exc_info') and e.exc_info and e.exc_info[0] == 36:
                        ydl_opts["outtmpl"] = {
                            "default": f"{Paths.down_path}/%(id)s.%(ext)s",
                            "thumbnail": f"{Paths.thumbnail_ytdl}/%(id)s.%(ext)s",
                        }
                        ydl.download([url])
        except Exception as e:
            logging.error(f"YTDL ERROR for URL '{url}': {e}")


async def get_YT_Name(link):
    with yt_dlp.YoutubeDL({"logger": MyLogger()}) as ydl:
        try:
            info = ydl.extract_info(link, download=False)
            if "title" in info and info["title"]: 
                return info["title"]
            else:
                return "UNKNOWN DOWNLOAD NAME"
        except Exception as e:
            logging.error(f"YTDL get_YT_Name ERROR for '{link}': {e}")
            await cancelTask(f"Can't Download from this link. Because: {str(e)}")
            return "UNKNOWN DOWNLOAD NAME"


def expand_playlist_urls(url):
    """
    If the URL is a playlist, return list of individual video URLs.
    If it's a single video, return list with just that URL.
    This allows sequential processing of playlist videos.
    """
    try:
        with yt_dlp.YoutubeDL({"logger": MyLogger(), "extract_flat": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info and "_type" in info and info["_type"] == "playlist":
                video_urls = []
                for entry in info.get("entries", []):
                    if entry is None:
                        continue
                    video_url = entry.get("webpage_url") or entry.get("url")
                    if video_url:
                        # Ensure full URL for playlist entries
                        if not video_url.startswith("http"):
                            video_url = f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                        video_urls.append(video_url)
                logging.info(f"Expanded playlist '{info.get('title', 'Unknown')}' to {len(video_urls)} videos")
                return video_urls
            else:
                return [url]
    except Exception as e:
        logging.error(f"Error expanding playlist: {e}")
        return [url]

