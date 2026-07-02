import re


def extract_episode_tag(url_or_line: str, index: int = 1) -> str:
    match = re.search(r'(S\d{1,2}E\d{1,2})', url_or_line, re.IGNORECASE)
    return match.group(1).upper() if match else f"S01E{index:02d}"


def generate_custom_filename(base: str, episode_tag: str, ext: str = ".mp4") -> str:
    safe_base = re.sub(r'[\\/*?:"<>|]', "_", base)
    return f"{safe_base}_{episode_tag}{ext}"
