"""Base processor class for OSINT data."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseProcessor(ABC):
    """Abstract base class for all data processors."""
    
    def __init__(self, processor_name: str):
        """
        Initialize the base processor.
        
        Args:
            processor_name: Identifier for the processor
        """
        self.processor_name = processor_name
        self.logger = logging.getLogger(f"{__name__}.{processor_name}")
    
    @abstractmethod
    def process(self, document: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Process a document.
        
        Args:
            document: Dictionary containing document content and metadata
            **kwargs: Additional processor-specific parameters
            
        Returns:
            Processed document
        """
        pass
    
    def _update_metadata(self, metadata: Dict[str, Any], additional_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update document metadata with processor information.
        
        Args:
            metadata: Original document metadata
            additional_metadata: Any additional metadata to include
            
        Returns:
            Updated metadata
        """
        updated_metadata = metadata.copy()
        
        # Add processor information
        if "processing_history" not in updated_metadata:
            updated_metadata["processing_history"] = []
            
        updated_metadata["processing_history"].append(self.processor_name)
        
        # Add any additional metadata
        if additional_metadata:
            updated_metadata.update(additional_metadata)
            
        return updated_metadata