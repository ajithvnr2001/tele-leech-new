# copyright 2024 © tele-leech-new

import re
import logging
import requests
from os import path as ospath


def get_tvd_video_urls(tweet_url: str) -> list:
    """
    Get direct video URLs from Twitter using twittervideodownloader.com service.
    1. GET homepage for dynamic tokens (csrf and gql) and session.
    2. POST to get download links.
    """
    try:
        session = requests.Session()
        home_url = "https://twittervideodownloader.com/en/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        
        # 1. GET homepage for tokens
        logging.info("Getting tokens from twittervideodownloader homepage...")
        home_resp = session.get(home_url, headers=headers, timeout=15)
        if home_resp.status_code != 200:
            logging.error(f"Failed to get TVD homepage: {home_resp.status_code}")
            return []
            
        html = home_resp.text
        csrf_token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
        gql_token = re.search(r'name="gql" value="([^"]+)"', html)
        
        if not csrf_token or not gql_token:
            logging.error("Could not find dynamic tokens on TVD homepage")
            return []
            
        csrf = csrf_token.group(1)
        gql = gql_token.group(1)
        logging.info("Extracted tokens from TVD")

        # 2. POST to get download links
        api_url = "https://twittervideodownloader.com/download"
        post_headers = headers.copy()
        post_headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://twittervideodownloader.com/en/",
            "Origin": "https://twittervideodownloader.com",
        })
        
        data = {
            "csrfmiddlewaretoken": csrf,
            "tweet": tweet_url,
            "gql": gql
        }
        
        logging.info(f"Fetching links from TVD for: {tweet_url}")
        response = session.post(api_url, headers=post_headers, data=data, timeout=30)
        
        if response.status_code == 200:
            html_res = response.text
            
            # Extract links from <a class="btn fw-bold tw-btn btn-sm" href="...">
            # The links are usually on Twitter CDN (twimg.com)
            matches = re.findall(r'href=["\'](https://[^"\']*twimg\.com[^"\']+\.mp4[^"\']*)["\']', html_res)
            
            if matches:
                # Get unique links
                video_urls = list(set(matches))
                
                # Sort by quality indicators in URL (higher = better)
                def get_quality(url):
                    import re as regex
                    res_match = regex.search(r'[/_](\d{3,4})[xp_/]', url)
                    if res_match:
                        return int(res_match.group(1))
                    for q in ['1080', '720', '480', '360', '240']:
                        if q in url:
                            return int(q)
                    return 0
                
                # Log all found URLs
                for url in video_urls:
                    logging.info(f"TVD Found video: quality={get_quality(url)}, url={url[:80]}...")
                
                video_urls.sort(key=get_quality, reverse=True)
                return video_urls
            else:
                logging.warning("No video download links found in TVD response")
                return []
        else:
            logging.error(f"TVD POST request failed: {response.status_code}")
            return []
            
    except Exception as e:
        logging.error(f"TVD scraping error: {e}")
        return []


def get_ssstwitter_urls(tweet_url: str) -> list:
    """
    Get direct video URLs from Twitter using ssstwitter.com service.
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
            return []
            
        html = home_resp.text
        tt_match = re.search(r'tt\s*:\s*[\'"]?([a-f0-9]{32})[\'"]?', html)
        ts_match = re.search(r'ts\s*:\s*(\d+)', html)
        
        if not tt_match or not ts_match:
            tt_match = re.search(r'["\']tt["\']\s*[:=]\s*["\']?([^"\',]+)["\']?', html)
            ts_match = re.search(r'["\']ts["\']\s*[:=]\s*["\']?(\d+)["\']?', html)
            
        if not tt_match or not ts_match:
            logging.error(f"Could not find tokens on ssstwitter. HTML preview: {html[:500]}")
            return []
            
        tt = tt_match.group(1)
        ts = ts_match.group(1)
        logging.info(f"Extracted ssstwitter tokens: tt={tt[:5]}..., ts={ts}")

        # 2. POST to get download links
        api_url = "https://ssstwitter.com/"
        post_headers = headers.copy()
        post_headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
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
        
        logging.info(f"Fetching links from ssstwitter for: {tweet_url}")
        response = session.post(api_url, headers=post_headers, data=data, timeout=30)
        
        if response.status_code == 200:
            html_res = response.text
            video_pattern = r'href=["\'](https://[^"\']*ssscdn\.io[^"\']+)["\']'
            matches = re.findall(video_pattern, html_res)
            
            if not matches:
                video_pattern = r'href=["\'](https://[^"\']*twimg\.com[^"\']*\.mp4[^"\']*)["\']'
                matches = re.findall(video_pattern, html_res)
            
            if matches:
                video_urls = list(set(matches))
                def get_quality(url):
                    import re as regex
                    res_match = regex.search(r'[/_](\d{3,4})[xp_/]', url)
                    if res_match:
                        return int(res_match.group(1))
                    for q in ['1080', '720', '480', '360', '240']:
                        if q in url:
                            return int(q)
                    return 0
                
                for url in video_urls:
                    logging.info(f"Ssstwitter Found video: quality={get_quality(url)}, url={url[:80]}...")
                
                video_urls.sort(key=get_quality, reverse=True)
                return video_urls
            else:
                logging.warning("No video download links found in ssstwitter response")
                return []
        else:
            logging.error(f"Ssstwitter POST request failed: {response.status_code}")
            return []
            
    except Exception as e:
        logging.error(f"Ssstwitter scraping error: {e}")
        return []


def get_twitter_video_url(tweet_url: str) -> list:
    """
    Orchestrator to get direct video URLs from Twitter.
    Tries TVD first, then ssstwitter as fallback.
    """
    # 1. Try TwitterVideoDownloader.com (Primary)
    urls = get_tvd_video_urls(tweet_url)
    if urls:
        logging.info(f"Using TwitterVideoDownloader.com - Found {len(urls)} videos")
        return urls
        
    # 2. Try ssstwitter.com (Fallback)
    logging.info("TVD failed or no links, trying ssstwitter.com...")
    urls = get_ssstwitter_urls(tweet_url)
    if urls:
        logging.info(f"Using ssstwitter.com - Found {len(urls)} videos")
        return urls
        
    return []


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
