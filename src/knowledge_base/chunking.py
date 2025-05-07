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
        
        if "metadata" not in document or "content" not in document:
            logger.error(f"Invalid document structure: missing metadata or content")
            return [document] 
        
        doc_id = document["metadata"]["id"]
        content = document["content"]
        
        logger.info(f"Chunking document with content keys: {list(content.keys())}")
        
        text_content = self._extract_text_content(content)
        
        if not text_content:
            logger.warning(f"Failed to extract text from document {doc_id}")
            document_copy = copy.deepcopy(document)
            # Ensure essential chunk metadata is present even for unchunkable docs
            document_copy["metadata"]["chunk_id"] = f"{doc_id}-0"
            document_copy["metadata"]["is_chunk"] = True # Treat as a single chunk
            document_copy["metadata"]["chunk_index"] = 0
            document_copy["metadata"]["total_chunks"] = 1
            # Add original document path to this single chunk's metadata
            if "path" in document["metadata"]:
                document_copy["metadata"]["original_document_path"] = document["metadata"]["path"]
            return [document_copy]
    
        paragraphs = self._split_into_paragraphs(text_content)
        current_chunk_text = "" # Renamed for clarity
        chunk_index = 0
        
        for paragraph in paragraphs:
            if len(current_chunk_text) + len(paragraph) + 2 > self.max_chunk_size and current_chunk_text: # +2 for potential \n\n
                chunk_doc = self._create_chunk_document(
                    document, current_chunk_text, doc_id, chunk_index)
                chunks.append(chunk_doc)
                
                if len(current_chunk_text) > self.overlap:
                    overlap_text = current_chunk_text[-self.overlap:]
                    current_chunk_text = overlap_text.rsplit(' ', 1)[0] + " " # Try to cut at word boundary
                    current_chunk_text += paragraph 
                else:
                    current_chunk_text = paragraph
                chunk_index += 1
            else:
                if current_chunk_text:
                    current_chunk_text += "\n\n" + paragraph
                else:
                    current_chunk_text = paragraph
        
        if current_chunk_text:
            chunk_doc = self._create_chunk_document(
                document, current_chunk_text, doc_id, chunk_index)
            chunks.append(chunk_doc)
        
        for i, chunk in enumerate(chunks): # Re-iterate to set correct total_chunks for all
            chunk["metadata"]["total_chunks"] = len(chunks)
            chunk["metadata"]["chunk_index"] = i # Ensure chunk_index is sequential after all processing
            # Re-generate chunk_id based on final index if necessary, though initial one should be fine
            # chunk["metadata"]["id"] = f"{doc_id}-{i}" 
            # chunk["metadata"]["chunk_id"] = f"{doc_id}-{i}"

        if not chunks and text_content: # If paragraphs were empty but text_content was not
            logger.warning(f"No chunks created from non-empty text_content for doc {doc_id}. Creating one large chunk.")
            chunk_doc = self._create_chunk_document(document, text_content, doc_id, 0)
            chunk_doc["metadata"]["total_chunks"] = 1
            chunks.append(chunk_doc)
            
        return chunks
    
    def _extract_text_content(self, content: Dict[str, Any]) -> str:
        logger.debug(f"Extracting content from keys: {list(content.keys())}")
        text_parts = []
        
        if "title" in content and isinstance(content["title"], str):
            text_parts.append(content["title"])
        
        # Prioritize 'description', then 'summary', then 'text', then 'content' (as a string value)
        preferred_fields = ["description", "summary", "abstract", "text", "content_text"] # Added more common fields
        
        main_content_found = False
        for field in preferred_fields:
            if field in content and isinstance(content[field], str) and content[field].strip():
                text_parts.append(content[field])
                main_content_found = True
                logger.debug(f"Added primary content from field: {field}")
                break # Take the first one found from the preferred list
        
        # If no primary field found, concatenate all other string values
        if not main_content_found:
            logger.debug("No primary content field found, concatenating all string values.")
            temp_parts = []
            for key, value in content.items():
                if key == "title": continue # Already added
                if isinstance(value, str) and value.strip():
                    temp_parts.append(value) # Just the value, not "Key: Value"
                elif isinstance(value, list) and all(isinstance(item, str) for item in value):
                    temp_parts.append(" ".join(value))
            if temp_parts:
                text_parts.extend(temp_parts)
        
        full_text = "\n\n".join(part.strip() for part in text_parts if part.strip())
        
        if not full_text:
            logger.warning(f"Failed to extract any text from content dict: {content}")
        else:
            logger.debug(f"Extracted {len(full_text)} characters of text")
        
        return full_text
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return paragraphs
    
    def _create_chunk_document(self, original_doc: Dict[str, Any],
                            chunk_text: str, doc_id: str,
                            chunk_index: int) -> Dict[str, Any]:
        base_metadata = original_doc["metadata"].copy()
        unique_chunk_id = f"{doc_id}-{chunk_index}"

        chunk_metadata = {
            **base_metadata,
            "id": unique_chunk_id,
            "chunk_id": unique_chunk_id,
            "is_chunk": True,
            "chunk_index": chunk_index, # Will be updated later if total_chunks changes logic
            "original_doc_id": doc_id,
            "embedding": None 
        }
        if "path" in original_doc["metadata"]:
            chunk_metadata["original_document_path"] = original_doc["metadata"]["path"]
        else:
            logger.warning(f"Original document {doc_id} metadata is missing 'path'. Chunk 'original_document_path' will be missing.")

        chunk_metadata = {k: v for k, v in chunk_metadata.items() if v is not None}

        chunk_content = {}
        original_content_fields = original_doc.get("content", {})

        if "title" in original_content_fields:
            chunk_content["title"] = original_content_fields["title"] + f" (Part {chunk_index + 1})"
        else:
            chunk_content["title"] = f"Chunk {chunk_index + 1} of {doc_id}"
        
        # The main text of the chunk is chunk_text
        # We can store it in a consistent field, e.g., "text_content" or "description"
        chunk_content["description"] = chunk_text 

        # Preserve other relevant metadata-like fields from original content if they exist
        # These are less about the chunk's text and more about the original doc's context
        for key in ["author", "date", "url", "cve_id", "attack_id", "source_type_from_content"]: # Example fields
            if key in original_content_fields:
                chunk_content[key] = original_content_fields[key]
        
        chunk_doc = {
            "content": chunk_content,
            "metadata": chunk_metadata
        }
        return chunk_doc


