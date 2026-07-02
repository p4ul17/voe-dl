import base64
import copy
import concurrent.futures
import os
import random
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL

from voe_dl.abort import DownloadAbortedException, _global_stop_event, delpartfiles, prompt_partial_file_cleanup
from voe_dl.http_client import USER_AGENTS, get_browser_headers, session
from voe_dl.naming import extract_episode_tag, generate_custom_filename
from voe_dl.piping import PIPED, flush_piped_link
from voe_dl.sources import SOURCE_METHODS
from voe_dl.sources.iframe_fallback import find_iframe_url


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

        # Enhanced source detection - try each method in turn until one succeeds
        source_json = None
        for find_sources in SOURCE_METHODS:
            source_json = find_sources(soup, html_page.text, URL)
            if source_json:
                break

        # If we still don't have sources, try to find any iframe that might contain the video
        if not source_json:
            iframe_url = find_iframe_url(soup, URL)
            if iframe_url:
                print(f"[*] Found iframe, following to: {iframe_url}")
                return download(iframe_url, args, stop_event, visited_urls, redirect_depth + 1)

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

                print(f"[*] Downloading MP4 stream: {link}")
                if dry_run:
                    print(f"[Dry Run] Would download: {link} to {name}")
                else:
                    # Progress hook to check for abort
                    def progress_hook(d):
                        if stop_event and stop_event.is_set():
                            raise DownloadAbortedException("Download aborted by user")

                    ydl_opts = {
                        'outtmpl': name,
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

                print(f"[*] Downloading HLS stream: {link}")
                if dry_run:
                    print(f"[Dry Run] Would download: {link} to {name}")
                else:
                    # Progress hook to check for abort
                    def progress_hook(d):
                        if stop_event and stop_event.is_set():
                            raise DownloadAbortedException("Download aborted by user")

                    ydl_opts = {
                        'outtmpl': name,
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
