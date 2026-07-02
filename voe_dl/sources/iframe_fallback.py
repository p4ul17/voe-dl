from urllib.parse import urljoin, urlparse


def find_iframe_url(soup, url):
    """If no source was found, look for an iframe that might contain the video.

    Returns an absolute URL to recurse into via download(), or None.
    """
    iframes = soup.find_all("iframe")
    if iframes:
        for iframe in iframes:
            iframe_src = iframe.get("src")
            if iframe_src:
                if iframe_src.startswith("//"):
                    iframe_src = "https:" + iframe_src
                elif not iframe_src.startswith(("http://", "https://")):
                    # Handle relative URLs
                    parsed_url = urlparse(url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    iframe_src = base_url + iframe_src if iframe_src.startswith(
                        "/") else base_url + "/" + iframe_src

                iframe_src = urljoin(url, iframe_src)
                return iframe_src
    return None
