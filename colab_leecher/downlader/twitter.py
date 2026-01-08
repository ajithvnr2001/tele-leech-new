# copyright 2024 © tele-leech-new

import re
import logging
import requests
from os import path as ospath


def get_twitter_video_url(tweet_url: str) -> str:
    """
    Get direct video URL from Twitter using ssstwitter.com service.
    Returns the highest quality video URL or empty string if failed.
    """
    try:
        # ssstwitter.com API endpoint
        api_url = "https://ssstwitter.com/r"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://ssstwitter.com",
            "Referer": "https://ssstwitter.com/",
        }
        
        # Form data
        data = {
            "id": tweet_url,
            "locale": "en",
            "tt": "",  # Token, might need to be extracted from page
        }
        
        logging.info(f"Fetching Twitter video via ssstwitter: {tweet_url}")
        
        response = requests.post(api_url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            html = response.text
            
            # Find all video URLs in the response
            # Pattern for direct MP4 links from Twitter CDN
            video_pattern = r'href="(https://[^"]*twimg\.com[^"]*\.mp4[^"]*)"'
            matches = re.findall(video_pattern, html)
            
            if matches:
                # Get highest quality (usually last or has highest resolution in URL)
                video_urls = list(set(matches))  # Remove duplicates
                
                # Sort by quality indicators in URL (1080, 720, 480, etc.)
                def get_quality(url):
                    for q in ['1080', '720', '480', '360', '240']:
                        if q in url:
                            return int(q)
                    return 0
                
                video_urls.sort(key=get_quality, reverse=True)
                
                best_url = video_urls[0]
                logging.info(f"Found Twitter video URL: {best_url[:80]}...")
                return best_url
            else:
                logging.warning("No video URLs found in ssstwitter response")
                return ""
        else:
            logging.error(f"ssstwitter request failed with status: {response.status_code}")
            return ""
            
    except Exception as e:
        logging.error(f"Error getting Twitter video URL: {e}")
        return ""


def is_twitter_link(link: str) -> bool:
    """Check if link is a Twitter/X URL."""
    return "twitter.com" in link or "x.com" in link


async def download_twitter_video(tweet_url: str, download_path: str) -> str:
    """
    Download Twitter video using ssstwitter.com.
    Returns the path to downloaded file or empty string if failed.
    """
    import subprocess
    
    video_url = get_twitter_video_url(tweet_url)
    
    if not video_url:
        return ""
    
    # Extract filename from URL or use tweet ID
    tweet_id_match = re.search(r'/status/(\d+)', tweet_url)
    if tweet_id_match:
        filename = f"twitter_{tweet_id_match.group(1)}.mp4"
    else:
        filename = "twitter_video.mp4"
    
    output_path = ospath.join(download_path, filename)
    
    # Download using aria2c
    cmd = [
        "aria2c",
        "-x16",
        "-d", download_path,
        "-o", filename,
        video_url
    ]
    
    try:
        logging.info(f"Downloading Twitter video to: {output_path}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logging.info(f"Successfully downloaded: {filename}")
            return output_path
        else:
            logging.error(f"aria2c failed: {result.stderr}")
            return ""
    except Exception as e:
        logging.error(f"Download error: {e}")
        return ""
