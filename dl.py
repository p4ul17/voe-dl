# coding=utf-8
import copy
import sys, os, glob
import re
import requests
import json
import wget
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
import base64
import concurrent.futures
import threading
import signal
import random
import time
import argparse
from urllib.parse import urlparse, urljoin
from io import StringIO
import pathlib

# When stdout is piped, buffer all print() output and only emit the
# resolved download link at the end (ported from upstream PR #52 by @Czer0xx)
PIPED = not sys.stdout.isatty()
if PIPED:
    sys.stdout_real = sys.stdout
    sys.stdout = StringIO()

# List of common user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Global stop event for handling Ctrl+C across all threads
_global_stop_event = threading.Event()

class DownloadAbortedException(Exception):
    """Raised when a download is aborted by user (Ctrl+C)"""
    pass

def signal_handler(signum, frame):
    """Handle Ctrl+C signal"""
    print("\n[!] Ctrl+C detected - Aborting all downloads...")
    _global_stop_event.set()
    # Don't call sys.exit() here, let the main thread handle cleanup

# Create a session that persists across requests
session = requests.Session()

def get_browser_headers(url=None):
    """Generate realistic browser headers with optional referer based on URL"""
    parsed_url = urlparse(url) if url else None
    referer = f"{parsed_url.scheme}://{parsed_url.netloc}/" if parsed_url else ""

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none" if not referer else "same-origin",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Priority": "u=1"
    }

    if referer:
        headers["Referer"] = referer

    return headers


# Method-8 dedicated helpers (obfuscated JSON inside <script type="application/json">) | @Domkeykong
def _rot13(text: str) -> str:
    """Apply ROT13 cipher (letters only)."""
    out = []
    for ch in text:
        o = ord(ch)
        if 65 <= o <= 90:
            out.append(chr(((o - 65 + 13) % 26) + 65))
        elif 97 <= o <= 122:
            out.append(chr(((o - 97 + 13) % 26) + 97))
        else:
            out.append(ch)
    return ''.join(out)


def _replace_patterns(txt: str) -> str:
    """Strip marker substrings used as obfuscation separators."""
    for pat in ['@$', '^^', '~@', '%?', '*~', '!!', '#&']:
        txt = txt.replace(pat, '')
    return txt


def _shift_chars(text: str, shift: int) -> str:
    """Shift character code-points by *-shift* (decode)."""
    return ''.join(chr(ord(c) - shift) for c in text)


def _safe_b64_decode(s: str) -> str:
    """Base64 decode with safe padding and utf-8 fallback."""
    pad = len(s) % 4
    if pad:
        s += '=' * (4 - pad)
    return base64.b64decode(s).decode('utf-8', errors='replace')


def deobfuscate_embedded_json(raw_json: str):
    """Return a dict or str extracted from the obfuscated JSON array found in <script type="application/json">."""
    try:
        arr = json.loads(raw_json)
        if not (isinstance(arr, list) and arr and isinstance(arr[0], str)):
            return None
        obf = arr[0]
    except json.JSONDecodeError:
        return None

    try:
        step1 = _rot13(obf)
        step2 = _replace_patterns(step1)
        step3 = _safe_b64_decode(step2)
        step4 = _shift_chars(step3, 3)
        step5 = step4[::-1]
        step6 = _safe_b64_decode(step5)
        try:
            return json.loads(step6)  # ideally a dict with direct_access_url / source
        except json.JSONDecodeError:
            return step6  # return plain string for fallback regex search
    except Exception:
        return None

def extract_episode_tag(url_or_line: str, index: int = 1) -> str:
    match = re.search(r'(S\d{1,2}E\d{1,2})', url_or_line, re.IGNORECASE)
    return match.group(1).upper() if match else f"S01E{index:02d}"

def generate_custom_filename(base: str, episode_tag: str, ext: str = ".mp4") -> str:
    safe_base = re.sub(r'[\\/*?:"<>|]', "_", base)
    return f"{safe_base}_{episode_tag}{ext}"

