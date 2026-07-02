from urllib.parse import urlparse

BAIT_FILENAMES = [
    "BigBuckBunny",
    "Big_Buck_Bunny_1080_10s_5MB",
    "bbb.mp4",
    # Add more bait filenames as needed
]

BAIT_DOMAINS = [
    "test-videos.co.uk",
    "sample-videos.com",
    "commondatastorage.googleapis.com",
    # Add more bait domains as needed
]


def is_bait_source(source: str) -> bool:
    """Return True if *source* looks like a known test/bait video."""
    if any(fn.lower() in source.lower() for fn in BAIT_FILENAMES):
        return True
    parsed = urlparse(source)
    if any(dom in parsed.netloc for dom in BAIT_DOMAINS):
        return True
    return False
