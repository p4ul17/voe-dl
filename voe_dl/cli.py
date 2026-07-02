import argparse
import signal
import sys
import time

from voe_dl.abort import _global_stop_event, delpartfiles, prompt_partial_file_cleanup, signal_handler
from voe_dl.downloader import download, list_dl
from voe_dl.piping import PIPED


def get_version_history():
    return (
        "\nVersion History:\n"
        "- Version v1.9.0 (Modularized codebase: split dl.py into the voe_dl package, one file per source-detection method)\n"
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
    parser.add_argument("--name", help="Base name for output files (used with --numbering or placeholders)")
    parser.add_argument("--numbering", action="store_true", help="Add S01E01-style numbering based on line order")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without downloading")
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Register signal handler once for the entire process
    signal.signal(signal.SIGINT, signal_handler)
    _global_stop_event.clear()

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
