"""
Improved test for the BasicRetriever, now pointing to the main knowledge base.
"""

import os
import logging
import json
import sys # Make sure sys is imported if not already
from pathlib import Path

# Add src directory to path if running script directly from root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '.')) # Assumes script is in root
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our modules
try:
    from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager
    from src.rag.retriever import BasicRetriever
except ImportError as e:
     logger.error(f"Import Error: {e}. Ensure the script is run from the project root or src is in PYTHONPATH.")
     sys.exit(1)

def main():
    """Test the retriever with the main knowledge base."""


    base_dir = "data"

    abs_base_dir = os.path.abspath(base_dir)
    kb_path = os.path.join(abs_base_dir, "knowledge_base")

    # Print directory info
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Target Knowledge Base Parent Directory: {abs_base_dir}")
    logger.info(f"Expected Knowledge Base Path: {kb_path}")

    # Check if the target knowledge base directory exists
    if not os.path.exists(kb_path):
        logger.error(f"Target Knowledge Base directory does not exist: {kb_path}")
        logger.error("Please run the ingest_documents.py script first to populate the knowledge base.")
        return

    logger.info(f"Found knowledge base directory at: {kb_path}")

    try:
        # Initialize the knowledge base manager pointing to the correct base directory
        kb_manager = KnowledgeBaseManager(
            base_dir=base_dir,  
            chunker_type="security",
            embedding_type="security",
            storage_type="simple"
        )
    except Exception as e:
        logger.error(f"Failed to initialize KnowledgeBaseManager for '{base_dir}': {e}", exc_info=True)
        return

    # Get stats to verify the knowledge base has content
    try:
        stats = kb_manager.get_stats()
        logger.info(f"Knowledge base stats: {stats}")

        if stats["document_count"] == 0 or stats["chunk_count"] == 0:
            logger.warning("Knowledge base appears empty or incomplete. Verify ingestion was successful.")
            # Allow test to continue, but results might be empty
    except Exception as e:
        logger.error(f"Failed to get KB stats: {e}")
        return

    # Create the retriever
    retriever = BasicRetriever(kb_manager, top_k=3) # Keep top_k=3 for manageable output

    # Test retrieval
    test_queries = [
        "sql injection vulnerability",
        "threat actor techniques",
        "APT29 malware",
        "zero-knowledge proofs",
        "security research methodology"
    ]

    for query in test_queries:
        logger.info(f"\n=== Testing retrieval for query: '{query}' ===")
        try:
            results = retriever.retrieve(query)

            if results:
                logger.info(f"Retrieved {len(results)} unique documents:")
                for i, doc_result in enumerate(results): # Renamed doc to doc_result to avoid confusion
                    logger.info(f"Result {i+1}:")
                    logger.info(f"  Similarity Score: {doc_result.get('similarity', 'N/A')}")

                    # Safely access nested document structure
                    doc_data = doc_result.get('document', {})
                    doc_content = doc_data.get('content', {})
                    doc_metadata = doc_data.get('metadata', {})

                    title = doc_content.get('title', 'N/A')
                    source_type = doc_metadata.get('source_type', 'N/A')
                    source_name = doc_metadata.get('source_name', 'N/A')
                    chunk_index = doc_metadata.get('chunk_index', -1)
                    original_doc_id = doc_metadata.get('original_doc_id', 'N/A')


                    logger.info(f"  Title: {title}")
                    logger.info(f"  Source Type: {source_type}")
                    logger.info(f"  Source Name: {source_name}")
                    if chunk_index != -1:
                        logger.info(f"  Chunk Index: {chunk_index}")
                        logger.info(f"  Original Doc ID: {original_doc_id}")

            else:
                logger.info("No documents retrieved for this query.")
        except Exception as e:
            logger.error(f"Error during retrieval for query '{query}': {e}", exc_info=True)


    # Test with filters
    logger.info("\n=== Testing retrieval with filters ===")
    try:
        # Filter by source type
        filter_query = "vulnerability"
        filters = {"source_type": "vulnerability"}
        logger.info(f"Retrieving for '{filter_query}' with filter: {filters}")
        results = retriever.retrieve(filter_query, filters=filters)
        logger.info(f"Retrieved {len(results)} documents matching filter {filters}")
        for i, doc_result in enumerate(results[:3]): # Show top 3
             doc_data = doc_result.get('document', {})
             doc_content = doc_data.get('content', {})
             doc_metadata = doc_data.get('metadata', {})
             title = doc_content.get('title', 'N/A')
             st = doc_metadata.get('source_type', 'N/A')
             logger.info(f"  Filtered Result {i+1}: {title} (Type: {st}, Score: {doc_result.get('similarity', 'N/A'):.4f})")

        # Add another filter test if applicable (e.g., for threat)
        filter_query = "attack techniques"
        filters = {"source_type": "threat"}
        logger.info(f"\nRetrieving for '{filter_query}' with filter: {filters}")
        results = retriever.retrieve(filter_query, filters=filters)
        logger.info(f"Retrieved {len(results)} documents matching filter {filters}")
        for i, doc_result in enumerate(results[:3]):
             doc_data = doc_result.get('document', {})
             doc_content = doc_data.get('content', {})
             doc_metadata = doc_data.get('metadata', {})
             title = doc_content.get('title', 'N/A')
             st = doc_metadata.get('source_type', 'N/A')
             logger.info(f"  Filtered Result {i+1}: {title} (Type: {st}, Score: {doc_result.get('similarity', 'N/A'):.4f})")

    except Exception as e:
        logger.error(f"Error during filtered retrieval: {e}", exc_info=True)

    logger.info("\nRetriever testing finished.")


if __name__ == "__main__":
    main()