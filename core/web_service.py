import aiohttp
import logging
import re
from typing import Optional
from bs4 import BeautifulSoup
from blogi.core.config import logger
from contextlib import asynccontextmanager

class WebService:
    def __init__(self):
        """Initialize the web service."""
        self._session = None

    @asynccontextmanager
    async def get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        try:
            yield self._session
        finally:
            if self._session and not self._session.closed:
                await self._session.close()

    async def get(self, url: str) -> Optional[str]:
        """Make a GET request to the specified URL.
        Args:
            url (str): The URL to request
        Returns:
            Optional[str]: The response text or None if request fails
        """
        async with self.get_session() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.error(f"HTTP error {response.status} for URL: {url}")
                    return None
            except Exception as e:
                logger.error(f"Error fetching URL {url}: {str(e)}")
                return None

    async def fetch_webpage_content(self, url: str) -> Optional[str]:
        """Fetch and extract main content from a webpage."""
        async with self.get_session() as session:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Clean up the HTML
                        for element in soup(["script", "style", "nav", "header", "footer"]):
                            element.decompose()
                        
                        # Extract main content
                        main_content = (
                            soup.find('main') or 
                            soup.find('article') or 
                            soup.find('div', class_=re.compile(r'content|article|post'))
                        )
                        
                        text = (main_content or soup).get_text(separator=' ', strip=True)
                        return re.sub(r'\s+', ' ', text)[:10000]
            except Exception as e:
                logger.error(f"Error fetching webpage {url}: {str(e)}")
                return None 