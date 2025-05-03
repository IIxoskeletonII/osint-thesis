"""
Debug script to examine the knowledge base location and files.
"""

import os
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_kb_location():
    """Examine the knowledge base location and files."""
    kb_dir = "data/test_kb"
    
    # Check if the directory exists
    if not os.path.exists(kb_dir):
        logger.error(f"Knowledge base directory not found: {kb_dir}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info("Directory contents:")
        for item in os.listdir():
            logger.info(f"  - {item}")
        return
    
    logger.info(f"Knowledge base directory found: {kb_dir}")
    
    # Check contents of the directory
    logger.info("Knowledge base directory contents:")
    for item in os.listdir(kb_dir):
        logger.info(f"  - {item}")
    
    # Look for specific files
    index_file = os.path.join(kb_dir, "index.json")
    if os.path.exists(index_file):
        logger.info(f"Index file found: {index_file}")
        # Read the index file
        try:
            with open(index_file, 'r') as f:
                index_data = json.load(f)
            logger.info(f"Index file contains {len(index_data)} documents")
        except Exception as e:
            logger.error(f"Error reading index file: {e}")
    else:
        logger.error(f"Index file not found: {index_file}")

if __name__ == "__main__":
    debug_kb_location()