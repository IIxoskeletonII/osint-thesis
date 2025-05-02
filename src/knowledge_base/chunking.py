"""
Document chunking strategies for the OSINT knowledge base.
This module provides different ways to split documents into chunks
for more effective retrieval and processing.
"""
import logging
logger = logging.getLogger(__name__)
import re
from typing import List, Dict, Any, Optional
import copy

class DocumentChunker:
    """Base class for document chunking strategies."""
    
    def chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split a document into chunks based on the implemented strategy.
        
        Args:
            document (Dict): The document to chunk
            
        Returns:
            List[Dict]: List of document chunks with metadata
        """
        raise NotImplementedError("Subclasses must implement chunk_document")


class SimpleChunker(DocumentChunker):
    """
    A straightforward chunking strategy that splits text by paragraphs
    or a maximum character limit, while preserving metadata.
    """
    
    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100):
        """
        Initialize the chunker with size parameters.
        
        Args:
            max_chunk_size (int): Maximum size of each chunk in characters
            overlap (int): Number of characters to overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
    
    def chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split a document into chunks based on paragraphs and size limits.
        
        Args:
            document (Dict): The document to chunk
            
        Returns:
            List[Dict]: List of document chunks with metadata
        """
        chunks = []
        
        # Ensure document has proper structure
        if "metadata" not in document or "content" not in document:
            logger.error(f"Invalid document structure: missing metadata or content")
            return [document]  # Return document as is to avoid errors
        
        doc_id = document["metadata"]["id"]
        content = document["content"]
        
        logger.info(f"Chunking document with content keys: {list(content.keys())}")
        
        # Extract the text content based on document structure
        text_content = self._extract_text_content(content)
        
        if not text_content:
            # If no suitable text found, return the document as a single chunk
            logger.warning(f"Failed to extract text from document {doc_id}")
            document_copy = copy.deepcopy(document)
            document_copy["metadata"]["chunk_id"] = f"{doc_id}-0"
            document_copy["metadata"]["is_chunk"] = True
            document_copy["metadata"]["chunk_index"] = 0
            document_copy["metadata"]["total_chunks"] = 1
            return [document_copy]
    

        
        # Split text by paragraphs first
        paragraphs = self._split_into_paragraphs(text_content)
        
        # Combine paragraphs into chunks of appropriate size
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed max size and we already have content,
            # create a new chunk
            if len(current_chunk) + len(paragraph) > self.max_chunk_size and current_chunk:
                chunk_doc = self._create_chunk_document(
                    document, current_chunk, doc_id, chunk_index)
                chunks.append(chunk_doc)
                
                # Start new chunk with overlap
                if len(current_chunk) > self.overlap:
                    overlap_text = current_chunk[-self.overlap:]
                    current_chunk = overlap_text + paragraph
                else:
                    current_chunk = paragraph
                    
                chunk_index += 1
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the final chunk if there's content left
        if current_chunk:
            chunk_doc = self._create_chunk_document(
                document, current_chunk, doc_id, chunk_index)
            chunks.append(chunk_doc)
        
        # Update total chunks count in metadata
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = len(chunks)
        
        return chunks
    
    def _extract_text_content(self, content: Dict[str, Any]) -> str:
        """
        Extract the main text content from a document based on its structure.
        
        Args:
            content (Dict): The document content
            
        Returns:
            str: Extracted text content
        """
        # Debug the content structure
        logger.info(f"Extracting content from keys: {list(content.keys())}")
        
        # Initialize text parts list
        text_parts = []
        
        # Extract title
        if "title" in content and isinstance(content["title"], str):
            text_parts.append(content["title"])
            logger.info(f"Added title: {content['title']}")
        
        # Extract description (main content for most documents)
        if "description" in content and isinstance(content["description"], str):
            text_parts.append(content["description"])
            desc_length = len(content["description"])
            logger.info(f"Added description ({desc_length} chars)")
        
        # Extract other potential content fields
        for field in ["summary", "text", "content"]:
            if field in content and isinstance(content[field], str) and content[field].strip():
                text_parts.append(content[field])
                logger.info(f"Added {field} ({len(content[field])} chars)")
        
        # Combine all text parts
        full_text = "\n\n".join(text_parts)
        
        # If still empty, try a more comprehensive approach
        if not full_text:
            logger.warning("No standard fields found, trying all string fields")
            for key, value in content.items():
                if isinstance(value, str) and len(value) > 20 and value.strip():  # Only include substantial text
                    text_parts.append(value)
                    logger.info(f"Added {key} ({len(value)} chars)")
            
            full_text = "\n\n".join(text_parts)
        
        if not full_text:
            logger.warning(f"Failed to extract any text from content")
        else:
            logger.info(f"Extracted {len(full_text)} characters of text")
        
        return full_text
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs.
        
        Args:
            text (str): Text to split
            
        Returns:
            List[str]: List of paragraphs
        """
        # Split by double newlines to separate paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Filter out empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return paragraphs
    
    def _create_chunk_document(self, original_doc: Dict[str, Any], 
                              chunk_text: str, doc_id: str, 
                              chunk_index: int) -> Dict[str, Any]:
        """
        Create a new document for a chunk with appropriate metadata.
        
        Args:
            original_doc (Dict): The original document
            chunk_text (str): The chunk text
            doc_id (str): The original document ID
            chunk_index (int): The index of this chunk
            
        Returns:
            Dict: A new document representing the chunk
        """
        # Create a shallow copy of the original document
        chunk_doc = {
            "content": {},
            "metadata": original_doc["metadata"].copy()
        }
        
        # Update metadata for the chunk
        chunk_doc["metadata"]["chunk_id"] = f"{doc_id}-{chunk_index}"
        chunk_doc["metadata"]["is_chunk"] = True
        chunk_doc["metadata"]["chunk_index"] = chunk_index
        chunk_doc["metadata"]["original_doc_id"] = doc_id
        
        # Create content structure based on original document type
        original_content = original_doc["content"]
        if "title" in original_content:
            # Preserve the title if it exists
            chunk_doc["content"]["title"] = original_content["title"]
            
            # Add chunk indicator to title
            chunk_doc["content"]["title"] += f" (Part {chunk_index + 1})"
        
        # Set the main text content based on document type
        if "description" in original_content:
            chunk_doc["content"]["description"] = chunk_text
        elif "summary" in original_content:
            chunk_doc["content"]["summary"] = chunk_text
        else:
            chunk_doc["content"]["text"] = chunk_text
        
        # Preserve other important fields from original content
        for key in ["source", "date", "author", "url"]:
            if key in original_content:
                chunk_doc["content"][key] = original_content[key]
        
        return chunk_doc


