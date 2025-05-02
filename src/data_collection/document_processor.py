"""Utility functions for processing documents."""

import logging
from typing import Dict, Any, List, Union, Optional

from src.data_collection.processors.processor_factory import ProcessorFactory, ProcessorPipeline

logger = logging.getLogger(__name__)

def process_document(document: Dict[str, Any], 
                    processor_configs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Process a document using specified processors.
    
    Args:
        document: Document to process
        processor_configs: List of processor configurations
            If None, default processors will be used
            
    Returns:
        Processed document
    """
    # Use default processor configuration if none provided
    if processor_configs is None:
        processor_configs = [
            {'type': 'text', 'params': {'normalize_whitespace': True}},
            {'type': 'security', 'params': {}}
        ]
        
    # Create and run the processor pipeline
    pipeline = ProcessorFactory.create_pipeline(processor_configs)
    return pipeline.process(document)

def process_documents(documents: List[Dict[str, Any]], 
                     processor_configs: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Process multiple documents using specified processors.
    
    Args:
        documents: List of documents to process
        processor_configs: List of processor configurations
            If None, default processors will be used
            
    Returns:
        List of processed documents
    """
    processed_documents = []
    
    for document in documents:
        try:
            processed_document = process_document(document, processor_configs)
            processed_documents.append(processed_document)
        except Exception as e:
            logger.error(f"Failed to process document: {str(e)}")
            # Add the original document to maintain count
            processed_documents.append(document)
    
    return processed_documents