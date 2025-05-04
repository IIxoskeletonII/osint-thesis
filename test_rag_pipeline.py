# test_rag_pipeline.py

"""
Test script for the complete RAG pipeline.
"""

import os
import logging
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager
from src.rag.rag_pipeline import RagPipeline

def main():
    """Test the complete RAG pipeline."""
    # Check if API key is available
    api_key = os.getenv("ANTHROPIC_API_KEY")
    should_generate = api_key is not None
    
    if not should_generate:
        logger.warning("No Anthropic API key found in environment. Will skip generation step.")
    
    # Initialize the knowledge base manager
    kb_manager = KnowledgeBaseManager(
        base_dir="data",
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
    
    # Create the RAG pipeline
    rag_pipeline = RagPipeline(
        knowledge_base_manager=kb_manager,
        api_key=api_key,
        top_k=3,
        temperature=0.2,
        max_tokens=1024
    )
    
    # Test queries
    test_queries = [
        "What is the SQL injection vulnerability that was discovered and how can it be mitigated?",
        "What threat actor techniques were mentioned in the knowledge base?",
        "Explain the benefits of zero-knowledge proofs for authentication"
    ]
    
    for query in test_queries:
        logger.info(f"\n=== Testing RAG pipeline for query: '{query}' ===")
        
        # Process the query
        result = rag_pipeline.process_query(query, generate=should_generate)
        
        # Print retrieval results
        logger.info(f"Retrieved {len(result['retrieved_documents'])} documents")
        
        for i, doc in enumerate(result['retrieved_documents']):
            title = "Unknown"
            score = doc.get("similarity", 0.0)
            
            if "document" in doc and "content" in doc["document"]:
                title = doc["document"]["content"].get("title", "Unknown")
            
            logger.info(f"Document {i+1}: {title} (Score: {score:.4f})")
        
        # Print generated response if available
        if "response" in result:
            logger.info("\nGenerated Response:")
            print("\n" + result["response"] + "\n")
        elif "error" in result:
            logger.error(f"Error: {result['error']}")
        else:
            logger.info("No response generated (API key not provided)")
        
        logger.info("---------------------------------------")
    
    logger.info("RAG pipeline tests completed successfully!")

if __name__ == "__main__":
    main()