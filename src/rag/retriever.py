# src/rag/retriever.py

"""
Retriever module for the OSINT RAG system.
Handles fetching relevant documents from the knowledge base based on user queries.
"""

import logging
import os
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BasicRetriever:
    """
    Basic retriever that fetches relevant documents from the knowledge base.
    """
    
    def __init__(self, knowledge_base, top_k: int = 5):
        """
        Initialize the retriever with a knowledge base.
        
        Args:
            knowledge_base: The knowledge base instance to retrieve documents from
            top_k: Number of documents to retrieve
        """
        self.knowledge_base = knowledge_base
        self.top_k = top_k
        logger.info(f"Initialized BasicRetriever with top_k={top_k}")
    
    def retrieve(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from the knowledge base based on the query.
        
        Args:
            query: The search query
            filters: Optional filters to apply to the search (e.g., source_type)
            
        Returns:
            List of retrieved documents with similarity scores
        """
        logger.info(f"Retrieving documents for query: '{query}'")
        
        # Perform search using the knowledge base
        search_results = self.knowledge_base.search(query, limit=self.top_k)
        
        # Apply filters if provided
        if filters and search_results:
            filtered_results = []
            for result in search_results:
                if self._matches_filters(result, filters):
                    filtered_results.append(result)
            search_results = filtered_results
        
        logger.info(f"Retrieved {len(search_results)} documents")
        return search_results
    
    def _matches_filters(self, document: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if a document matches the provided filters.
        
        Args:
            document: The document to check
            filters: Filters to apply
            
        Returns:
            True if the document matches the filters, False otherwise
        """
        for key, value in filters.items():
            # Handle filtering based on document structure
            if 'document' in document and 'metadata' in document['document']:
                if key in document['document']['metadata']:
                    if document['document']['metadata'][key] != value:
                        return False
            # Handle direct metadata in results (different structure)
            elif 'metadata' in document:
                if key in document['metadata']:
                    if document['metadata'][key] != value:
                        return False
            else:
                return False
        return True