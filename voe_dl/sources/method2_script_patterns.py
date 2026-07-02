import json


def find_sources(soup, html_text, url):
    """Method 2: Look for script tags with sources."""
    source_json = None
    scripts = soup.find_all("script")
    for script in scripts:
        if not script.string:
            continue

        # Look for different patterns
        patterns = [
            "var sources",
            "sources =",
            "sources:",
            "\"sources\":",
            "'sources':"
        ]

        for pattern in patterns:
            if pattern in script.string:
                try:
                    # Extract JSON-like structure
                    script_text = script.string

                    # Find the start of the sources object
                    start_idx = script_text.find(pattern)
                    if start_idx == -1:
                        continue

                    # Find the opening brace
                    brace_idx = script_text.find("{", start_idx)
                    if brace_idx == -1:
                        continue

                    # Count braces to find the matching closing brace
                    brace_count = 1
                    end_idx = brace_idx + 1

                    while brace_count > 0 and end_idx < len(script_text):
                        if script_text[end_idx] == "{":
                            brace_count += 1
                        elif script_text[end_idx] == "}":
                            brace_count -= 1
                        end_idx += 1

                    if brace_count == 0:
                        json_str = script_text[brace_idx:end_idx]
                        # Clean up the JSON string
                        json_str = json_str.replace("'", "\"")

                        # Try to parse the JSON
                        try:
                            source_json = json.loads(json_str)
                            print(f"[+] Found sources using pattern: {pattern}")
                            break
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    print(f"[!] Error extracting sources from script: {e}")

        if source_json:
            break
    return source_json
