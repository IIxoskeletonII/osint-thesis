"""
Embedding generation for OSINT knowledge base.
This module provides functionality to convert text chunks into vector embeddings,
with optional domain adaptation for security contexts.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Union, Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Base class for embedding generation."""
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.
        
        Args:
            text (str): Text to embed
            
        Returns:
            List[float]: Embedding vector
        """
        raise NotImplementedError("Subclasses must implement generate_embedding")
    
    def generate_embeddings_for_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of document chunks.
        
        Args:
            chunks (List[Dict]): Document chunks to embed
            
        Returns:
            List[Dict]: Chunks with embeddings added
        """
        raise NotImplementedError("Subclasses must implement generate_embeddings_for_chunks")


class SimpleEmbeddingGenerator(EmbeddingGenerator):
    """
    A basic embedding generator using sentence-transformers models.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize with a specific embedding model.
        
        Args:
            model_name (str): Name of the sentence-transformers model to use
        """
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Initialized embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_name}: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.
        
        Args:
            text (str): Text to embed
            
        Returns:
            List[float]: Embedding vector
        """
        if not text:
            logger.warning("Attempted to embed empty text")
            # Return zero vector with same dimensions as model output
            return [0.0] * self.model.get_sentence_embedding_dimension()
        
        try:
            # Generate embedding
            embedding = self.model.encode(text)
            
            # Convert to list of floats for JSON serialization
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector with same dimensions as model output
            return [0.0] * self.model.get_sentence_embedding_dimension()
    
    def generate_embeddings_for_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of document chunks.
        
        Args:
            chunks (List[Dict]): Document chunks to embed
            
        Returns:
            List[Dict]: Chunks with embeddings added
        """
        embedded_chunks = []
        
        for chunk in chunks:
            # Extract text content from the chunk
            text = self._extract_text_from_chunk(chunk)
            
            # Generate embedding
            embedding = self.generate_embedding(text)
            
            # Add embedding to chunk metadata
            chunk_with_embedding = chunk.copy()
            chunk_with_embedding["metadata"]["embedding"] = embedding
            
            embedded_chunks.append(chunk_with_embedding)
        
        logger.info(f"Generated embeddings for {len(chunks)} chunks")
        return embedded_chunks
    
    def _extract_text_from_chunk(self, chunk: Dict[str, Any]) -> str:
        """
        Extract the text content from a chunk document.
        
        Args:
            chunk (Dict): Document chunk
            
        Returns:
            str: Text content for embedding
        """
        if 'content' not in chunk:
            logger.warning(f"No content found in chunk with keys: {list(chunk.keys())}")
            return ""
        
        content = chunk["content"]
        
        # Debug the content structure
        logger.debug(f"Extracting text from content with keys: {list(content.keys())}")
        
        # Initialize text parts list
        text_parts = []
        
        # Extract title
        if "title" in content and content["title"]:
            text_parts.append(content["title"])
            logger.debug(f"Added title: {content['title']}")
        
        # Extract description (main content for most documents)
        if "description" in content and content["description"]:
            text_parts.append(content["description"])
            logger.debug(f"Added description ({len(content['description'])} chars)")
        
        # Extract other potential content fields
        for field in ["summary", "text", "content"]:
            if field in content and content[field] and isinstance(content[field], str):
                text_parts.append(content[field])
                logger.debug(f"Added {field} ({len(content[field])} chars)")
        
        # Combine all text parts
        full_text = " ".join(text_parts)
        
        # If still empty, try a more comprehensive approach
        if not full_text:
            logger.warning("No standard fields found, trying all string fields")
            for key, value in content.items():
                if isinstance(value, str) and value.strip():
                    text_parts.append(value)
                    logger.debug(f"Added {key} ({len(value)} chars)")
            
            full_text = " ".join(text_parts)
        
        if not full_text:
            logger.warning(f"Failed to extract any text from content")
        else:
            logger.debug(f"Extracted {len(full_text)} characters of text")
        
        return full_text

class SecurityEmbeddingGenerator(SimpleEmbeddingGenerator):
    """
    A security-focused embedding generator with domain adaptation.
    Applies security-specific prefixing to improve embedding quality.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize with parent class parameters."""
        super().__init__(model_name)
        
        # Define security domain prefixes for different content types
        self.domain_prefixes = {
            "vulnerability": "security vulnerability: ",
            "malware": "malware analysis: ",
            "threat": "threat intelligence: ",
            "attack": "attack technique: ",
            "research": "security research: "
        }
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding with security domain adaptation.
        
        Args:
            text (str): Text to embed
            
        Returns:
            List[float]: Embedding vector
        """
        if not text:
            return super().generate_embedding(text)
        
        # Apply domain-specific prefix based on content
        adapted_text = self._apply_domain_adaptation(text)
        
        # Generate embedding using the adapted text
        return super().generate_embedding(adapted_text)
    
    def _apply_domain_adaptation(self, text: str) -> str:
        """
        Apply domain-specific adaptation based on text content.
        
        Args:
            text (str): Original text
            
        Returns:
            str: Adapted text with appropriate prefix
        """
        text_lower = text.lower()
        
        # Check for security-related keywords to determine appropriate prefix
        for domain, prefix in self.domain_prefixes.items():
            if domain in text_lower:
                return prefix + text
        
        # Default prefix if no specific domain is detected
        if any(term in text_lower for term in ["security", "cyber", "hack", "breach"]):
            return "cybersecurity context: " + text
        
        # No adaptation for non-security content
        return text


# Factory function to get appropriate embedding generator
def get_embedding_generator(generator_type: str = "simple", 
                           model_name: str = "all-MiniLM-L6-v2") -> EmbeddingGenerator:
    """
    Factory function to get the appropriate embedding generator.
    
    Args:
        generator_type (str): Type of generator ("simple" or "security")
        model_name (str): Name of the embedding model to use
        
    Returns:
        EmbeddingGenerator: An instance of the specified generator
    """
    if generator_type.lower() == "security":
        return SecurityEmbeddingGenerator(model_name)
    else:
        return SimpleEmbeddingGenerator(model_name)