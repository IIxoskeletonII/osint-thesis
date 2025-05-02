"""Factory for creating document loaders based on source type."""

import os
import logging
import mimetypes
from urllib.parse import urlparse
from typing import Dict, Any, Optional

from .base_loader import BaseLoader
from .pdf_loader import PDFLoader
from .text_loader import TextLoader
from .web_loader import WebLoader

logger = logging.getLogger(__name__)

class LoaderFactory:
    """Factory for creating appropriate document loaders."""
    
    @staticmethod
    def get_loader(source_path: str, source_name: Optional[str] = None) -> BaseLoader:
        """
        Get the appropriate loader for the given source path.
        
        Args:
            source_path: Path or URL to the document
            source_name: Optional name for the source
            
        Returns:
            An instance of the appropriate loader
        """
        # Determine if it's a URL or a file path
        parsed_url = urlparse(source_path)
        
        if parsed_url.scheme in ['http', 'https']:
            # It's a web URL
            logger.info(f"Creating web loader for {source_path}")
            return WebLoader(source_name or "web_page")
        
        # It's a file path
        if not os.path.exists(source_path):
            logger.error(f"File not found: {source_path}")
            raise FileNotFoundError(f"File not found: {source_path}")
        
        # Get the file extension
        _, file_extension = os.path.splitext(source_path)
        file_extension = file_extension.lower()
        
        # Determine mime type if extension is not obvious
        if not file_extension:
            mime_type, _ = mimetypes.guess_type(source_path)
            if mime_type:
                if mime_type.startswith('text/'):
                    file_extension = '.txt'
                elif mime_type == 'application/pdf':
                    file_extension = '.pdf'
        
        # Create appropriate loader based on file extension
        if file_extension == '.pdf':
            logger.info(f"Creating PDF loader for {source_path}")
            return PDFLoader(source_name or "pdf_document")
        elif file_extension in ['.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm']:
            logger.info(f"Creating text loader for {source_path}")
            return TextLoader(source_name or "text_document")
        else:
            logger.warning(f"Unrecognized file type for {source_path}, defaulting to text loader")
            return TextLoader(source_name or "unknown_document")