def prompt_partial_file_cleanup():
    """Prompt user to keep or delete partial download files."""
    print("\n[?] What would you like to do with partial downloads?")
    print("  [K]eep - Keep .part files to resume later")
    print("  [D]elete - Remove all .part files and start fresh next time")
    
    try:
        choice = input("Your choice (K/D): ").strip().upper()
        if choice == 'D':
            print("[*] Cleaning up temporary files...")
            delpartfiles()
            print("[*] All .part files removed.")
        elif choice == 'K':
            print("[*] Keeping .part files for resume.")
        else:
            print("[*] Invalid choice, keeping .part files by default.")
    except (EOFError, KeyboardInterrupt):
        print("\n[*] Keeping .part files by default.")

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Multi-threaded downloader for video sources with advanced detection methods.",
        epilog=get_version_history(),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("target", help="URL or path to .txt file")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--url", dest="is_url", action="store_true", help="Treat target as single URL")
    group.add_argument("-l", "--list", dest="is_list", action="store_true", help="Treat target as list file")
    parser.add_argument("-w", "--workers", type=int, default=4, help="Parallel downloads for -l (default: 4)")
    parser.add_argument("-p", "--proxy", type=str, dest="proxy", help="Specify a proxy url to use, currently only accepting http:// and https:// urls.")
    parser.add_argument("--name", help="Base name for output files (used with --numbering or placeholders)")
    parser.add_argument("-d", "--directoy", type=pathlib.Path, dest="output_dir", default=".", help="Specify the output directory")
    parser.add_argument("--numbering", action="store_true", help="Add S01E01-style numbering based on line order")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without downloading") 
    return parser.parse_args()

def main():  
    args = parse_arguments()
    
    # Register signal handler once for the entire process
    signal.signal(signal.SIGINT, signal_handler)
    _global_stop_event.clear()
    
    # validate output directory
    if not os.path.isdir(args.output_dir):
      print(f"The output directory \"{args.output_dir}\" is not a valid folder.") # tell the user about the invalid output directory
      quit()
    
    # assign proxy to requests session
    if args.proxy:
        # set proxy_url for the requests session
        if args.proxy.startswith("http://"):
            session.proxies = {
                "http": args.proxy,
            }
        elif args.proxy.startswith("https://"):
            session.proxies = {
                "https": args.proxy,
            }
        else:
            print("Proxy url is invalid. Use -h for Help") # advise the user that the proxy url is invalid
            quit()

    if args.is_list:
        list_dl(args.target, args)
    else:
        print("[*] Press Ctrl+C to abort download")
        try:
            download(args.target, args, _global_stop_event)
        except KeyboardInterrupt:
            print("\n[!] KeyboardInterrupt - Aborting download...")
            _global_stop_event.set()
        finally:
            if _global_stop_event.is_set():
                time.sleep(0.5)
                print("[*] Abort complete.")
                
                # Flush output streams to avoid interleaved output
                sys.stdout.flush()
                sys.stderr.flush()
                
                # Ask user what to do with partial downloads
                prompt_partial_file_cleanup()
            else:
                # Normal completion - clean up
                if not PIPED:
                    print("[*] Cleaning up temporary files...")
                delpartfiles()

def get_version_history():
    return (
        "\nVersion History:\n"
        "- Version v1.8.3 (Fixed a crash in --output-dir validation when the given path doesn't exist)\n"
        "- Version v1.8.2 (Added -p/--proxy and -d/--output-dir support, ported from @BlockyBlockling; migrated project setup to uv)\n"
        "- Version v1.8.1 (Piped output: print only the resolved link when stdout is piped, ported from @Czer0xx)\n"
        "- Version v1.8.0 (CLI improvements, custom filename generation, episode tagging, dry-run mode)\n"
        "- Version v1.7.1 (Improved bait detection)\n"
        "- Version v1.7.0 (Method 8 for source detection by @Domkeykong)\n"
        "- Version v1.6.0 (Method 7 for source detection by @ottobauer)\n"
        "- Version v1.5.1 (Documentation updates: help descriptions, README usage info)\n"
        "- Version v1.5.0 (Improved source detection and bait handling)\n"
        "- Version v1.4.0 (Forked by MPZ-00)\n"
        "- Version v1.3.1 (Forked by HerobrineTV, Fixed issues with finding the Download Links)\n"
        "\nCredits to @NikOverflow, @cuitrlal, @cybersnash, @HerobrineTV, @Czer0xx and @MPZ-00 on GitHub for contributing\n"
    )

