"""Base document loader class for OSINT data sources."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional


class BaseLoader(ABC):
    """Abstract base class for all document loaders."""
    
    def __init__(self, source_name: str):
        """
        Initialize the base loader.
        
        Args:
            source_name: Identifier for the source being loaded
        """
        self.source_name = source_name
        self.logger = logging.getLogger(f"{__name__}.{source_name}")
    
    @abstractmethod
    def load(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """
        Load a document from the specified source.
        
        Args:
            source_path: Path or URL to the document
            **kwargs: Additional source-specific parameters
            
        Returns:
            Dictionary containing the document content and metadata
        """
        pass
    
    def _create_metadata(self, source_path: str, additional_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create standard metadata for loaded documents.
        
        Args:
            source_path: Path or URL to the document
            additional_metadata: Any additional metadata to include
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            "source_name": self.source_name,
            "source_path": source_path,
            "collection_date": datetime.now().isoformat(),
            "source_type": self._get_source_type()
        }
        
        if additional_metadata:
            metadata.update(additional_metadata)
            
        return metadata
    
    @abstractmethod
    def _get_source_type(self) -> str:
        """
        Get the type of source this loader handles.
        
        Returns:
            String identifying the source type
        """
        pass