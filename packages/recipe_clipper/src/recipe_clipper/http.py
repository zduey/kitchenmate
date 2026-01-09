"""HTTP client for fetching recipe pages."""

import httpx
from typing import Dict, Optional

from recipe_clipper.exceptions import NetworkError
from recipe_clipper.models import ImmutableBaseModel

DEFAULT_USER_AGENT = "recipe-clipper/0.1.0 (https://github.com/recipe-clipper/recipe-clipper)"
DEFAULT_TIMEOUT = 10


class HttpResponse(ImmutableBaseModel):
    """HTTP response data."""

    content: str
    status_code: int
    url: str


def fetch_url(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    headers: Optional[Dict[str, str]] = None,
) -> HttpResponse:
    """
    Fetch HTML content from a URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        headers: Optional custom headers

    Returns:
        HttpResponse with content, status_code, and final URL (after redirects)

    Raises:
        NetworkError: If the request fails
    """
    if headers is None:
        headers = {}

    # Set default user agent if not provided
    if "User-Agent" not in headers:
        headers["User-Agent"] = DEFAULT_USER_AGENT

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            return HttpResponse(
                content=response.text,
                status_code=response.status_code,
                url=str(response.url),
            )
    except httpx.HTTPStatusError as e:
        raise NetworkError(f"HTTP error {e.response.status_code} while fetching {url}") from e
    except httpx.RequestError as e:
        raise NetworkError(f"Network error while fetching {url}: {e}") from e
    except Exception as e:
        raise NetworkError(f"Unexpected error while fetching {url}: {e}") from e
