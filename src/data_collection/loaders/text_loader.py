"""Text document loader for OSINT data sources."""

import os
import logging
from typing import Dict, Any, Optional

# Use direct relative import
from .base_loader import BaseLoader

logger = logging.getLogger(__name__)

class TextLoader(BaseLoader):
    """Loader for text documents."""
    
    def __init__(self, source_name: str = "text_document"):
        """
        Initialize the text loader.
        
        Args:
            source_name: Identifier for the source being loaded
        """
        super().__init__(source_name)
    
    def load(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """
        Load a text document from the specified path.
        
        Args:
            source_path: Path to the text file
            **kwargs: Additional parameters:
                - encoding: The character encoding to use (default: utf-8)
                
        Returns:
            Dictionary containing the document content and metadata
        """
        logger.info(f"Loading text document from {source_path}")
        
        if not os.path.exists(source_path):
            logger.error(f"Text file not found: {source_path}")
            raise FileNotFoundError(f"Text file not found: {source_path}")
        
        encoding = kwargs.get('encoding', 'utf-8')
        
        try:
            with open(source_path, 'r', encoding=encoding) as file:
                content = file.read()
                
            # Extract metadata
            additional_metadata = {
                "title": os.path.basename(source_path),
                "file_size": os.path.getsize(source_path),
                "encoding": encoding
            }
            
            return {
                "content": content,
                "metadata": self._create_metadata(source_path, additional_metadata)
            }
                
        except Exception as e:
            logger.error(f"Error loading text file {source_path}: {str(e)}")
            raise
    
    def _get_source_type(self) -> str:
        """Get the source type."""
        return "text"