class SecurityAwareChunker(SimpleChunker):
    """
    A security-focused chunking strategy that preserves the context
    of security-related entities and concepts.
    """
    
    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100):
        """Initialize with parent class parameters."""
        super().__init__(max_chunk_size, overlap)
        # Security-related terms that shouldn't be split across chunks
        self.security_terms = [
            "CVE-", "vulnerability", "exploit", "malware", "ransomware",
            "attack", "threat actor", "APT", "zero-day", "injection",
            "XSS", "CSRF", "buffer overflow", "privilege escalation"
        ]
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs while preserving security context.
        
        Args:
            text (str): Text to split
            
        Returns:
            List[str]: List of security-aware paragraphs
        """
        # Get initial paragraphs from parent method
        paragraphs = super()._split_into_paragraphs(text)
        
        # Check if security terms are split across paragraphs
        result_paragraphs = []
        buffer = ""
        
        for i, paragraph in enumerate(paragraphs):
            # Check if current paragraph ends with partial security term
            should_combine = False
            
            for term in self.security_terms:
                # Look for partial security terms at paragraph boundaries
                if i < len(paragraphs) - 1:  # Not the last paragraph
                    combined = paragraph + " " + paragraphs[i+1]
                    for t in self.security_terms:
                        if t in combined and t not in paragraph and t not in paragraphs[i+1]:
                            should_combine = True
                            break
            
            if should_combine:
                # Add to buffer to combine with next paragraph
                if buffer:
                    buffer += "\n\n" + paragraph
                else:
                    buffer = paragraph
            else:
                # Add buffer + current paragraph if buffer exists
                if buffer:
                    result_paragraphs.append(buffer + "\n\n" + paragraph)
                    buffer = ""
                else:
                    result_paragraphs.append(paragraph)
        
        # Add any remaining buffer
        if buffer:
            result_paragraphs.append(buffer)
        
        return result_paragraphs


# Factory function to get appropriate chunker
def get_chunker(chunker_type: str = "simple", 
                max_chunk_size: int = 1000, 
                overlap: int = 100) -> DocumentChunker:
    """
    Factory function to get the appropriate chunker based on type.
    
    Args:
        chunker_type (str): Type of chunker ("simple" or "security")
        max_chunk_size (int): Maximum chunk size in characters
        overlap (int): Character overlap between chunks
        
    Returns:
        DocumentChunker: An instance of the specified chunker
    """
    if chunker_type.lower() == "security":
        return SecurityAwareChunker(max_chunk_size, overlap)
    else:
        return SimpleChunker(max_chunk_size, overlap)