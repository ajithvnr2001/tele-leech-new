# copyright 2024 © Xron Trix | https://github.com/Xrontrix10

import subprocess
import json
import os
import logging
from os import path as ospath

async def extract_subtitles(video_file, output_dir):
    """
    Extract all subtitle tracks from a video file using ffmpeg.
    
    Naming:
    - Single: filename_sub_lang.srt
    - Multiple: filename_sub_lang-1.srt, filename_sub_lang-2.srt, etc.
    """
    if not ospath.exists(video_file):
        logging.error(f"File not found: {video_file}")
        return []

    if not ospath.exists(output_dir):
        os.makedirs(output_dir)

    base_name = ospath.splitext(ospath.basename(video_file))[0]
    
    # Analyze streams
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        '-select_streams', 's',
        video_file
    ]

    extracted_files = []
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        streams = data.get('streams', [])

        if not streams:
            logging.info(f"No subtitle streams found in {video_file}")
            return []

        logging.info(f"Found {len(streams)} subtitle stream(s) in {video_file}")

        for idx, stream in enumerate(streams):
            stream_index = stream['index']
            tags = stream.get('tags', {})
            language = tags.get('language', 'und')
            
            # User naming logic:
            # Single: filename_sub_languagecode.srt
            # Multiple: filename_sub_languagecode-1.srt, -2.srt etc.
            if len(streams) == 1:
                output_filename = f"{base_name}_sub_{language}.srt"
            else:
                output_filename = f"{base_name}_sub_{language}-{idx + 1}.srt"
            
            # Clean filename
            output_filename = "".join(c for c in output_filename if c.isalnum() or c in ('.', '-', '_')).strip()
            output_path = ospath.join(output_dir, output_filename)

            # Extract command
            extract_cmd = [
                'ffmpeg',
                '-i', video_file,
                '-map', f'0:{stream_index}',
                '-c:s', 'srt',
                '-y',
                output_path
            ]

            extract_result = subprocess.run(extract_cmd, capture_output=True, text=True)

            if extract_result.returncode == 0:
                if ospath.exists(output_path) and os.path.getsize(output_path) > 0:
                    logging.info(f"Extracted: {output_filename}")
                    extracted_files.append(output_path)
                else:
                    logging.warning(f"Extracted file is empty or missing: {output_filename}")
            else:
                logging.error(f"Failed to extract stream {stream_index}: {extract_result.stderr}")

    except Exception as e:
        logging.error(f"Error during subtitle extraction: {e}")

    return extracted_files
