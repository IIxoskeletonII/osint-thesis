"""
RAG Pipeline implementation for the OSINT system.
This module combines retrieval, context formatting, and LLM generation
to create a complete RAG system.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union

import anthropic
from anthropic import Anthropic

from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager
from src.rag.retriever import BasicRetriever
from src.rag.prompts import PromptTemplateManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RagPipeline:
    """
    Retrieval-Augmented Generation pipeline for the OSINT system.
    Combines retrieval, context formatting, and LLM generation.
    """
    
    def __init__(self, 
                knowledge_base_manager: KnowledgeBaseManager,
                api_key: Optional[str] = None,
                model: str = "claude-3-7-sonnet-20250219",
                top_k: int = 3,
                temperature: float = 0.2,
                max_tokens: int = 1024):
        """
        Initialize the RAG pipeline.
        
        Args:
            knowledge_base_manager: Knowledge base manager instance
            api_key: Anthropic API key (defaults to environment variable)
            model: LLM model to use
            top_k: Number of documents to retrieve
            temperature: Temperature for generation
            max_tokens: Maximum number of tokens to generate
        """
        self.knowledge_base_manager = knowledge_base_manager
        self.retriever = BasicRetriever(knowledge_base_manager, top_k=top_k)
        self.prompt_manager = PromptTemplateManager()
        
        # Initialize the Anthropic client
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("No Anthropic API key provided. The generate method will fail without an API key.")
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        logger.info(f"Initialized RAG Pipeline with model {model}, top_k={top_k}")
    
    def process_query(self, 
                     query: str, 
                     filters: Optional[Dict[str, Any]] = None,
                     custom_system_prompt: Optional[str] = None,
                     generate: bool = True) -> Dict[str, Any]:
        """
        Process a query through the complete RAG pipeline.
        
        Args:
            query: User query
            filters: Optional filters for retrieval
            custom_system_prompt: Optional custom system prompt
            generate: Whether to generate a response (requires API key)
            
        Returns:
            Dictionary with retrieval results, prompt, and optionally the generated response
        """
        logger.info(f"Processing query: '{query}'")
        
        # Step 1: Retrieve relevant documents
        retrieved_docs = self.retriever.retrieve(query, filters)
        
        # Improve docs to ensure they have source info
        self._improve_doc_sources(retrieved_docs)
        
        logger.info(f"Retrieved {len(retrieved_docs)} documents")
        
        # Step 2: Format the prompt with context
        prompt = self.prompt_manager.format_rag_prompt(query, retrieved_docs, custom_system_prompt)
        
        # Prepare the result
        result = {
            "query": query,
            "retrieved_documents": retrieved_docs,
            "prompt": prompt
        }
        
        # Step 3: Generate response if requested
        if generate:
            if not self.api_key:
                logger.error("Cannot generate response: No API key provided")
                result["error"] = "No API key provided for generation"
            else:
                try:
                    response = self._generate_response(prompt)
                    result["response"] = response
                except Exception as e:
                    logger.error(f"Error generating response: {str(e)}")
                    result["error"] = f"Error generating response: {str(e)}"
        
        return result
    
    def _improve_doc_sources(self, documents: List[Dict[str, Any]]) -> None:
        """
        Improve source information in documents.
        
        Args:
            documents: List of documents to improve
        """
        for doc in documents:
            # Check if source is missing or unknown
            if not doc.get("source") or doc.get("source") == "Unknown source":
                # Try to get source from metadata
                if "metadata" in doc:
                    metadata = doc["metadata"]
                    if "source" in metadata:
                        doc["source"] = metadata["source"]
                    elif "filename" in metadata:
                        doc["source"] = os.path.basename(metadata["filename"])
                
                # Try to get source from document field
                if not doc.get("source") and "document" in doc:
                    document = doc["document"]
                    if "metadata" in document:
                        metadata = document["metadata"]
                        if "source" in metadata:
                            doc["source"] = metadata["source"]
                        elif "filename" in metadata:
                            doc["source"] = os.path.basename(metadata["filename"])
                            
                # If source looks like a filepath, extract just the filename
                if doc.get("source") and ('/' in doc["source"] or '\\' in doc["source"]):
                    doc["source"] = os.path.basename(doc["source"])
    
    def _generate_response(self, prompt: Dict[str, str]) -> str:
        """
        Generate a response using the Anthropic API.
        
        Args:
            prompt: Formatted prompt with system and user messages
            
        Returns:
            Generated response text
        """
        try:
            client = Anthropic(api_key=self.api_key)
            
            message = client.messages.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                system=prompt["system"],
                messages=[
                    {"role": "user", "content": prompt["user"]}
                ]
            )
            
            response_text = message.content[0].text
            logger.info(f"Generated response with {len(response_text)} characters")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {str(e)}")
            raise