"""
Test script for the knowledge base implementation.
This script tests the creation, indexing, and retrieval functionality
of the knowledge base.
"""

import os
import logging
import json
import argparse
import sys
from typing import Dict, List, Any

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our modules
from src.knowledge_base.simple_knowledge_base import SimpleKnowledgeBase
from src.knowledge_base.chunking import get_chunker
from src.knowledge_base.embedding import get_embedding_generator
from src.knowledge_base.storage import get_vector_storage
from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager

def create_test_document(doc_id: str, title: str, content: str, 
                        source_type: str, source_name: str) -> Dict[str, Any]:
    """Create a test document for the knowledge base."""
    # Clean up the content by removing leading/trailing whitespace and normalizing newlines
    clean_content = content.strip()
    # Replace multiple newlines with a single newline
    import re
    clean_content = re.sub(r'\n\s*\n', '\n\n', clean_content)
    
    # Create proper document structure directly
    return {
        "content": {
            "title": title,
            "description": clean_content,
            "author": "Test Author",
            "date": "2025-04-01"
        },
        "metadata": {
            "id": doc_id,
            "source_type": source_type,
            "source_name": source_name
        }
    }
def populate_test_data(kb_manager: KnowledgeBaseManager) -> List[str]:
    """Populate the knowledge base with test data."""
    doc_ids = []
    
    # Create a vulnerability document
    vuln_doc = create_test_document(
        "test-vuln-001",
        "Critical SQL Injection Vulnerability in Web Application",
        """
        A critical SQL injection vulnerability has been discovered in the login form
        of the web application. This vulnerability allows attackers to bypass authentication
        and access sensitive user data. The vulnerability exists because user input is not
        properly sanitized before being used in SQL queries. Attackers can inject malicious
        SQL code to manipulate the database and extract information.
        
        CVE-2025-1234 has been assigned to this vulnerability. The CVSS score is 9.8,
        indicating critical severity. All versions prior to 2.3.5 are affected.
        
        Mitigation: Update to version 2.3.5 or implement proper input validation and
        parameterized queries to prevent SQL injection attacks.
        """,
        "vulnerability",
        "NVD"
    )
    
    # Debug the document structure
    debug_document_structure(vuln_doc)
    
    doc_id, _ = kb_manager.add_document(vuln_doc, "vulnerability", "NVD")
    doc_ids.append(doc_id)
    
    # Add a threat intelligence document
    threat_doc = create_test_document(
        "test-threat-001",
        "APT29 Campaign Targeting Healthcare Organizations",
        """
        A sophisticated campaign attributed to APT29 (also known as Cozy Bear) has been
        observed targeting healthcare organizations. The threat actor is using spear-phishing
        emails with COVID-19 themed lures to deliver custom malware.
        
        The attack chain begins with a phishing email containing a malicious document.
        When opened, the document exploits CVE-2023-5678 to download and execute a
        custom backdoor called "HealthSteal". This backdoor establishes persistence
        through a scheduled task and communicates with command and control servers
        using encrypted HTTPS connections.
        
        Indicators of compromise include domain names like health-updates.com and
        vaccine-tracker.net, which are used for command and control. File hashes for
        the malware include 5f8d3b7c55b116c0a6db0baaf12c3b29 (MD5).
        
        Organizations in the healthcare sector should implement email filtering,
        keep systems patched, and monitor for the provided indicators of compromise.
        """,
        "threat",
        "MITRE ATT&CK"
    )
    
    doc_id, _ = kb_manager.add_document(threat_doc, "threat", "MITRE ATT&CK")
    doc_ids.append(doc_id)
    
    # Add a research paper document
    research_doc = create_test_document(
        "test-research-001",
        "Advances in Zero-Knowledge Proofs for Privacy-Preserving Authentication",
        """
        This research paper explores recent advances in zero-knowledge proof systems
        and their applications to privacy-preserving authentication mechanisms. We present
        a novel approach that reduces computational overhead while maintaining strong
        security guarantees.
        
        Zero-knowledge proofs allow one party (the prover) to prove to another party
        (the verifier) that a statement is true without revealing any additional information.
        This property makes them ideal for authentication systems where privacy is paramount.
        
        Our proposed system, ZKAuth, implements a variant of the Schnorr protocol with
        optimizations that reduce verification time by 43% compared to existing approaches.
        We demonstrate the practicality of ZKAuth through a prototype implementation and
        evaluate its performance across multiple platforms.
        
        Experimental results show that ZKAuth can process over 1,000 authentication
        requests per second on commodity hardware while providing formal security guarantees.
        The system is particularly suited for resource-constrained environments such as
        IoT devices and mobile applications.
        
        We also discuss potential applications in secure voting systems, anonymous
        credentials, and blockchain-based identity management.
        """,
        "research",
        "arXiv"
    )
    
    doc_id, _ = kb_manager.add_document(research_doc, "research", "arXiv")
    doc_ids.append(doc_id)
    
    logger.info(f"Added {len(doc_ids)} test documents to the knowledge base")
    return doc_ids

