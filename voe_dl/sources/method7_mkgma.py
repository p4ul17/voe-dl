import base64
import json
import re

from voe_dl.decoding import _rot13, _shift_chars


def find_sources(soup, html_text, url):
    """Method 7: Look for MKGMa encoded sources.

    https://github.com/p4ul17/voe-dl/issues/33#issuecomment-2807006973
    """
    source_json = None
    print("[*] Searching for MKGMa sources...")

    MKGMa_pattern = r'MKGMa="(.*?)"'
    match = re.search(MKGMa_pattern, html_text, re.DOTALL)

    if match:
        raw_MKGMa = match.group(1)

        try:
            step1 = _rot13(raw_MKGMa)
            step2 = step1.replace('_', '')
            step3 = base64.b64decode(step2).decode('utf-8')
            step4 = _shift_chars(step3, 3)
            step5 = step4[::-1]

            decoded = base64.b64decode(step5).decode('utf-8')

            try:
                parsed_json = json.loads(decoded)

                if 'direct_access_url' in parsed_json:
                    source_json = {"mp4": parsed_json['direct_access_url']}
                    print("[+] Found direct .mp4 URL in JSON.")
                elif 'source' in parsed_json:
                    source_json = {"hls": parsed_json['source']}
                    print("[+] Found fallback .m3u8 URL in JSON.")

            except json.JSONDecodeError:
                print("[-] Decoded string is not valid JSON. Attempting fallback regex search...")

                mp4_match = re.search(r'(https?://[^\s"]+\.mp4[^\s"]*)', decoded)
                m3u8_match = re.search(r'(https?://[^\s"]+\.m3u8[^\s"]*)', decoded)

                if mp4_match:
                    source_json = {"mp4": mp4_match.group(1)}
                    print("[+] Found base64 encoded MP4 URL.")
                elif m3u8_match:
                    source_json = {"hls": m3u8_match.group(1)}
                    print("[+] Found base64 encoded HLS (m3u8) URL.")

        except Exception as e:
            print(f"[-] Error while decoding MKGMa string: {e}")
    return source_json
