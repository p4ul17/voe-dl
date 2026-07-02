from voe_dl.bait import is_bait_source


def find_sources(soup, html_text, url):
    """Method 3: Look for data attributes in video tags."""
    source_json = None
    video_tags = soup.find_all("video")
    for video in video_tags:
        src = video.get("src")
        if src:
            if is_bait_source(src):
                print(f"[!] Ignoring bait source: {src}")
                continue
            print(f"[+] Found direct video source: {src}")
            source_json = {"mp4": src}
            break

        # Check for source tags inside video
        source_tags = video.find_all("source")
        if source_tags:
            for source_tag in source_tags:
                src = source_tag.get("src")
                if src:
                    if is_bait_source(src):
                        print(f"[!] Ignoring bait source: {src}")
                        continue
                    type_attr = source_tag.get("type", "")
                    if "mp4" in type_attr:
                        source_json = {"mp4": src}
                    elif "m3u8" in type_attr or "hls" in type_attr:
                        source_json = {"hls": src}
                    else:
                        source_json = {"mp4": src}  # Default to mp4
                    print(f"[+] Found video source from source tag: {src}")
                    break

        if source_json:
            break
    return source_json
