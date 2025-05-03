# test_rag_prompts.py

"""
Test script for the RAG prompt templates.
"""

import os
import logging
import json
from pprint import pprint

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager
from src.rag.retriever import BasicRetriever
from src.rag.prompts import PromptTemplateManager

def main():
    """Test the RAG prompt templates with the retriever."""
    # Initialize the knowledge base manager
    kb_manager = KnowledgeBaseManager(
        base_dir="data/test_kb",
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
    retriever = BasicRetriever(kb_manager, top_k=2)
    
    # Create the prompt template manager
    prompt_manager = PromptTemplateManager()
    
    # Test queries
    test_queries = [
        "Explain the SQL injection vulnerability that was discovered and how to mitigate it",
        "What techniques does APT29 use in their attacks?",
        "Describe the benefits of zero-knowledge proofs for authentication"
    ]
    
    for query in test_queries:
        logger.info(f"\n=== Testing RAG prompt for query: '{query}' ===")
        
        # Retrieve relevant documents
        retrieved_docs = retriever.retrieve(query)
        logger.info(f"Retrieved {len(retrieved_docs)} documents")
        
        # Format the RAG prompt
        prompt = prompt_manager.format_rag_prompt(query, retrieved_docs)
        
        # Print the formatted prompt
        logger.info("Formatted System Prompt:")
        print("\n" + prompt["system"] + "\n")
        
        logger.info("Formatted User Prompt (excerpt):")
        user_prompt_excerpt = prompt["user"].split("\n\n")[0] + "\n\n[...content truncated...]"
        print("\n" + user_prompt_excerpt + "\n")
        
        logger.info("---------------------------------------")
    
    logger.info("RAG prompt tests completed successfully!")

if __name__ == "__main__":
    main()