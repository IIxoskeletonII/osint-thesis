# test_retriever_fixed.py

"""
Improved test for the BasicRetriever with proper knowledge base location.
"""

import os
import logging
import json
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager
from src.rag.retriever import BasicRetriever

def main():
    """Test the retriever with the knowledge base."""
    # Use the same base directory as in test_knowledge_base.py
    base_dir = "data/test_kb"
    
    # Print directory info
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Knowledge base directory: {os.path.abspath(base_dir)}")
    
    # Check if the directory has content
    if os.path.exists(base_dir):
        logger.info(f"Directory exists, contents: {os.listdir(base_dir)}")
        if os.path.exists(os.path.join(base_dir, "knowledge_base")):
            logger.info(f"Knowledge base subdirectory exists: {os.listdir(os.path.join(base_dir, 'knowledge_base'))}")
    else:
        logger.error(f"Directory does not exist: {base_dir}")
        logger.info("Please run test_knowledge_base.py first")
        return
    
    # Initialize the knowledge base manager with the same settings as test_knowledge_base.py
    kb_manager = KnowledgeBaseManager(
        base_dir=base_dir,
        chunker_type="security",
        embedding_type="security",
        storage_type="simple"
    )
    
    # Get stats to verify the knowledge base has content
    stats = kb_manager.get_stats()
    logger.info(f"Knowledge base stats: {stats}")
    
    if stats["document_count"] == 0:
        logger.warning("Knowledge base is empty. Please run test_knowledge_base.py first.")
        return
    
    # Create the retriever
    retriever = BasicRetriever(kb_manager, top_k=3)
    
    # Test retrieval
    test_queries = [
        "sql injection vulnerability",
        "threat actor techniques",
        "security research methodology"
    ]
    
    for query in test_queries:
        logger.info(f"\nTesting retrieval for query: '{query}'")
        results = retriever.retrieve(query)
        
        if results:
            logger.info(f"Retrieved {len(results)} documents:")
            for i, doc in enumerate(results):
                logger.info(f"Result {i+1}:")
                logger.info(f"  Score: {doc.get('similarity', 'N/A')}")
                
                # Extract source type safely based on document structure
                source_type = None
                if 'document' in doc and 'metadata' in doc['document']:
                    source_type = doc['document']['metadata'].get('source_type', 'N/A')
                logger.info(f"  Source: {source_type}")
                
                # Extract title safely based on document structure
                title = None
                if 'document' in doc and 'content' in doc['document']:
                    title = doc['document']['content'].get('title', 'N/A')
                logger.info(f"  Title: {title}")
        else:
            logger.info("No documents retrieved.")
    
    # Test with filters
    logger.info("\nTesting retrieval with filters:")
    results = retriever.retrieve("vulnerability", filters={"source_type": "vulnerability"})
    logger.info(f"Retrieved {len(results)} vulnerability documents for 'vulnerability'")

if __name__ == "__main__":
    main()