def list_dl(doc, args):
    """
    Reads lines from the specified doc file and downloads them in parallel.
    Lines starting with '#' and empty lines are ignored.
    Supports graceful abort with Ctrl+C.
    """
    lines = []
    title = args.name

    with open(doc, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if i == 0 and line.startswith("#:"):
                title = line[2:].strip()
                continue
            if not line or line.startswith('#'):
                continue
            lines.append(line)
    
    # If --numbering is used without --name, use "Episode" as default
    if args.numbering and not title:
        title = "Episode"

    print(f"Downloading {len(lines)} files in parallel with {args.workers} threads...")
    print("[*] Press Ctrl+C to abort all downloads")

    future_to_link = {}
    executor = None
    
    try:
        # Execute parallel downloads
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)
        futures = []
        for i, link in enumerate(lines, 1):
            if _global_stop_event.is_set():
                break
                
            episode = extract_episode_tag(link, i) if args.numbering else None
            filename = generate_custom_filename(title, episode) if title and episode else None
            thread_args = copy.copy(args)
            thread_args.name = filename if filename else args.name
            future = executor.submit(download, link, thread_args, _global_stop_event)
            futures.append(future)
            future_to_link[future] = link

        # Poll futures with timeout to allow KeyboardInterrupt
        completed = set()
        total = len(futures)
        success_count = 0
        failed_count = 0
        
        while len(completed) < total and not _global_stop_event.is_set():
            # Use as_completed with very short timeout
            done, not_done = concurrent.futures.wait(
                [f for f in futures if f not in completed],
                timeout=0.1,
                return_when=concurrent.futures.FIRST_COMPLETED
            )
            
            # Process completed futures
            for future in done:
                try:
                    future.result(timeout=0)
                    completed.add(future)
                    success_count += 1
                    print(f"[*] Download {success_count} / {total} completed successfully.")
                    print(f"[*] Link: '{future_to_link[future]}'")
                except concurrent.futures.CancelledError:
                    # Future was cancelled due to abort - this is expected
                    completed.add(future)
                except Exception as e:
                    completed.add(future)
                    failed_count += 1
                    print(f"[!] Error downloading file (failed {failed_count}): {e}")
                    print(f"[!] Link: '{future_to_link[future]}'")
        
        # If abort was triggered, cancel all pending futures
        if _global_stop_event.is_set():
            print("[*] Cancelling pending downloads...")
            for future in futures:
                if future not in completed:
                    future.cancel()
                        
    except KeyboardInterrupt:
        print("\n[!] KeyboardInterrupt - Aborting all downloads...")
        _global_stop_event.set()
    finally:
        # Forcefully shutdown the executor
        if executor:
            if _global_stop_event.is_set():
                print("[*] Shutting down executor...")
                # Cancel pending futures first
                for future in futures:
                    future.cancel()
                # Wait a moment for running threads to notice stop_event
                time.sleep(2)
                # Then shutdown without waiting for stragglers
                executor.shutdown(wait=False, cancel_futures=True)
                print("[*] Abort complete.")
                
                # Flush output streams to avoid interleaved output from threads
                sys.stdout.flush()
                sys.stderr.flush()
                
                # Ask user what to do with partial downloads
                prompt_partial_file_cleanup()
            else:
                # Normal shutdown - wait for completion
                executor.shutdown(wait=True)
                # Clean up after successful completion
                print("[*] Cleaning up temporary files...")
                delpartfiles()


def flush_piped_link(url):
    """Restore the real stdout and write only the resolved link, for piped usage."""
    sys.stdout = sys.stdout_real
    sys.stdout.write(url + "\n")
    sys.stdout.flush()

def flush_and_restore_stdout(url):
    """
    Write url to stdout and flush it. Then restore the original stdout that was replaced with StringIO.
    """
    # Restore stdout
    sys.stdout = sys.stdout_real

    # Flush only the URL to the pipe
    sys.stdout.write(url + "\n")
    sys.stdout.flush()


