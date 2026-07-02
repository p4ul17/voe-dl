import glob
import os
import threading

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


def delpartfiles():
    path = os.getcwd()
    for file in glob.iglob(os.path.join(path, '*.part')):
        os.remove(file)
