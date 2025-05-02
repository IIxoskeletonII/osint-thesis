"""
Direct testing of knowledge base components.
This script tests the chunking and embedding directly
without going through document storage.
"""

import os
import logging
import json
from typing import Dict, List, Any

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the component classes directly
from src.knowledge_base.chunking import get_chunker
from src.knowledge_base.embedding import get_embedding_generator

def create_test_document(title: str, content: str) -> Dict[str, Any]:
    """Create a test document with proper structure."""
    return {
        "content": {
            "title": title,
            "description": content,
            "author": "Test Author",
            "date": "2025-04-01"
        },
        "metadata": {
            "id": "test-doc-001",
            "source_type": "test",
            "source_name": "Test Source"
        }
    }

def main():
    # Create a test document
    test_doc = create_test_document(
        "SQL Injection Vulnerability",
        """
        A critical SQL injection vulnerability has been discovered.
        This vulnerability allows attackers to bypass authentication
        and access sensitive data.
        """
    )
    
    logger.info("=== Test Document Structure ===")
    logger.info(f"Document keys: {list(test_doc.keys())}")
    logger.info(f"Content keys: {list(test_doc['content'].keys())}")
    logger.info(f"Title: {test_doc['content']['title']}")
    logger.info(f"Description: {test_doc['content']['description']}")
    
    # Create a chunker
    chunker = get_chunker("security")
    
    # Test chunking
    logger.info("\n=== Testing Chunking ===")
    chunks = chunker.chunk_document(test_doc)
    logger.info(f"Document chunked into {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        logger.info(f"Chunk {i+1}:")
        logger.info(f"  Metadata keys: {list(chunk['metadata'].keys())}")
        logger.info(f"  Content keys: {list(chunk['content'].keys())}")
        if 'title' in chunk['content']:
            logger.info(f"  Title: {chunk['content']['title']}")
        if 'description' in chunk['content']:
            desc = chunk['content']['description']
            logger.info(f"  Description: {desc[:100]}..." if len(desc) > 100 else desc)
    
    # Create an embedding generator
    embedding_gen = get_embedding_generator("security")
    
    # Test embedding generation
    logger.info("\n=== Testing Embedding Generation ===")
    embedded_chunks = embedding_gen.generate_embeddings_for_chunks(chunks)
    
    for i, chunk in enumerate(embedded_chunks):
        logger.info(f"Embedded Chunk {i+1}:")
        logger.info(f"  Has embedding: {'embedding' in chunk['metadata']}")
        if 'embedding' in chunk['metadata']:
            embedding = chunk['metadata']['embedding']
            logger.info(f"  Embedding length: {len(embedding)}")
            logger.info(f"  First 5 values: {embedding[:5]}")
    
    logger.info("\nDirect testing completed successfully!")

if __name__ == "__main__":
    main()