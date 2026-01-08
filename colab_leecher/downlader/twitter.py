# copyright 2024 © tele-leech-new

import re
import logging
import requests
from os import path as ospath


def get_twitter_video_url(tweet_url: str) -> str:
    """
    Get direct video URL from Twitter using ssstwitter.com service.
    1. GET homepage to extract dynamic tokens (tt, ts).
    2. POST to get the download links.
    """
    try:
        session = requests.Session()
        home_url = "https://ssstwitter.com/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        
        # 1. GET homepage for tokens
        logging.info("Getting tokens from ssstwitter homepage...")
        home_resp = session.get(home_url, headers=headers, timeout=15)
        if home_resp.status_code != 200:
            logging.error(f"Failed to get ssstwitter homepage: {home_resp.status_code}")
            return ""
            
        # Extract tt and ts from the form's include-vals or hx-vals
        # Format can be: include-vals="tt:'...',ts:...,source:'form'"
        html = home_resp.text
        
        # More flexible regex that handles quoted and unquoted values
        tt_match = re.search(r'tt\s*:\s*[\'"]?([a-f0-9]{32})[\'"]?', html)
        ts_match = re.search(r'ts\s*:\s*(\d+)', html)
        
        if not tt_match or not ts_match:
            # Try alternate pattern (json-like or attribute names)
            tt_match = re.search(r'["\']tt["\']\s*[:=]\s*["\']?([^"\',]+)["\']?', html)
            ts_match = re.search(r'["\']ts["\']\s*[:=]\s*["\']?(\d+)["\']?', html)
            
        if not tt_match or not ts_match:
            logging.error(f"Could not find dynamic tokens (tt/ts) on ssstwitter homepage. HTML preview: {html[:500]}")
            return ""
            
        tt = tt_match.group(1)
        ts = ts_match.group(1)
        logging.info(f"Extracted tokens: tt={tt[:5]}..., ts={ts}")

        # 2. POST to get download links
        api_url = "https://ssstwitter.com/r" # Note: response is actually HTML
        post_headers = headers.copy()
        post_headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://ssstwitter.com",
            "Referer": "https://ssstwitter.com/",
            "HX-Request": "true",
            "HX-Target": "target",
            "HX-Current-URL": "https://ssstwitter.com/",
        })
        
        data = {
            "id": tweet_url,
            "locale": "en",
            "tt": tt,
            "ts": ts,
            "source": "form"
        }
        
        logging.info(f"Fetching links for: {tweet_url}")
        response = session.post(api_url, headers=post_headers, data=data, timeout=30)
        
        if response.status_code == 200:
            html_res = response.text
            
            # The links are in <a class="download_link" href="...">
            # Use a more specific pattern for ssscdn links or twimg links
            video_pattern = r'href=["\'](https://[^"\']*ssscdn\.io[^"\']+)["\']'
            matches = re.findall(video_pattern, html_res)
            
            if not matches:
                # Try fallback pattern for direct twimg links
                video_pattern = r'href=["\'](https://[^"\']*twimg\.com[^"\']*\.mp4[^"\']*)["\']'
                matches = re.findall(video_pattern, html_res)
            
            if matches:
                # Get unique links
                video_urls = list(set(matches))
                
                # Sort by quality indicators in URL
                def get_quality(url):
                    for q in ['1080', '720', '480', '360', '240']:
                        if f"_{q}_" in url or f"/{q}/" in url or q in url:
                            return int(q)
                    return 0
                
                video_urls.sort(key=get_quality, reverse=True)
                best_url = video_urls[0]
                logging.info(f"Successfully found video URL: {best_url[:60]}...")
                return best_url
            else:
                logging.warning("No video download links found in response HTML")
                # Log a bit of the HTML for debugging if needed
                return ""
        else:
            logging.error(f"POST request failed: {response.status_code}")
            return ""
            
    except Exception as e:
        logging.error(f"Scraping error: {e}")
        return ""


def is_twitter_link(link: str) -> bool:
    """Check if link is a Twitter/X URL."""
    result = "twitter.com" in link or "x.com" in link
    logging.info(f"is_twitter_link check: '{link[:50]}...' = {result}")
    return result


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
