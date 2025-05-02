"""
Knowledge Base Manager for OSINT thesis project.
This module integrates chunking, embedding, and storage components 
to provide a complete knowledge base solution.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Import our knowledge base components
from src.knowledge_base.chunking import get_chunker
from src.knowledge_base.embedding import get_embedding_generator
from src.knowledge_base.storage import get_vector_storage
from src.knowledge_base.simple_knowledge_base import SimpleKnowledgeBase
logger = logging.getLogger(__name__)

class KnowledgeBaseManager:
    """
    Manager class that integrates chunking, embedding, and storage
    to provide a complete knowledge base solution.
    """
    
    def __init__(self, 
                base_dir: str = "data", 
                chunker_type: str = "security",
                embedding_type: str = "security",
                embedding_model: str = "all-MiniLM-L6-v2",
                storage_type: str = "simple"):
        """
        Initialize the knowledge base manager with specified components.
        
        Args:
            base_dir (str): Base directory for knowledge base data
            chunker_type (str): Type of chunker to use
            embedding_type (str): Type of embedding generator to use
            embedding_model (str): Name of embedding model to use
            storage_type (str): Type of vector storage to use
        """
        self.base_dir = base_dir
        
        # Set up storage directories
        self.kb_dir = os.path.join(base_dir, "knowledge_base")
        self.vector_dir = os.path.join(self.kb_dir, "vectors")
        os.makedirs(self.kb_dir, exist_ok=True)
        os.makedirs(self.vector_dir, exist_ok=True)
        
        # Initialize components
        self.chunker = get_chunker(chunker_type)
        self.embedding_generator = get_embedding_generator(embedding_type, embedding_model)
        self.vector_storage = get_vector_storage(storage_type, self.vector_dir)
        self.document_store = SimpleKnowledgeBase(self.kb_dir)
        
        logger.info(f"KnowledgeBaseManager initialized with {chunker_type} chunker, "
                   f"{embedding_type} embeddings, and {storage_type} storage")
    
    def add_document(self, document: Dict[str, Any], 
                    source_type: str, 
                    source_name: str) -> Tuple[str, List[str]]:
        """
        Process and add a document to the knowledge base.
        
        Args:
            document (Dict): Document to add
            source_type (str): Type of source
            source_name (str): Name of source
            
        Returns:
            Tuple[str, List[str]]: Original document ID and chunk IDs
        """
        # Debug document before adding
        if "content" in document:
            content = document["content"]
            logger.info(f"Adding document with content keys: {list(content.keys())}")
            if "title" in content:
                logger.info(f"Document title: {content['title']}")
                if "description" in content:
                    desc_sample = content["description"][:100] + "..." if len(content["description"]) > 100 else content["description"]
                    logger.info(f"Description sample: {desc_sample}")
        else:
            logger.warning("Document missing content section")
        
        # Step 1: Add the original document to the document store
        doc_id = self.document_store.add_document(document, source_type, source_name)
        
        # Step 2: Retrieve the stored document with metadata
        stored_doc = self.document_store.get_document(doc_id)
        if not stored_doc:
            logger.error(f"Failed to retrieve document {doc_id} after adding")
            return doc_id, []
        
        # Debug stored document
        if "content" in stored_doc:
            logger.info(f"Retrieved stored document with content keys: {list(stored_doc['content'].keys())}")
        else:
            logger.error(f"Invalid document structure: 'content' missing")
            return doc_id, []
        
        # Step 3: Chunk the document
        logger.info(f"Chunking document {doc_id}")
        chunks = self.chunker.chunk_document(stored_doc)
        logger.info(f"Document {doc_id} split into {len(chunks)} chunks")
        
        # Step 4: Generate embeddings for chunks
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        embedded_chunks = self.embedding_generator.generate_embeddings_for_chunks(chunks)
        
        # Step 5: Store chunks with embeddings in vector storage
        chunk_ids = []
        for chunk in embedded_chunks:
            chunk_id = self.vector_storage.add_document(chunk)
            chunk_ids.append(chunk_id)
        
        logger.info(f"Added document {doc_id} with {len(chunk_ids)} embedded chunks")
        return doc_id, chunk_ids
    
    def search(self, query: str, limit: int = 10, 
              filter_source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search the knowledge base using semantic similarity.
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results to return
            filter_source_type (Optional[str]): Filter by source type
            
        Returns:
            List[Dict]: Search results with similarity scores
        """
        # Generate embedding for the query
        logger.info(f"Generating embedding for query: {query}")
        query_embedding = self.embedding_generator.generate_embedding(query)
        
        # Search using the query embedding
        logger.info(f"Searching with query embedding, limit={limit}")
        results = self.vector_storage.search(
            query_embedding, 
            limit=limit,
            filter_source_type=filter_source_type
        )
        
        logger.info(f"Found {len(results)} results for query: {query}")
        return results
    
    def get_document(self, doc_id: str, get_chunks: bool = False) -> Dict[str, Any]:
        """
        Get a document by ID, optionally including its chunks.
        
        Args:
            doc_id (str): Document ID
            get_chunks (bool): Whether to include chunks
            
        Returns:
            Dict: Document with optional chunks
        """
        # Get the original document
        document = self.document_store.get_document(doc_id)
        if not document:
            logger.warning(f"Document {doc_id} not found")
            return {}
        
        # If chunks are requested, find and include them
        if get_chunks:
            # Find chunks by filtering vector storage documents
            # This is simplified; in a real implementation, you'd have a more efficient way to do this
            chunks = []
            for chunk_doc_id, doc_info in self.vector_storage.index["documents"].items():
                chunk_doc = self.vector_storage.get_document(chunk_doc_id)
                if chunk_doc and chunk_doc["metadata"].get("original_doc_id") == doc_id:
                    chunks.append(chunk_doc)
            
            document["chunks"] = chunks
            logger.info(f"Retrieved document {doc_id} with {len(chunks)} chunks")
        else:
            logger.info(f"Retrieved document {doc_id} without chunks")
            
        return document
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.
        
        Returns:
            Dict: Knowledge base statistics
        """
        doc_store_stats = self.document_store.get_stats()
        vector_stats = self.vector_storage.get_stats()
        
        # Calculate the average number of chunks per document
        avg_chunks = 0
        if doc_store_stats["total_documents"] > 0:
            avg_chunks = vector_stats["total_documents"] / doc_store_stats["total_documents"]
        
        return {
            "document_count": doc_store_stats["total_documents"],
            "chunk_count": vector_stats["total_documents"],
            "avg_chunks_per_document": avg_chunks,
            "creation_date": doc_store_stats["creation_date"],
            "last_update": doc_store_stats["last_update"],
            "by_source_type": doc_store_stats["by_source_type"]
        }
    
    def text_search(self, query: str, limit: int = 10, 
                   filter_source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform a text-based (non-semantic) search using the document store.
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results to return
            filter_source_type (Optional[str]): Filter by source type
            
        Returns:
            List[Dict]: Search results
        """
        return self.document_store.search(query, source_type=filter_source_type, limit=limit)
    
    def hybrid_search(self, query: str, limit: int = 10, 
                     filter_source_type: Optional[str] = None,
                     semantic_weight: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform a hybrid search combining semantic and text-based search.
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results to return
            filter_source_type (Optional[str]): Filter by source type
            semantic_weight (float): Weight for semantic results (0-1)
            
        Returns:
            List[Dict]: Search results
        """
        # Get semantic search results
        semantic_results = self.search(
            query, 
            limit=limit*2,  # Get more results to allow for merging
            filter_source_type=filter_source_type
        )
        
        # Get text search results
        text_results = self.text_search(
            query,
            limit=limit*2,  # Get more results to allow for merging
            filter_source_type=filter_source_type
        )
        
        # Create a map of document IDs to results for easy lookup
        results_map = {}
        
        # Add semantic results to the map with weighted scores
        for result in semantic_results:
            doc_id = result["id"]
            results_map[doc_id] = {
                "id": doc_id,
                "document": result["document"],
                "semantic_score": result["similarity"],
                "text_score": 0.0,
                "combined_score": result["similarity"] * semantic_weight
            }
        
        # Add or update with text results
        for result in text_results:
            doc_id = result["id"]
            text_score = result["score"] / 10.0  # Normalize text score to 0-1 range
            
            if doc_id in results_map:
                # Update existing entry
                results_map[doc_id]["text_score"] = text_score
                results_map[doc_id]["combined_score"] += text_score * (1 - semantic_weight)
            else:
                # Add new entry
                results_map[doc_id] = {
                    "id": doc_id,
                    "document": result["document"],
                    "semantic_score": 0.0,
                    "text_score": text_score,
                    "combined_score": text_score * (1 - semantic_weight)
                }
        
        # Convert map to list and sort by combined score
        combined_results = list(results_map.values())
        combined_results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        logger.info(f"Hybrid search found {len(combined_results)} results for query: {query}")
        return combined_results[:limit]
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document and its chunks from the knowledge base.
        
        Args:
            doc_id (str): Document ID to delete
            
        Returns:
            bool: Success or failure
        """
        # Get document to find associated chunks
        document = self.get_document(doc_id, get_chunks=True)
        if not document:
            logger.warning(f"Document {doc_id} not found for deletion")
            return False
        
        # Delete chunks from vector storage
        if "chunks" in document:
            for chunk in document["chunks"]:
                chunk_id = chunk["metadata"]["id"]
                self.vector_storage.delete_document(chunk_id)
                logger.info(f"Deleted chunk {chunk_id} from vector storage")
        
        # Delete original document
        result = self.document_store.remove_document(doc_id)
        logger.info(f"Deleted document {doc_id} from document store: {result}")
        
        return result