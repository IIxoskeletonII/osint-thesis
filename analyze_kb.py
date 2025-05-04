"""
Script to analyze knowledge base content.
Run this script to see what documents are in your knowledge base
and check if specific topics are covered.
"""

import logging
import json
from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager
from src.knowledge_base.knowledge_base_analyzer import KnowledgeBaseAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Topics of interest to check in knowledge base
TOPICS_TO_CHECK = [
    "MITRE ATT&CK",
    "zero trust",
    "ransomware",
    "vulnerability",
    "threat intelligence",
    "CVE",
    "backdoor",
    "phishing"
]

def main():
    # Initialize knowledge base manager with default settings
    kb_manager = KnowledgeBaseManager()
    
    # Create analyzer
    analyzer = KnowledgeBaseAnalyzer(kb_manager)
    
    # Print knowledge base stats
    stats = kb_manager.get_stats()
    print("\n=== Knowledge Base Statistics ===")
    print(f"Total documents: {stats['document_count']}")
    print(f"Total chunks: {stats['chunk_count']}")
    print(f"Average chunks per document: {stats['avg_chunks_per_document']:.2f}")
    
    # Print source type distribution
    print("\n=== Document Distribution by Source Type ===")
    for source_type, count in stats['by_source_type'].items():
        print(f"  {source_type}: {count} documents")
    
    # Check for topics of interest
    print("\n=== Topic Analysis ===")
    for topic in TOPICS_TO_CHECK:
        matching_docs = analyzer.search_document_content(topic)
        print(f"\n-- '{topic}' found in {len(matching_docs)} documents --")
        
        # Print top 3 matching documents
        for i, doc in enumerate(matching_docs[:3]):
            print(f"  {i+1}. {doc['source_name']} ({doc['occurrences']} occurrences)")
            print(f"     Snippet: {doc['snippet'][:150]}...")
    
    # Generate and save full report
    report = analyzer.generate_content_report(TOPICS_TO_CHECK)
    with open("kb_analysis_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nFull report saved to kb_analysis_report.json")


if __name__ == "__main__":
    main()