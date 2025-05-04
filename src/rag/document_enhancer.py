"""
Document enhancer module for the OSINT system.
Enhances document metadata for better source attribution.
"""

import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class DocumentEnhancer:
    """
    Enhances documents with better metadata for source attribution.
    """
    
    @staticmethod
    def enhance_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance a list of documents with better metadata.
        
        Args:
            documents: List of documents to enhance
            
        Returns:
            Enhanced documents with improved metadata
        """
        enhanced_docs = []
        
        for doc in documents:
            enhanced_doc = DocumentEnhancer.enhance_document(doc)
            enhanced_docs.append(enhanced_doc)
            
        return enhanced_docs
    
    @staticmethod
    def enhance_document(doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a single document with better metadata.
        
        Args:
            doc: Document to enhance
            
        Returns:
            Enhanced document with improved metadata
        """
        # Make a copy to avoid modifying the original
        enhanced_doc = doc.copy()
        
        # Extract document content if available
        document_obj = enhanced_doc.get("document", {})
        
        # Handle the case where document might be nested or directly in the object
        if "document" in document_obj and isinstance(document_obj["document"], dict):
            document_obj = document_obj["document"]
        
        content_obj = {}
        if "content" in document_obj and document_obj["content"]:
            content_obj = document_obj["content"]
        elif "content" in enhanced_doc and enhanced_doc["content"]:
            content_obj = enhanced_doc["content"]
        
        # Extract title from content
        if isinstance(content_obj, dict):
            if "title" in content_obj and not enhanced_doc.get("title"):
                enhanced_doc["title"] = content_obj["title"]
            
            # Extract text content for potential title creation
            content_text = ""
            for field in ["description", "text", "content"]:
                if field in content_obj and content_obj[field]:
                    content_text = content_obj[field]
                    break
        elif isinstance(content_obj, str):
            content_text = content_obj
        else:
            content_text = ""
        
        # Extract metadata
        metadata = {}
        if "metadata" in document_obj:
            metadata = document_obj["metadata"]
        elif "metadata" in enhanced_doc:
            metadata = enhanced_doc["metadata"]
        
        # Extract source information from metadata
        if isinstance(metadata, dict):
            if "source_name" in metadata and not enhanced_doc.get("source"):
                enhanced_doc["source"] = metadata["source_name"]
            elif "source" in metadata and not enhanced_doc.get("source"):
                enhanced_doc["source"] = metadata["source"]
            
            # Extract source type
            if "source_type" in metadata and not enhanced_doc.get("source_type"):
                enhanced_doc["source_type"] = metadata["source_type"]
            
            # Extract title from metadata if not already present
            if "title" in metadata and not enhanced_doc.get("title"):
                enhanced_doc["title"] = metadata["title"]
            
            # Try to extract from filename if present
            if "filename" in metadata and not enhanced_doc.get("source"):
                filename = metadata["filename"]
                enhanced_doc["source"] = os.path.basename(filename)
                
                # Use filename as title if no title exists
                if not enhanced_doc.get("title"):
                    name, _ = os.path.splitext(os.path.basename(filename))
                    enhanced_doc["title"] = name.replace('_', ' ').replace('-', ' ').title()
        
        # If no title found, try to create one from content
        if not enhanced_doc.get("title") and content_text:
            lines = content_text.strip().split("\n")
            first_line = lines[0] if lines else ""
            # Use first line as title if not too long
            if first_line and len(first_line) < 100:
                enhanced_doc["title"] = first_line
            else:
                # Use first 50 characters
                title = content_text[:50].replace('\n', ' ')
                if len(content_text) > 50:
                    title += "..."
                enhanced_doc["title"] = title
        
        # If still no title, use fallback
        if not enhanced_doc.get("title"):
            if "id" in enhanced_doc:
                enhanced_doc["title"] = f"Document {enhanced_doc['id']}"
            else:
                enhanced_doc["title"] = "Untitled Document"
        
        # Ensure source is set
        if not enhanced_doc.get("source"):
            if enhanced_doc.get("source_type"):
                enhanced_doc["source"] = f"{enhanced_doc['source_type']} document"
            else:
                source_path = doc.get("source", "")
                if source_path:
                    enhanced_doc["source"] = os.path.basename(source_path)
                else:
                    enhanced_doc["source"] = "Unknown source"
        
        # Check for similarity score
        if "similarity" in doc:
            enhanced_doc["similarity"] = doc["similarity"]
        elif "score" in doc:
            enhanced_doc["similarity"] = doc["score"]
        
        # Ensure document_id is set if available
        if "id" in doc and not enhanced_doc.get("id"):
            enhanced_doc["id"] = doc["id"]
        
        # Add debug info
        logger.debug(f"Enhanced document: title='{enhanced_doc.get('title')}', source='{enhanced_doc.get('source')}'")
        
        return enhanced_doc
    
    @staticmethod
    def deduplicate_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate documents from search results.
        
        Args:
            documents: List of documents that may contain duplicates
            
        Returns:
            List of documents with duplicates removed
        """
        unique_docs = []
        seen_sources = set()
        seen_titles = set()
        seen_docs = set()
        
        for doc in documents:
            # Get key identifying information
            title = doc.get("title", "")
            source = doc.get("source", "")
            content = ""
            
            # Try to extract content
            if "document" in doc and "content" in doc["document"]:
                content_obj = doc["document"]["content"]
                if isinstance(content_obj, dict):
                    # If content is a dict, create a hash of its values
                    content_hash = hash(frozenset({k: str(v)[:100] for k, v in content_obj.items()}.items()))
                elif isinstance(content_obj, str):
                    # If content is a string, use the first 100 chars
                    content_hash = hash(content_obj[:100])
                else:
                    content_hash = hash(str(content_obj)[:100])
            elif "content" in doc:
                content_obj = doc["content"]
                if isinstance(content_obj, dict):
                    content_hash = hash(frozenset({k: str(v)[:100] for k, v in content_obj.items()}.items()))
                elif isinstance(content_obj, str):
                    content_hash = hash(content_obj[:100])
                else:
                    content_hash = hash(str(content_obj)[:100])
            else:
                content_hash = 0
            
            # Create a unique signature for this document
            doc_signature = (title, source, content_hash)
            
            # Skip if we've seen this document before
            if (doc_signature in seen_docs or 
                (title and title in seen_titles and source in seen_sources)):
                logger.debug(f"Skipping duplicate document: '{title}' from '{source}'")
                continue
            
            # Add to unique documents
            unique_docs.append(doc)
            
            # Record that we've seen this document
            if title:
                seen_titles.add(title)
            if source:
                seen_sources.add(source)
            seen_docs.add(doc_signature)
        
        logger.info(f"Removed {len(documents) - len(unique_docs)} duplicate documents from search results")
        return unique_docs