def download(url, args, stop_event=None, visited_urls=None, redirect_depth=0):
    """
    Download a video from the given URL.
    
    Args:
        url: The URL to download from
        args: Parsed command line arguments
        stop_event: Optional threading.Event() to signal abort
    """
    # Check if abort was requested before starting
    if stop_event and stop_event.is_set():
        print(f"[!] Download aborted before starting: {url}")
        return
    
    URL = str(url)
    if visited_urls is None:
        visited_urls = set()
    if URL in visited_urls:
        print(f"[!] Redirect loop detected, already visited: {URL}")
        return
    if redirect_depth > 10:
        print(f"[!] Too many redirects while resolving: {URL}")
        return
    visited_urls.add(URL)
    custom_name = args.name if hasattr(args, 'name') else None
    dry_run = args.dry_run if hasattr(args, 'dry_run') else False

    # Add a small random delay to mimic human behavior
    for _ in range(10):  # Split sleep into smaller chunks for responsiveness
        if stop_event and stop_event.is_set():
            print(f"[!] Download aborted during initial delay: {url}")
            return
        time.sleep(random.uniform(0.1, 0.3))

    # Get browser-like headers
    headers = get_browser_headers(URL)

    try:
        # Check abort before making request
        if stop_event and stop_event.is_set():
            print(f"[!] Download aborted: {url}")
            return
            
        # Use the session for persistent cookies
        html_page = session.get(URL, headers=headers, timeout=30)
        html_page.raise_for_status()  # Raise exception for 4XX/5XX responses

        # Check abort after request
        if stop_event and stop_event.is_set():
            print(f"[!] Download aborted after page fetch: {url}")
            return

        # Handle cloudflare or other protection
        if html_page.status_code == 403 or "captcha" in html_page.text.lower():
            print(f"[!] Access denied or captcha detected for {URL}. Trying with different headers...")
            # Try again with different headers after a delay
            for _ in range(10):
                if stop_event and stop_event.is_set():
                    print(f"[!] Download aborted during retry delay: {url}")
                    return
                time.sleep(random.uniform(0.3, 0.5))
            headers = get_browser_headers(URL)
            headers["User-Agent"] = random.choice(USER_AGENTS)  # Force different UA
            html_page = session.get(URL, headers=headers, timeout=30)
            html_page.raise_for_status()

        soup = BeautifulSoup(html_page.content, 'html.parser')

        #print(html_page.text)

        redirect_patterns = [
            "window.location.href = '",
            "window.location = '",
            "location.href = '",
            "window.location.replace('",
            "window.location.assign('",
            "window.location=\"",
            "window.location.href=\""
        ]

        # Check for redirects in any script tag
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                for pattern in redirect_patterns:
                    if pattern in script.string:
                        L = len(pattern)
                        i0 = script.string.find(pattern)
                        closing_quote = "'" if pattern.endswith("'") else "\""
                        i1 = script.string.find(closing_quote, i0 + L)
                        if i1 > i0:
                            redirect_url = script.string[i0 + L:i1].strip()
                            redirect_url = urljoin(URL, redirect_url)
                            print(f"[*] Detected redirect to: {redirect_url}")
                            return download(redirect_url, args, stop_event, visited_urls, redirect_depth + 1)

        # Try multiple methods to find the title
        name = None
        for meta_tag in ['og:title', 'twitter:title', 'title']:
            name_find = soup.find('meta', attrs={"property": meta_tag}) or soup.find('meta', attrs={"name": meta_tag})
            if name_find and name_find.get("content"):
                name = name_find["content"]
                break

        # If meta tags fail, try the title tag
        if not name and soup.title and soup.title.string:
            name = soup.title.string

        if name:
            # Clean the filename to avoid issues
            name = re.sub(r'[\\/*?:"<>|]', "_", name)
            name = name.replace(" ", "_")
            print("Name of file: " + name)
        else:
            print("Could not find the name of the file. Using default name.")
            name = URL.split("/")[-1]  # Use the last part of the URL as the default file name
            if not name or name == "":
                name = f"download_{int(time.time())}"
            print("Using default file name: " + name)

        # Enhanced source detection - multiple patterns and approaches
        source_json = None

        # Method 1: Look for "var sources" pattern
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

        # Method 2: Look for script tags with sources
        if not source_json:
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

        # Method 3: Look for data attributes in video tags
        if not source_json:
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

        # Method 4: Look for m3u8 or mp4 URLs in the page
        if not source_json:
            print("[*] Searching for direct media URLs in page...")
            # Look for m3u8 URLs
            m3u8_pattern = r'(https?://[^"\']+\.m3u8[^"\'\s]*)'
            m3u8_matches = re.findall(m3u8_pattern, html_page.text)
            if m3u8_matches:
                if is_bait_source(m3u8_matches[0]):
                    print(f"[!] Ignoring bait source: {m3u8_matches[0]}")
                else:
                    source_json = {"hls": m3u8_matches[0]}
                    print(f"[+] Found HLS URL: {m3u8_matches[0]}")

            # Look for mp4 URLs
            if not source_json:
                mp4_pattern = r'(https?://[^"\']+\.mp4[^"\'\s]*)'
                mp4_matches = re.findall(mp4_pattern, html_page.text)
                if mp4_matches:
                    if is_bait_source(mp4_matches[0]):
                        print(f"[!] Ignoring bait source: {mp4_matches[0]}")
                    else:
                        source_json = {"mp4": mp4_matches[0]}
                        print(f"[+] Found MP4 URL: {mp4_matches[0]}")

        # Method 5: Look for base64 encoded sources
        if not source_json:
            base64_pattern = r'base64[,:]([A-Za-z0-9+/=]+)'
            base64_matches = re.findall(base64_pattern, html_page.text)
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

        # Method 6: Look for a168c encoded sources
        if not source_json:
            print("[*] Searching for a168c encoded sources...")

            # Robust pattern to capture long base64 string inside script tags
            a168c_script_pattern = r"a168c\s*=\s*'([^']+)'"
            match = re.search(a168c_script_pattern, html_page.text, re.DOTALL)

            if match:
                raw_base64 = match.group(1)
                try:
                    cleaned = clean_base64(raw_base64)
                    decoded = base64.b64decode(cleaned).decode('utf-8')[::-1]

                    # Optional: Try parsing full JSON if applicable
                    try:
                        parsed = json.loads(decoded)
                        # print("[+] Decoded JSON:")
                        # print(json.dumps(parsed, indent=4))

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
        
        # Method 7: Look for MKGMa encoded sources
        # https://github.com/p4ul17/voe-dl/issues/33#issuecomment-2807006973
        if not source_json:
            print("[*] Searching for MKGMa sources...")

            MKGMa_pattern = r'MKGMa="(.*?)"'
            match = re.search(MKGMa_pattern, html_page.text, re.DOTALL)

            if match:
                raw_MKGMa = match.group(1)

                def rot13_decode(s: str) -> str:
                    result = []
                    for c in s:
                        if 'A' <= c <= 'Z':
                            result.append(chr((ord(c) - ord('A') + 13) % 26 + ord('A')))
                        elif 'a' <= c <= 'z':
                            result.append(chr((ord(c) - ord('a') + 13) % 26 + ord('a')))
                        else:
                            result.append(c)
                    return ''.join(result)

                def shift_characters(s: str, offset: int) -> str:
                    return ''.join(chr(ord(c) - offset) for c in s)

                try:
                    step1 = rot13_decode(raw_MKGMa)
                    step2 = step1.replace('_', '')
                    step3 = base64.b64decode(step2).decode('utf-8')
                    step4 = shift_characters(step3, 3)
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

        # Method 8: Obfuscated JSON in <script type="application/json"> tags
        if not source_json:
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

        # If we still don't have sources, try to find any iframe that might contain the video
        if not source_json:
            iframes = soup.find_all("iframe")
            if iframes:
                for iframe in iframes:
                    iframe_src = iframe.get("src")
                    if iframe_src:
                        if iframe_src.startswith("//"):
                            iframe_src = "https:" + iframe_src
                        elif not iframe_src.startswith(("http://", "https://")):
                            # Handle relative URLs
                            parsed_url = urlparse(URL)
                            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                            iframe_src = base_url + iframe_src if iframe_src.startswith(
                                "/") else base_url + "/" + iframe_src

                        iframe_src = urljoin(URL, iframe_src)
                        print(f"[*] Found iframe, following to: {iframe_src}")
                        return download(iframe_src, args, stop_event, visited_urls, redirect_depth + 1)

        if not source_json:
            print("[!] Could not find sources in the page. The site structure might have changed.")
            print("[*] Dumping page content for debugging...")
            with open(f"debug_page_{int(time.time())}.html", "w", encoding="utf-8") as f:
                f.write(html_page.text)
            print(f"[*] Page content saved for debugging")
            return

        # Process the found sources
        try:
            if isinstance(source_json, str):
                print(f"[!] source_json is a string. Wrapping it in a dictionary.")
                source_json = {"mp4": source_json}

            if not isinstance(source_json, dict):
                print(f"[!] Unexpected source_json format: {type(source_json)}")
                print(f"[!] source_json content: {source_json}")
                return

            if "mp4" in source_json:
                link = source_json["mp4"]
                # Check if the link is base64 encoded
                if isinstance(link, str) and (link.startswith("eyJ") or re.match(r'^[A-Za-z0-9+/=]+$', link)):
                    try:
                        link = base64.b64decode(link).decode("utf-8")
                        print("[+] Successfully decoded base64 MP4 URL")
                    except Exception as e:
                        print(f"[!] Failed to decode base64: {e}")

                # Ensure the link is a complete URL
                if link.startswith("//"):
                    link = "https:" + link

                basename, ext = os.path.splitext(name)
                if not ext:
                    ext = ".mp4"
                name = f"{basename}_SS{ext}" if not custom_name else f"{custom_name}{ext}"

                if PIPED:
                    flush_piped_link(link)
                    return

                # Check for abort before starting download
                if stop_event and stop_event.is_set():
                    print(f"[!] Download aborted before starting MP4 download: {URL}")
                    return

                # If the output is piped
                if PIPED:
                    flush_and_restore_stdout(link)
                    # Exit the process, so that it does not actually download the file
                    exit()

                print(f"[*] Downloading MP4 stream: {link}")
                if dry_run:
                    print(f"[Dry Run] Would download: {link} to {name}")
                else:
                    # Progress hook to check for abort
                    def progress_hook(d):
                        if stop_event and stop_event.is_set():
                            raise DownloadAbortedException("Download aborted by user")
                    
                    ydl_opts = {
                        'outtmpl': os.path.join(args.output_dir, name),
                        'quiet': False,
                        'no_warnings': False,
                        'http_headers': headers,
                        'progress_hooks': [progress_hook],
                        'proxy': args.proxy,
                    }
                    with YoutubeDL(ydl_opts) as ydl:
                        try:
                            ydl.download([link])
                        except DownloadAbortedException:
                            # Re-raise abort exception to be handled by caller
                            raise
                        except Exception as e:
                            # Check if it was aborted
                            if stop_event and stop_event.is_set():
                                print(f"[!] Download aborted during MP4 download: {URL}")
                                return
                            print(f"[!] YoutubeDL error: {e}")
            elif "hls" in source_json:
                link = source_json["hls"]
                # Check if the link is base64 encoded
                if isinstance(link, str) and (link.startswith("eyJ") or re.match(r'^[A-Za-z0-9+/=]+$', link)):
                    try:
                        link = base64.b64decode(link).decode("utf-8")
                        print("[+] Successfully decoded base64 HLS URL")
                    except Exception as e:
                        print(f"[!] Failed to decode base64: {e}")

                # Ensure the link is a complete URL
                if link.startswith("//"):
                    link = "https:" + link

                basename, ext = os.path.splitext(name)
                if not ext:
                    ext = ".mp4"  # HLS streams are typically downloaded as MP4
                name = f"{basename}_SS{ext}" if not custom_name else f"{custom_name}{ext}"

                if PIPED:
                    flush_piped_link(link)
                    return

                # Check for abort before starting download
                if stop_event and stop_event.is_set():
                    print(f"[!] Download aborted before starting HLS download: {URL}")
                    return

                # If the output is piped
                if PIPED:
                    flush_and_restore_stdout(link)
                    # Exit the process, so that it does not actually download the file
                    exit()

                print(f"[*] Downloading HLS stream: {link}")
                if dry_run:
                    print(f"[Dry Run] Would download: {link} to {name}")
                else:
                    # Progress hook to check for abort
                    def progress_hook(d):
                        if stop_event and stop_event.is_set():
                            raise DownloadAbortedException("Download aborted by user")
                    
                    ydl_opts = {
                        'outtmpl': os.path.join(args.output_dir, name),
                        'quiet': False,
                        'no_warnings': False,
                        'http_headers': headers,
                        'progress_hooks': [progress_hook],
                        'proxy': args.proxy,
                    }
                    with YoutubeDL(ydl_opts) as ydl:
                        try:
                            ydl.download([link])
                        except DownloadAbortedException:
                            # Re-raise abort exception to be handled by caller
                            raise
                        except Exception as e:
                            # Check if it was aborted
                            if stop_event and stop_event.is_set():
                                print(f"[!] Download aborted during HLS download: {URL}")
                                return
                            print(f"[!] YoutubeDL error: {e}")
            else:
                print("[!] Could not find downloadable URL. The site might have changed.")
                print(f"Available keys in source_json: {list(source_json.keys())}")
                for key, value in source_json.items():
                    print(f"{key}: {value}")
        except KeyError as e:
            print(f"[!] KeyError: {e}")
            print("[!] Could not find downloadable URL. The site might have changed.")
            print(f"Available keys in source_json: {list(source_json.keys())}")

    except requests.exceptions.RequestException as e:
        print(f"[!] Request error: {e}")
    except Exception as e:
        print(f"[!] Unexpected error: {e}")

    print("\n")


