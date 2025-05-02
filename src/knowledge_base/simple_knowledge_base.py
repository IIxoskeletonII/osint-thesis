"""
Simple Knowledge Base implementation for OSINT thesis project.
This follows the practical approach outlined in the implementation guide,
focusing on demonstrating key concepts without complex dependencies.
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class SimpleKnowledgeBase:
    """
    A straightforward knowledge base implementation that stores documents
    and provides basic search capabilities.
    """
    
    def __init__(self, storage_dir: str):
        """
        Initialize the knowledge base with a storage directory.
        
        Args:
            storage_dir (str): Directory to store knowledge base files
        """
        self.storage_dir = storage_dir
        self.documents_dir = os.path.join(storage_dir, "documents")
        self.index_file = os.path.join(storage_dir, "index.json")
        
        # Create directories if they don't exist
        os.makedirs(self.documents_dir, exist_ok=True)
        
        # Initialize or load the index
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {
                "creation_date": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "document_count": 0,
                "documents": {}
            }
            self._save_index()
            
        logger.info(f"Knowledge base initialized with {len(self.index['documents'])} documents")
    
    def _save_index(self):
        """Save the current index to disk."""
        self.index["last_update"] = datetime.now().isoformat()
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def add_document(self, document: Dict[str, Any], source_type: str, 
                    source_name: str) -> str:
        """
        Add a document to the knowledge base.
        
        Args:
            document (Dict): The document to add (either a content object or a full document)
            source_type (str): Type of source (e.g., 'vulnerability', 'research', 'threat')
            source_name (str): Name of the source
            
        Returns:
            str: Document ID
        """
        # Generate a unique ID
        doc_id = str(uuid.uuid4())
        
        # Create proper document structure
        if "content" in document and "metadata" in document:
            # Document already has proper structure
            structured_doc = document.copy()
            # Update the ID in metadata
            structured_doc["metadata"]["id"] = doc_id
            # Ensure source type and name are set
            structured_doc["metadata"]["source_type"] = source_type
            structured_doc["metadata"]["source_name"] = source_name
            structured_doc["metadata"]["ingestion_date"] = datetime.now().isoformat()
        else:
            # Assume document is the content and create proper structure
            structured_doc = {
                "content": document,
                "metadata": {
                    "id": doc_id,
                    "source_type": source_type,
                    "source_name": source_name,
                    "ingestion_date": datetime.now().isoformat()
                }
            }
        
        # Save document to file
        doc_path = os.path.join(self.documents_dir, f"{doc_id}.json")
        with open(doc_path, 'w') as f:
            json.dump(structured_doc, f, indent=2)
        
        # Update index
        self.index["documents"][doc_id] = {
            "id": doc_id,
            "source_type": source_type,
            "source_name": source_name,
            "ingestion_date": structured_doc["metadata"]["ingestion_date"],
            "path": doc_path
        }
        
        self.index["document_count"] = len(self.index["documents"])
        self._save_index()
        
        logger.info(f"Added document {doc_id} from {source_name} ({source_type})")
        return doc_id
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID.
        
        Args:
            doc_id (str): Document ID
            
        Returns:
            Optional[Dict]: Document content or None if not found
        """
        if doc_id not in self.index["documents"]:
            logger.warning(f"Document {doc_id} not found in knowledge base")
            return None
        
        doc_path = self.index["documents"][doc_id]["path"]
        if not os.path.exists(doc_path):
            logger.error(f"Document file {doc_path} not found on disk")
            return None
        
        with open(doc_path, 'r') as f:
            return json.load(f)
    
    def search(self, query: str, source_type: Optional[str] = None, 
               limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for documents matching the query.
        This implements a simple keyword-based search.
        
        Args:
            query (str): Search query
            source_type (Optional[str]): Filter by source type
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict]: Matching documents with scores
        """
        query = query.lower()
        results = []
        
        # Process each document
        for doc_id, doc_info in self.index["documents"].items():
            # Apply source type filter if specified
            if source_type and doc_info["source_type"] != source_type:
                continue
            
            # Load the document
            doc_path = doc_info["path"]
            try:
                with open(doc_path, 'r') as f:
                    document = json.load(f)
                
                # Calculate a simple relevance score
                score = self._calculate_relevance(document, query)
                
                if score > 0:
                    results.append({
                        "id": doc_id,
                        "score": score,
                        "document": document
                    })
            except Exception as e:
                logger.error(f"Error loading document {doc_id}: {e}")
        
        # Sort by score (descending) and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def _calculate_relevance(self, document: Dict[str, Any], query: str) -> float:
        """
        Calculate relevance score for a document against the query.
        
        Args:
            document (Dict): Document to score
            query (str): Search query
            
        Returns:
            float: Relevance score
        """
        score = 0.0
        query_terms = query.lower().split()
        
        # Check content fields
        content = document["content"]
        
        # Handle different document types differently
        if "title" in content:
            title = content["title"].lower()
            for term in query_terms:
                if term in title:
                    score += 3.0  # Title matches are weighted higher
        
        if "description" in content:
            description = content["description"].lower()
            for term in query_terms:
                if term in description:
                    score += 2.0  # Description matches have medium weight
        
        # Check all other fields with lower weight
        for key, value in content.items():
            if key not in ["title", "description"] and isinstance(value, str):
                text = value.lower()
                for term in query_terms:
                    if term in text:
                        score += 1.0
        
        return score
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.
        
        Returns:
            Dict: Knowledge base statistics
        """
        # Count documents by source type
        source_type_counts = {}
        for doc_info in self.index["documents"].values():
            source_type = doc_info["source_type"]
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
        
        return {
            "total_documents": self.index["document_count"],
            "creation_date": self.index["creation_date"],
            "last_update": self.index["last_update"],
            "by_source_type": source_type_counts
        }
    
    def remove_document(self, doc_id: str) -> bool:
        """
        Remove a document from the knowledge base.
        
        Args:
            doc_id (str): Document ID to remove
            
        Returns:
            bool: Success or failure
        """
        if doc_id not in self.index["documents"]:
            logger.warning(f"Document {doc_id} not found in knowledge base")
            return False
        
        # Get document path and remove file
        doc_path = self.index["documents"][doc_id]["path"]
        if os.path.exists(doc_path):
            os.remove(doc_path)
        
        # Update index
        del self.index["documents"][doc_id]
        self.index["document_count"] = len(self.index["documents"])
        self._save_index()
        
        logger.info(f"Removed document {doc_id} from knowledge base")
        return True