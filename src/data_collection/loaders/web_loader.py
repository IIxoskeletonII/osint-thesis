"""Web page loader for OSINT data sources."""

import re
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Use direct relative import
from .base_loader import BaseLoader

logger = logging.getLogger(__name__)

class WebLoader(BaseLoader):
    """Loader for web pages."""
    
    def __init__(self, source_name: str = "web_page", timeout: int = 30):
        """
        Initialize the web loader.
        
        Args:
            source_name: Identifier for the source being loaded
            timeout: Request timeout in seconds
        """
        super().__init__(source_name)
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    
    def load(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """
        Load content from a web page.
        
        Args:
            source_path: URL of the web page
            **kwargs: Additional parameters:
                - headers: Custom HTTP headers
                - extract_metadata: Whether to extract metadata from HTML (default: True)
                - extract_content_only: Whether to extract main content only (default: False)
                
        Returns:
            Dictionary containing the web page content and metadata
        """
        logger.info(f"Loading web page from {source_path}")
        
        if not self._is_valid_url(source_path):
            logger.error(f"Invalid URL: {source_path}")
            raise ValueError(f"Invalid URL: {source_path}")
        
        custom_headers = kwargs.get('headers', {})
        headers = {**self.headers, **custom_headers}
        extract_metadata = kwargs.get('extract_metadata', True)
        extract_content_only = kwargs.get('extract_content_only', False)
        
        try:
            response = requests.get(source_path, headers=headers, timeout=self.timeout)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract metadata
            additional_metadata = {
                "url": source_path,
                "status_code": response.status_code,
                "content_type": response.headers.get('Content-Type', 'unknown')
            }
            
            if extract_metadata:
                additional_metadata.update(self._extract_html_metadata(soup))
            
            # Extract content
            if extract_content_only:
                content = self._extract_main_content(soup)
            else:
                content = self._clean_html_content(soup)
                
            return {
                "content": content,
                "metadata": self._create_metadata(source_path, additional_metadata)
            }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error loading web page {source_path}: {str(e)}")
            raise
    
    # Rest of the methods stay the same
    def _is_valid_url(self, url: str) -> bool:
        """Check if the URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _extract_html_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract metadata from HTML."""
        metadata = {}
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.text.strip()
        
        # Extract meta tags
        for meta in soup.find_all('meta'):
            # Description
            if meta.get('name') == 'description':
                metadata['description'] = meta.get('content', '')
            
            # Keywords
            elif meta.get('name') == 'keywords':
                metadata['keywords'] = meta.get('content', '')
            
            # Author
            elif meta.get('name') == 'author':
                metadata['author'] = meta.get('content', '')
                
            # OpenGraph metadata
            elif meta.get('property') and meta.get('property').startswith('og:'):
                prop = meta.get('property')[3:]  # Remove 'og:' prefix
                metadata[f'og_{prop}'] = meta.get('content', '')
        
        return metadata
    
    def _clean_html_content(self, soup: BeautifulSoup) -> str:
        """Clean and extract text content from HTML."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'header', 'footer', 'nav']):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from the page, attempting to remove navigation, 
        headers, footers, and other non-content elements.
        """
        # This is a simple heuristic approach that looks for the largest text block
        # More sophisticated approaches could be implemented
        
        # Remove obvious non-content elements
        for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            element.decompose()
        
        # Look for main content containers
        main_content = None
        for tag in ['main', 'article', 'div[role="main"]', '.main-content', '.content', '#content']:
            if '[' in tag:
                # Handle attribute selector
                tag_name, attr = tag.split('[', 1)
                attr = attr.rstrip(']')
                attr_name, attr_value = attr.split('=', 1)
                attr_value = attr_value.strip('"\'')
                elements = soup.find_all(tag_name, {attr_name: attr_value})
            elif '.' in tag and not tag.startswith('.'):
                # Handle tag with class
                tag_name, class_name = tag.split('.')
                elements = soup.find_all(tag_name, class_=class_name)
            elif tag.startswith('.'):
                # Handle class selector
                elements = soup.find_all(class_=tag[1:])
            elif tag.startswith('#'):
                # Handle ID selector
                element = soup.find(id=tag[1:])
                elements = [element] if element else []
            else:
                # Handle simple tag selector
                elements = soup.find_all(tag)
            
            if elements:
                # Choose the element with the most text
                main_content = max(elements, key=lambda el: len(el.get_text()))
                break
        
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            # If no main content container found, use the body
            text = soup.body.get_text(separator=' ', strip=True) if soup.body else soup.get_text(separator=' ', strip=True)
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _get_source_type(self) -> str:
        """Get the source type."""
        return "web"