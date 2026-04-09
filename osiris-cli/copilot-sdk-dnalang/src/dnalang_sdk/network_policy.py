"""Network policy for offline NCLM bridge with controlled zenodo access."""

from urllib.parse import urlparse

ALLOWED_HOSTS = {"zenodo.org", "api.zenodo.org"}


def ensure_allowed_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP/S URLs are allowed")

    host = parsed.netloc.lower()
    if host.endswith(":443") or host.endswith(":80"):
        host = host.rsplit(":", 1)[0]

    if host not in ALLOWED_HOSTS:
        raise PermissionError(f"Network access restricted to {ALLOWED_HOSTS}, blocked: {host}")

    return url
