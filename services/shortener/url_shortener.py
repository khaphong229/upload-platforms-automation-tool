import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class URLShortener:
    """
    Simple URL shortener for APIs like link4m.co.
    Usage:
        shortener = URLShortener()
        short_url = shortener.shorten_url(
            base_url="https://link4m.co/api-shorten/v2?api=YOUR_API_KEY&url=",
            apk_url="https://your-apk-link.com"
        )
    """

    def shorten_url(self, base_url: str, apk_url: str) -> str:
        """
        Shorten an APK URL using the provided base API endpoint.

        Args:
            base_url: The API endpoint up to 'url=' (e.g. 'https://link4m.co/api-shorten/v2?api=KEY&url=')
            apk_url: The APK link to be shortened

        Returns:
            The shortened URL if successful, otherwise returns the original apk_url
        """
        try:
            full_url = f"{base_url}{apk_url}"
            resp = requests.get(full_url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            short = data.get('shortenedUrl')
            if short and short.startswith('http'):
                return short
            return apk_url
        except Exception:
            return apk_url