def run_test_queries(kb_manager: KnowledgeBaseManager):
    """Run test queries against the knowledge base."""
    # Test 1: Basic semantic search
    logger.info("\n=== Test 1: Basic Semantic Search ===")
    query = "sql injection vulnerability"
    results = kb_manager.search(query, limit=5)
    
    logger.info(f"Query: {query}")
    logger.info(f"Found {len(results)} results")
    
    for i, result in enumerate(results[:3]):  # Show top 3 for brevity
        title = result['document']['content'].get('title', 'No title')
        # Also display a snippet of content for context
        content = result['document']['content'].get('description', '')
        if content:
            snippet = content[:100] + "..." if len(content) > 100 else content
        else:
            snippet = "No content"
            
        logger.info(f"Result {i+1}: {title} (Score: {result['similarity']:.4f})")
        logger.info(f"  Snippet: {snippet}")
    

def debug_document_structure(document):
    """Print the document structure for debugging."""
    logger.info("=== Document Structure Debug ===")
    logger.info(f"Document ID: {document['metadata']['id']}")
    logger.info(f"Metadata keys: {list(document['metadata'].keys())}")
    logger.info(f"Content keys: {list(document['content'].keys())}")
    
    # Print sample of content values
    for key, value in document['content'].items():
        if isinstance(value, str):
            sample = value[:100] + "..." if len(value) > 100 else value
            logger.info(f"Content '{key}': {sample}")

def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test knowledge base functionality")
    parser.add_argument("--base-dir", default="data/test_kb", 
                        help="Base directory for test knowledge base")
    parser.add_argument("--clean", action="store_true", 
                        help="Clean existing data before testing")
    args = parser.parse_args()
    
    # Clean the test directory if requested
    if args.clean and os.path.exists(args.base_dir):
        import shutil
        shutil.rmtree(args.base_dir)
        logger.info(f"Cleaned test directory: {args.base_dir}")
    
    # Create test directory if it doesn't exist
    os.makedirs(args.base_dir, exist_ok=True)
    
    # Initialize the knowledge base manager
    kb_manager = KnowledgeBaseManager(
        base_dir=args.base_dir,
        chunker_type="security",
        embedding_type="security",
        storage_type="simple"
    )
    logger.info("Initialized knowledge base manager for testing")
    
    # Populate with test data
    doc_ids = populate_test_data(kb_manager)
    
    # Run test queries
    run_test_queries(kb_manager)
    
    # Report knowledge base statistics
    stats = kb_manager.get_stats()
    logger.info("\n=== Knowledge Base Statistics ===")
    logger.info(f"Document count: {stats['document_count']}")
    logger.info(f"Chunk count: {stats['chunk_count']}")
    logger.info(f"Average chunks per document: {stats['avg_chunks_per_document']:.2f}")
    logger.info(f"Documents by source type:")
    for source_type, count in stats.get('by_source_type', {}).items():
        logger.info(f"  - {source_type}: {count}")
    
    logger.info("\nKnowledge base testing completed successfully!")

if __name__ == "__main__":
    main()