def download_file(url, filename, referer_url=None):
    """Download file with proper headers and progress tracking"""
    headers = get_browser_headers(referer_url)

    try:
        with session.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))

            with open(os.path.join(args.output_dir, filename), 'wb') as f:
                if total_size == 0:
                    print("[!] Unknown file size. Downloading...")
                    f.write(r.content)
                else:
                    downloaded = 0
                    print(f"[*] File size: {total_size / 1024 / 1024:.2f} MB")
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            done = int(50 * downloaded / total_size)
                            sys.stdout.write(
                                f"\r[{'=' * done}{' ' * (50 - done)}] {downloaded / 1024 / 1024:.2f}/{total_size / 1024 / 1024:.2f} MB")
                            sys.stdout.flush()
            print("\n[+] Download complete!")
    except Exception as e:
        print(f"[!] Error downloading file: {e}")
        # Fall back to wget if our method fails
        print("[*] Falling back to wget...")
        wget.download(url, out=os.path.join(args.output_dir, filename))

def delpartfiles():
    path = os.getcwd()
    for file in glob.iglob(os.path.join(path, '*.part')):
        os.remove(file)

def is_bait_source(source: str) -> bool:
    """Return True if *source* looks like a known test/bait video."""
    bait_filenames = [
        "BigBuckBunny",
        "Big_Buck_Bunny_1080_10s_5MB",
        "bbb.mp4",
        # Add more bait filenames as needed
    ]
    bait_domains = [
        "test-videos.co.uk",
        "sample-videos.com",
        "commondatastorage.googleapis.com",
        # Add more bait domains as needed
    ]
    if any(fn.lower() in source.lower() for fn in bait_filenames):
        return True
    parsed = urlparse(source)
    if any(dom in parsed.netloc for dom in bait_domains):
        return True
    return False

# Function to clean and pad base64 safely
def clean_base64(s):
    try:
        s = s.replace('\\', '')  # remove literal backslashes
        missing_padding = len(s) % 4
        if missing_padding:
            s += '=' * (4 - missing_padding)
        # Validate if the string is valid base64
        base64.b64decode(s, validate=True)
        return s
    except (base64.binascii.Error, ValueError) as e:
        print(f"[!] Invalid base64 string: {e}")
        return None

if __name__ == "__main__":

    main()









