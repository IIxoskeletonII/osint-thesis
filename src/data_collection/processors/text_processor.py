"""Text processor for OSINT data."""

import re
import logging
from typing import Dict, Any, List, Optional

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)

class TextProcessor(BaseProcessor):
    """Processor for text normalization and cleaning."""
    
    def __init__(self, processor_name: str = "text_processor"):
        """
        Initialize the text processor.
        
        Args:
            processor_name: Identifier for the processor
        """
        super().__init__(processor_name)
    
    def process(self, document: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Process a document's text content.
        
        Args:
            document: Dictionary containing document content and metadata
            **kwargs: Additional parameters:
                - normalize_whitespace: Whether to normalize whitespace (default: True)
                - remove_urls: Whether to remove URLs (default: False)
                - remove_numbers: Whether to remove numbers (default: False)
                - lowercase: Whether to convert text to lowercase (default: False)
                - min_line_length: Minimum line length to retain (default: 0)
                
        Returns:
            Processed document
        """
        self.logger.info(f"Processing document with text processor")
        
        content = document.get("content", "")
        if not content:
            self.logger.warning("Document has no content to process")
            return document
        
        normalize_whitespace = kwargs.get('normalize_whitespace', True)
        remove_urls = kwargs.get('remove_urls', False)
        remove_numbers = kwargs.get('remove_numbers', False)
        lowercase = kwargs.get('lowercase', False)
        min_line_length = kwargs.get('min_line_length', 0)
        
        # Apply text processing steps
        processed_content = content
        
        if remove_urls:
            processed_content = self._remove_urls(processed_content)
            
        if remove_numbers:
            processed_content = self._remove_numbers(processed_content)
            
        if normalize_whitespace:
            processed_content = self._normalize_whitespace(processed_content)
            
        if lowercase:
            processed_content = processed_content.lower()
            
        if min_line_length > 0:
            processed_content = self._filter_short_lines(processed_content, min_line_length)
        
        # Calculate statistics about the processing
        original_length = len(content)
        processed_length = len(processed_content)
        char_reduction = original_length - processed_length
        
        processing_stats = {
            "original_length": original_length,
            "processed_length": processed_length,
            "char_reduction": char_reduction,
            "reduction_percentage": round((char_reduction / original_length * 100) if original_length > 0 else 0, 2)
        }
        
        # Update document with processed content
        processed_document = document.copy()
        processed_document["content"] = processed_content
        processed_document["metadata"] = self._update_metadata(
            document.get("metadata", {}),
            {"text_processing_stats": processing_stats}
        )
        
        return processed_document
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple whitespaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        
        # Remove whitespace at the beginning and end of each line
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text."""
        # Pattern for matching URLs
        url_pattern = r'https?://\S+|www\.\S+'
        return re.sub(url_pattern, '', text)
    
    def _remove_numbers(self, text: str) -> str:
        """Remove standalone numbers from text."""
        # Replace numbers that are not part of words
        return re.sub(r'\b\d+\b', '', text)
    
    def _filter_short_lines(self, text: str, min_length: int) -> str:
        """Filter out lines shorter than the minimum length."""
        lines = text.split('\n')
        filtered_lines = [line for line in lines if len(line.strip()) >= min_length]
        return '\n'.join(filtered_lines)