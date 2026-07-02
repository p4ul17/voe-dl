import base64
import json
import re

from voe_dl.decoding import clean_base64


def find_sources(soup, html_text, url):
    """Method 6: Look for a168c encoded sources."""
    source_json = None
    print("[*] Searching for a168c encoded sources...")

    # Robust pattern to capture long base64 string inside script tags
    a168c_script_pattern = r"a168c\s*=\s*'([^']+)'"
    match = re.search(a168c_script_pattern, html_text, re.DOTALL)

    if match:
        raw_base64 = match.group(1)
        try:
            cleaned = clean_base64(raw_base64)
            decoded = base64.b64decode(cleaned).decode('utf-8')[::-1]

            # Optional: Try parsing full JSON if applicable
            try:
                parsed = json.loads(decoded)

                if 'direct_access_url' in parsed:
                    source_json = {"mp4": parsed['direct_access_url']}
                    print("[+] Found direct .mp4 URL in JSON.")
                elif 'source' in parsed:
                    source_json = {"hls": parsed['source']}
                    print("[+] Found fallback .m3u8 URL in JSON.")
            except json.JSONDecodeError:
                print("[-] Decoded string is not valid JSON. Trying fallback regex search...")

                # If it's not JSON, fallback to pattern search
                mp4_match = re.search(r'(https?://[^\s"]+\.mp4[^\s"]*)', decoded)
                m3u8_match = re.search(r'(https?://[^\s"]+\.m3u8[^\s"]*)', decoded)

                if mp4_match:
                    source_json = {"mp4": mp4_match.group(1)}
                    print("[+] Found base64 encoded MP4 URL.")
                elif m3u8_match:
                    source_json = {"hls": m3u8_match.group(1)}
                    print("[+] Found base64 encoded HLS (m3u8) URL.")
        except Exception as e:
            print(f"[!] Failed to decode a168c string: {e}")
    return source_json
