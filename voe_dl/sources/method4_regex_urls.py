import re

from voe_dl.bait import is_bait_source


def find_sources(soup, html_text, url):
    """Method 4: Look for m3u8 or mp4 URLs in the page."""
    source_json = None
    print("[*] Searching for direct media URLs in page...")
    # Look for m3u8 URLs
    m3u8_pattern = r'(https?://[^"\']+\.m3u8[^"\'\s]*)'
    m3u8_matches = re.findall(m3u8_pattern, html_text)
    if m3u8_matches:
        if is_bait_source(m3u8_matches[0]):
            print(f"[!] Ignoring bait source: {m3u8_matches[0]}")
        else:
            source_json = {"hls": m3u8_matches[0]}
            print(f"[+] Found HLS URL: {m3u8_matches[0]}")

    # Look for mp4 URLs
    if not source_json:
        mp4_pattern = r'(https?://[^"\']+\.mp4[^"\'\s]*)'
        mp4_matches = re.findall(mp4_pattern, html_text)
        if mp4_matches:
            if is_bait_source(mp4_matches[0]):
                print(f"[!] Ignoring bait source: {mp4_matches[0]}")
            else:
                source_json = {"mp4": mp4_matches[0]}
                print(f"[+] Found MP4 URL: {mp4_matches[0]}")
    return source_json
