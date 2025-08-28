import logging
import pyshorteners
import requests
from config import SHORTENER_API_KEY

logger = logging.getLogger(__name__)

class URLShortener:
    """Service to shorten URLs using various URL shortening services"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or SHORTENER_API_KEY
        self.shortener = pyshorteners.Shortener()
    
    def shorten_url(self, url, service='tinyurl'):
        """
        Shorten a URL using the specified service
        
        Args:
            url (str): The URL to shorten
            service (str): The shortening service to use (tinyurl, bitly, etc.)
            
        Returns:
            str: The shortened URL
        """
        logger.info(f"Shortening URL: {url} using {service}")
        
        try:
            if service == 'tinyurl':
                short_url = self.shortener.tinyurl.short(url)
            elif service == 'bitly':
                if not self.api_key:
                    raise ValueError("Bitly API key is required")
                bitly_shortener = pyshorteners.Shortener(api_key=self.api_key)
                short_url = bitly_shortener.bitly.short(url)
            elif service == 'chilpit':
                short_url = self.shortener.chilpit.short(url)
            elif service == 'clckru':
                short_url = self.shortener.clckru.short(url)
            elif service == 'dagd':
                short_url = self.shortener.dagd.short(url)
            elif service == 'isgd':
                short_url = self.shortener.isgd.short(url)
            elif service == 'osdb':
                short_url = self.shortener.osdb.short(url)
            else:
                # Default to TinyURL if service not recognized
                short_url = self.shortener.tinyurl.short(url)
            
            logger.info(f"URL shortened: {short_url}")
            return short_url
            
        except Exception as e:
            logger.error(f"Error shortening URL: {str(e)}")
            # Fallback to TinyURL if the specified service fails
            if service != 'tinyurl':
                logger.info(f"Falling back to TinyURL")
                return self.shorten_url(url, 'tinyurl')
            raise
    
    def shorten_multiple(self, urls, service='tinyurl'):
        """
        Shorten multiple URLs using the specified service
        
        Args:
            urls (list): List of URLs to shorten
            service (str): The shortening service to use
            
        Returns:
            dict: Dictionary mapping original URLs to shortened URLs
        """
        logger.info(f"Shortening {len(urls)} URLs using {service}")
        
        result = {}
        for url in urls:
            try:
                result[url] = self.shorten_url(url, service)
            except Exception as e:
                logger.error(f"Error shortening URL {url}: {str(e)}")
                result[url] = url  # Use original URL if shortening fails
        
        return result 