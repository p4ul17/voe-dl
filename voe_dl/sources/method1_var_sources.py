import json
import re

from voe_dl.bait import is_bait_source


def find_sources(soup, html_text, url):
    """Method 1: Look for "var sources" pattern."""
    source_json = None
    sources_find = soup.find_all(string=re.compile("var sources"))
    if sources_find:
        sources_find = str(sources_find)
        try:
            slice_start = sources_find.index("var sources")
            source = sources_find[slice_start:]
            slice_end = source.index(";")
            source = source[:slice_end]
            source = source.replace("var sources = ", "")
            source = source.replace("\'", "\"")
            source = source.replace("\\n", "")
            source = source.replace("\\", "")

            # Check for "Bait" sources
            if is_bait_source(source):
                print(f"[!] Ignoring bait source: {source}")
                source_json = None
            else:
                # Clean up JSON for parsing
                strToReplace = ","
                replacementStr = ""
                source = replacementStr.join(source.rsplit(strToReplace, 1))
                source_json = json.loads(source)
                print("[+] Found sources using var sources pattern")
        except (ValueError, json.JSONDecodeError) as e:
            print(f"[!] Error parsing sources: {e}")
            source_json = None
    return source_json
