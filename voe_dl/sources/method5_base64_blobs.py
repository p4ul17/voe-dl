import base64
import re


def find_sources(soup, html_text, url):
    """Method 5: Look for base64 encoded sources."""
    source_json = None
    base64_pattern = r'base64[,:]([A-Za-z0-9+/=]+)'
    base64_matches = re.findall(base64_pattern, html_text)
    for match in base64_matches:
        try:
            decoded = base64.b64decode(match).decode('utf-8')
            if '.mp4' in decoded:
                source_json = {"mp4": decoded}
                print(f"[+] Found base64 encoded MP4 URL")
                break
            elif '.m3u8' in decoded:
                source_json = {"hls": decoded}
                print(f"[+] Found base64 encoded HLS URL")
                break
        except:
            continue
    return source_json
