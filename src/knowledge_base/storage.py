"""
Vector storage implementation for OSINT knowledge base.
This module provides a simple vector storage solution for document embeddings
and supports vector similarity search.
"""

import os
import json
import logging
import shutil
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorStorage:
    """Base class for vector storage implementations."""
    
    def add_document(self, document: Dict[str, Any]) -> str:
        """
        Add a document with embedding to storage.
        
        Args:
            document (Dict): Document with embedding in metadata
            
        Returns:
            str: Document ID
        """
        raise NotImplementedError("Subclasses must implement add_document")
    
    def search(self, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for similar documents by vector similarity.
        
        Args:
            query_vector (List[float]): Query embedding vector
            limit (int): Maximum number of results
            
        Returns:
            List[Dict]: Similar documents with similarity scores
        """
        raise NotImplementedError("Subclasses must implement search")
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID.
        
        Args:
            doc_id (str): Document ID
            
        Returns:
            Optional[Dict]: Document or None if not found
        """
        raise NotImplementedError("Subclasses must implement get_document")


class SimpleVectorStorage(VectorStorage):
    """
    A simple file-based vector storage implementation.
    Provides basic vector similarity search capabilities.
    """
    
    def __init__(self, storage_dir: str):
        """
        Initialize the vector storage.
        
        Args:
            storage_dir (str): Directory to store vector data
        """
        self.storage_dir = storage_dir
        self.vectors_dir = os.path.join(storage_dir, "vectors")
        self.index_file = os.path.join(storage_dir, "vector_index.json")
        
        # Create directories if they don't exist
        os.makedirs(self.vectors_dir, exist_ok=True)
        
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
        
        logger.info(f"Vector storage initialized with {len(self.index['documents'])} documents")
    
    def _save_index(self):
        """Save the current index to disk."""
        self.index["last_update"] = datetime.now().isoformat()
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def add_document(self, document: Dict[str, Any]) -> str:
        """
        Add a document with embedding to storage.
        
        Args:
            document (Dict): Document with embedding in metadata
            
        Returns:
            str: Document ID
        """
        # Ensure document has required metadata
        if "metadata" not in document or "embedding" not in document["metadata"]:
            raise ValueError("Document must have embedding in metadata")
        
        doc_id = document["metadata"]["id"]
        
        # Save document to file
        doc_path = os.path.join(self.vectors_dir, f"{doc_id}.json")
        with open(doc_path, 'w') as f:
            json.dump(document, f, indent=2)
        
        # Update index
        self.index["documents"][doc_id] = {
            "id": doc_id,
            "source_type": document["metadata"].get("source_type", "unknown"),
            "source_name": document["metadata"].get("source_name", "unknown"),
            "ingestion_date": document["metadata"].get("ingestion_date", datetime.now().isoformat()),
            "path": doc_path,
            "has_embedding": True
        }
        
        self.index["document_count"] = len(self.index["documents"])
        self._save_index()
        
        logger.info(f"Added document with embedding to vector storage: {doc_id}")
        return doc_id
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID.
        
        Args:
            doc_id (str): Document ID
            
        Returns:
            Optional[Dict]: Document or None if not found
        """
        if doc_id not in self.index["documents"]:
            logger.warning(f"Document {doc_id} not found in vector storage")
            return None
        
        doc_path = self.index["documents"][doc_id]["path"]
        if not os.path.exists(doc_path):
            logger.error(f"Document file {doc_path} not found on disk")
            return None
        
        with open(doc_path, 'r') as f:
            return json.load(f)
    
    def search(self, query_vector: List[float], limit: int = 10, 
              filter_source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents by vector similarity.
        
        Args:
            query_vector (List[float]): Query embedding vector
            limit (int): Maximum number of results
            filter_source_type (Optional[str]): Filter by source type
            
        Returns:
            List[Dict]: Similar documents with similarity scores
        """
        if not query_vector:
            logger.error("Empty query vector provided for search")
            return []
        
        query_vector = np.array(query_vector)
        results = []
        
        # Process each document
        for doc_id, doc_info in self.index["documents"].items():
            # Apply source type filter if specified
            if filter_source_type and doc_info.get("source_type") != filter_source_type:
                continue
            
            # Skip documents without embeddings
            if not doc_info.get("has_embedding", False):
                continue
            
            # Load the document
            doc_path = doc_info["path"]
            try:
                with open(doc_path, 'r') as f:
                    document = json.load(f)
                
                # Get the document embedding
                doc_vector = np.array(document["metadata"].get("embedding", []))
                
                if len(doc_vector) > 0:
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_vector, doc_vector)
                    
                    results.append({
                        "id": doc_id,
                        "similarity": float(similarity),
                        "document": document
                    })
            except Exception as e:
                logger.error(f"Error processing document {doc_id} during search: {e}")
        
        # Sort by similarity (descending) and limit results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1 (np.ndarray): First vector
            vec2 (np.ndarray): Second vector
            
        Returns:
            float: Cosine similarity (-1 to 1)
        """
        if len(vec1) != len(vec2):
            logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
            return 0.0
        
        try:
            # Make sure we're working with numpy arrays
            vec1 = np.array(vec1, dtype=np.float32)
            vec2 = np.array(vec2, dtype=np.float32)
            
            # Check for zero vectors
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 < 1e-10 or norm2 < 1e-10:
                logger.warning("Zero norm vector detected in similarity calculation")
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            
            # Ensure the result is valid
            if np.isnan(similarity):
                logger.warning("NaN similarity detected")
                return 0.0
                
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from vector storage.
        
        Args:
            doc_id (str): Document ID to delete
            
        Returns:
            bool: Success or failure
        """
        if doc_id not in self.index["documents"]:
            logger.warning(f"Document {doc_id} not found in vector storage")
            return False
        
        # Get document path and remove file
        doc_path = self.index["documents"][doc_id]["path"]
        if os.path.exists(doc_path):
            os.remove(doc_path)
        
        # Update index
        del self.index["documents"][doc_id]
        self.index["document_count"] = len(self.index["documents"])
        self._save_index()
        
        logger.info(f"Deleted document {doc_id} from vector storage")
        return True
    
    def clear(self) -> bool:
        """
        Clear all documents from vector storage.
        
        Returns:
            bool: Success or failure
        """
        try:
            # Remove all document files
            if os.path.exists(self.vectors_dir):
                shutil.rmtree(self.vectors_dir)
                os.makedirs(self.vectors_dir)
            
            # Reset index
            self.index = {
                "creation_date": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "document_count": 0,
                "documents": {}
            }
            self._save_index()
            
            logger.info("Vector storage cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing vector storage: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector storage.
        
        Returns:
            Dict: Vector storage statistics
        """
        # Count documents by source type
        source_type_counts = {}
        for doc_info in self.index["documents"].values():
            source_type = doc_info.get("source_type", "unknown")
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
        
        return {
            "total_documents": self.index["document_count"],
            "creation_date": self.index["creation_date"],
            "last_update": self.index["last_update"],
            "by_source_type": source_type_counts
        }


# Factory function to get a vector storage instance
def get_vector_storage(storage_type: str = "simple", 
                      storage_dir: str = "data/vector_storage") -> VectorStorage:
    """
    Factory function to get a vector storage instance.
    
    Args:
        storage_type (str): Type of vector storage
        storage_dir (str): Directory to store vector data
        
    Returns:
        VectorStorage: An instance of the specified storage
    """
    if storage_type.lower() == "simple":
        return SimpleVectorStorage(storage_dir)
    else:
        # Default to simple storage
        logger.warning(f"Unknown storage type: {storage_type}, using simple storage")
        return SimpleVectorStorage(storage_dir)