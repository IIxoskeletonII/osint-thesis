"""
Knowledge Base Analyzer for OSINT thesis project.
This script provides functions to analyze the content of the knowledge base
and find information about specific topics.
"""

import os
import json
import logging
import argparse
from typing import List, Dict, Any, Optional, Tuple
import re

# Import knowledge base components
from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KnowledgeBaseAnalyzer:
    """
    Class for analyzing and reporting on knowledge base content.
    """
    
    def __init__(self, kb_manager: KnowledgeBaseManager):
        """
        Initialize the analyzer with a knowledge base manager.
        
        Args:
            kb_manager: The knowledge base manager instance
        """
        self.kb_manager = kb_manager
        logger.info("Knowledge Base Analyzer initialized")
        
    def list_all_documents(self) -> List[Dict[str, Any]]:
        """
        Get a list of all documents in the knowledge base with basic metadata.
        
        Returns:
            List of document summaries
        """
        document_store = self.kb_manager.document_store
        index = document_store.index
        
        documents = []
        for doc_id, doc_info in index["documents"].items():
            documents.append({
                "id": doc_id,
                "source_name": doc_info.get("source_name", "Unknown"),
                "source_type": doc_info.get("source_type", "Unknown"),
                "ingestion_date": doc_info.get("ingestion_date", "Unknown")
            })
            
        return documents
        
    def search_document_content(self, topic: str) -> List[Dict[str, Any]]:
        """
        Search for documents containing a specific topic.
        
        Args:
            topic: The topic to search for
            
        Returns:
            List of document summaries containing the topic
        """
        document_store = self.kb_manager.document_store
        index = document_store.index
        
        matching_docs = []
        pattern = re.compile(fr'\b{re.escape(topic)}\b', re.IGNORECASE)
        
        for doc_id, doc_info in index["documents"].items():
            try:
                # Load the full document
                document = document_store.get_document(doc_id)
                if not document:
                    continue
                    
                # Extract text content
                content = document.get("content", {})
                text_content = self._extract_document_text(content)
                
                # Check if the topic appears in the content
                if pattern.search(text_content):
                    # Count occurrences
                    count = len(pattern.findall(text_content))
                    
                    # Extract a context snippet around the first match
                    match = pattern.search(text_content)
                    snippet = "..."
                    if match:
                        start = max(0, match.start() - 100)
                        end = min(len(text_content), match.end() + 100)
                        snippet = text_content[start:end]
                        # Highlight the match
                        snippet = pattern.sub(f"**{topic}**", snippet)
                    
                    matching_docs.append({
                        "id": doc_id,
                        "source_name": doc_info.get("source_name", "Unknown"),
                        "source_type": doc_info.get("source_type", "Unknown"),
                        "occurrences": count,
                        "snippet": snippet
                    })
            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {e}")
                
        # Sort by number of occurrences (most relevant first)
        matching_docs.sort(key=lambda x: x["occurrences"], reverse=True)
        return matching_docs
        
    def generate_content_report(self, topics: List[str] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive report about the knowledge base content.
        
        Args:
            topics: Optional list of specific topics to analyze
            
        Returns:
            Report dictionary
        """
        # Get general stats
        stats = self.kb_manager.get_stats()
        
        # Add list of all documents
        all_docs = self.list_all_documents()
        
        # Generate report
        report = {
            "stats": stats,
            "document_count": len(all_docs),
            "documents": all_docs,
        }
        
        # If topics specified, add topic analysis
        if topics:
            topic_analysis = {}
            for topic in topics:
                matching_docs = self.search_document_content(topic)
                topic_analysis[topic] = {
                    "document_count": len(matching_docs),
                    "documents": matching_docs
                }
            report["topic_analysis"] = topic_analysis
            
        return report
    
    def _extract_document_text(self, content: Dict[str, Any]) -> str:
        """
        Extract all text content from a document.
        
        Args:
            content: Document content dictionary
            
        Returns:
            Combined text content
        """
        text_parts = []
        
        # Extract title
        if "title" in content and isinstance(content["title"], str):
            text_parts.append(content["title"])
        
        # Extract other text fields
        for field in ["description", "summary", "text", "content"]:
            if field in content and isinstance(content[field], str):
                text_parts.append(content[field])
        
        # Try to extract from any other string fields
        for key, value in content.items():
            if isinstance(value, str) and len(value) > 20 and key not in ["title", "description", "summary", "text", "content"]:
                text_parts.append(value)
                
        # Combine all text parts
        return " ".join(text_parts)


def main():
    """Command line interface for the knowledge base analyzer."""
    parser = argparse.ArgumentParser(description="Analyze OSINT Knowledge Base content")
    parser.add_argument("--base-dir", type=str, default="data", help="Base directory for knowledge base data")
    parser.add_argument("--topics", type=str, nargs="*", help="Topics to search for")
    parser.add_argument("--output", type=str, help="Output file for the report (JSON)")
    args = parser.parse_args()
    
    # Initialize knowledge base manager
    kb_manager = KnowledgeBaseManager(base_dir=args.base_dir)
    
    # Create analyzer
    analyzer = KnowledgeBaseAnalyzer(kb_manager)
    
    # Generate report
    report = analyzer.generate_content_report(args.topics)
    
    # Print summary
    print(f"Knowledge Base Summary:")
    print(f"Total documents: {report['document_count']}")
    
    # Print source type distribution
    print("\nDocument distribution by source type:")
    for source_type, count in report["stats"]["by_source_type"].items():
        print(f"  {source_type}: {count} documents")
    
    # Print topic analysis if topics were specified
    if args.topics and "topic_analysis" in report:
        print("\nTopic Analysis:")
        for topic, analysis in report["topic_analysis"].items():
            print(f"\n  {topic}: found in {analysis['document_count']} documents")
            
            # Print top 3 documents for each topic
            for i, doc in enumerate(analysis["documents"][:3]):
                print(f"    {i+1}. {doc['source_name']} ({doc['occurrences']} occurrences)")
                print(f"       Snippet: {doc['snippet'][:150]}...")
    
    # Save report to file if specified
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nFull report saved to {args.output}")


if __name__ == "__main__":
    main()