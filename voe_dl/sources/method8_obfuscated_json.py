import re

from voe_dl.decoding import deobfuscate_embedded_json


def find_sources(soup, html_text, url):
    """Method 8: Obfuscated JSON in <script type="application/json"> tags."""
    source_json = None
    print("[*] Searching for obfuscated JSON sources…")
    app_json_scripts = soup.find_all("script", attrs={"type": "application/json"})
    for js in app_json_scripts:
        if not js.string:
            continue
        candidate = js.string.strip()
        result = deobfuscate_embedded_json(candidate)
        if result is None:
            continue
        try:
            if isinstance(result, dict):
                if 'direct_access_url' in result:
                    source_json = {"mp4": result['direct_access_url']}
                    print("[+] Found direct .mp4 URL in obfuscated JSON")
                elif 'source' in result:
                    source_json = {"hls": result['source']}
                    print("[+] Found .m3u8 URL in obfuscated JSON")
                elif any(k in result for k in ("mp4", "hls")):
                    source_json = result
                    print("[+] Found media URL in obfuscated JSON")
            elif isinstance(result, str):
                mp4_m = re.search(r'(https?://[^\s"]+\.mp4[^\s"]*)', result)
                m3u8_m = re.search(r'(https?://[^\s"]+\.m3u8[^\s"]*)', result)
                if mp4_m:
                    source_json = {"mp4": mp4_m.group(0)}
                elif m3u8_m:
                    source_json = {"hls": m3u8_m.group(0)}
                if source_json:
                    print("[+] Extracted media link from obfuscated JSON string")
        except Exception as e:
            print(f"[!] Error parsing obfuscated JSON result: {e}")
        if source_json:
            break
    return source_json