class SecurityAwareChunker(SimpleChunker):
    """
    A security-focused chunking strategy that preserves the context
    of security-related entities and concepts.
    """
    
    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100):
        super().__init__(max_chunk_size, overlap)
        self.security_terms = [
            "CVE-", "vulnerability", "exploit", "malware", "ransomware",
            "attack", "threat actor", "APT", "zero-day", "injection",
            "XSS", "CSRF", "buffer overflow", "privilege escalation"
        ]
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        paragraphs = super()._split_into_paragraphs(text)
        
        
        result_paragraphs = []
        buffer = ""
        
        for i, paragraph in enumerate(paragraphs):
            should_combine = False
            if i < len(paragraphs) - 1:
                # A simpler check: if a term starts at the end of current paragraph and continues in next
                for term in self.security_terms:
                    # Check if current para ends with start of term and next para starts with rest of term
                    for k in range(1, len(term)):
                        if paragraph.endswith(term[:k]) and paragraphs[i+1].startswith(term[k:]):
                            should_combine = True
                            break
                    if should_combine:
                        break
            
            if should_combine:
                if buffer:
                    buffer += "\n\n" + paragraph
                else:
                    buffer = paragraph
            else:
                if buffer:
                    result_paragraphs.append(buffer + "\n\n" + paragraph)
                    buffer = ""
                else:
                    result_paragraphs.append(paragraph)
        
        if buffer:
            result_paragraphs.append(buffer)
        
        return result_paragraphs


def get_chunker(chunker_type: str = "simple", 
                max_chunk_size: int = 1000, 
                overlap: int = 100) -> DocumentChunker:
    if chunker_type.lower() == "security":
        logger.info(f"Using SecurityAwareChunker with max_size={max_chunk_size}, overlap={overlap}")
        return SecurityAwareChunker(max_chunk_size, overlap)
    else:
        logger.info(f"Using SimpleChunker with max_size={max_chunk_size}, overlap={overlap}")
        return SimpleChunker(max_chunk_size, overlap)