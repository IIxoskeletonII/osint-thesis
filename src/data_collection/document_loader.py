"""Utility functions for loading documents from various sources."""

from typing import Dict, Any, List, Union, Optional

from src.data_collection.loaders.loader_factory import LoaderFactory
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

def load_document(source_path: str, source_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Load a document from the specified source.
    
    Args:
        source_path: Path or URL to the document
        source_name: Optional name for the source
        **kwargs: Additional source-specific parameters
        
    Returns:
        Dictionary containing the document content and metadata
    """
    loader = LoaderFactory.get_loader(source_path, source_name)
    return loader.load(source_path, **kwargs)

def load_documents(source_paths: List[str], source_names: Optional[List[str]] = None, **kwargs) -> List[Dict[str, Any]]:
    """
    Load multiple documents from the specified sources.
    
    Args:
        source_paths: List of paths or URLs to the documents
        source_names: Optional list of names for the sources
        **kwargs: Additional source-specific parameters
        
    Returns:
        List of dictionaries containing the document contents and metadata
    """
    documents = []
    
    for i, source_path in enumerate(source_paths):
        source_name = None
        if source_names and i < len(source_names):
            source_name = source_names[i]
            
        try:
            document = load_document(source_path, source_name, **kwargs)
            documents.append(document)
            logger.info(f"Successfully loaded document from {source_path}")
        except Exception as e:
            logger.error(f"Failed to load document from {source_path}: {str(e)}")
            # Continue loading other documents even if one fails
    
    return documents