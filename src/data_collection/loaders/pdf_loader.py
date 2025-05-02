"""PDF document loader for OSINT data sources."""

import os
import logging
from typing import Dict, Any, List, Optional

import PyPDF2

# Use direct relative import
from .base_loader import BaseLoader

logger = logging.getLogger(__name__)

class PDFLoader(BaseLoader):
    """Loader for PDF documents."""
    
    def __init__(self, source_name: str = "pdf_document"):
        """
        Initialize the PDF loader.
        
        Args:
            source_name: Identifier for the source being loaded
        """
        super().__init__(source_name)
    
    def load(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """
        Load a PDF document from the specified path.
        
        Args:
            source_path: Path to the PDF file
            **kwargs: Additional parameters:
                - page_numbers: Optional list of page numbers to extract
                
        Returns:
            Dictionary containing the document content and metadata
        """
        logger.info(f"Loading PDF from {source_path}")
        
        if not os.path.exists(source_path):
            logger.error(f"PDF file not found: {source_path}")
            raise FileNotFoundError(f"PDF file not found: {source_path}")
            
        page_numbers = kwargs.get('page_numbers', None)
        
        try:
            with open(source_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                info = reader.metadata
                additional_metadata = {
                    "title": info.title if info and info.title else os.path.basename(source_path),
                    "author": info.author if info and info.author else "Unknown",
                    "page_count": len(reader.pages)
                }
                
                # Extract content
                if page_numbers:
                    content = self._extract_specific_pages(reader, page_numbers)
                else:
                    content = self._extract_all_pages(reader)
                
                return {
                    "content": content,
                    "metadata": self._create_metadata(source_path, additional_metadata)
                }
                
        except Exception as e:
            logger.error(f"Error loading PDF {source_path}: {str(e)}")
            raise
    
    def _extract_all_pages(self, reader: PyPDF2.PdfReader) -> str:
        """Extract text from all pages in the PDF."""
        text = ""
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {i+1} ---\n{page_text}"
            except Exception as e:
                logger.warning(f"Could not extract text from page {i+1}: {str(e)}")
        
        return text
    
    def _extract_specific_pages(self, reader: PyPDF2.PdfReader, page_numbers: List[int]) -> str:
        """Extract text from specific pages in the PDF."""
        text = ""
        for page_num in page_numbers:
            if 0 <= page_num < len(reader.pages):
                try:
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num+1} ---\n{page_text}"
                except Exception as e:
                    logger.warning(f"Could not extract text from page {page_num+1}: {str(e)}")
            else:
                logger.warning(f"Page number {page_num+1} out of range")
        
        return text
    
    def _get_source_type(self) -> str:
        """Get the source type."""
        return "pdf"