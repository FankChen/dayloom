from urllib.parse import urlsplit


def allowed_page(url, origins):
    parsed = urlsplit(str(url))
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return (
        parsed.scheme == "https"
        and not parsed.username
        and not parsed.password
        and origin in origins
    )
