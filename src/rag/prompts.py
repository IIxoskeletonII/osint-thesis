"""
Prompt templates for the OSINT RAG system.
This module provides templates for formatting queries and context
for the LLM to generate responses.
"""

import logging
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PromptTemplateManager:
    """
    Manager for creating and formatting prompt templates for the RAG system.
    """
    
    def __init__(self):
        """Initialize the prompt template manager."""
        logger.info("Initializing PromptTemplateManager")
    
    def format_rag_prompt(self, 
                        query: str, 
                        context_docs: List[Dict[str, Any]],
                        system_prompt: Optional[str] = None) -> Dict[str, str]:
        """
        Format a RAG prompt with query and context documents.
        
        Args:
            query: The user's query
            context_docs: List of retrieved context documents
            system_prompt: Optional custom system prompt
            
        Returns:
            Dictionary with formatted system and user prompts
        """
        # Format context from retrieved documents
        formatted_context = self._format_context_from_docs(context_docs)
        
        # Use default system prompt if none provided
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()
        
        # Format the user prompt with context and query
        user_prompt = self._format_user_prompt(query, formatted_context)
        
        logger.info(f"Formatted RAG prompt for query: '{query[:50]}...' with {len(context_docs)} context documents")
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def _format_context_from_docs(self, context_docs: List[Dict[str, Any]]) -> str:
        """
        Format retrieved documents into a context string.
        
        Args:
            context_docs: List of retrieved documents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, doc in enumerate(context_docs):
            # Extract document information safely based on the structure
            title = "Unknown Title"
            content = ""
            source_type = "unknown"
            source_name = "unknown"
            similarity = doc.get("similarity", 0.0)
            
            # Extract document content based on structure
            if "document" in doc:
                document = doc["document"]
                if "content" in document:
                    content_obj = document["content"]
                    title = content_obj.get("title", "Unknown Title")
                    
                    # Get the main content - could be in description, text, or content field
                    for field in ["description", "text", "content"]:
                        if field in content_obj and content_obj[field]:
                            content = content_obj[field]
                            break
                
                if "metadata" in document:
                    metadata = document["metadata"]
                    source_type = metadata.get("source_type", "unknown")
                    source_name = metadata.get("source_name", "unknown")
            
            # Format this document's context
            doc_context = f"[Document {i+1}: {title}]\n"
            doc_context += f"Source: {source_name} ({source_type})\n"
            doc_context += f"Relevance: {similarity:.2f}\n"
            doc_context += f"Content:\n{content[:800]}..." if len(content) > 800 else f"Content:\n{content}"
            doc_context += "\n\n"
            
            context_parts.append(doc_context)
        
        return "\n".join(context_parts)
    
    def _format_user_prompt(self, query: str, context: str) -> str:
        """
        Format the user prompt with query and context.
        
        Args:
            query: The user's query
            context: Formatted context string
            
        Returns:
            Formatted user prompt
        """
        return f"""
I need information about the following query:

Query: {query}

Here is the relevant context from the knowledge base:

{context}

Based on this context, please provide a comprehensive and accurate response to the query. 
Include relevant information from the provided context and cite your sources.
If the provided context doesn't contain sufficient information to answer the query,
acknowledge the limitations and provide the best possible response given the available information.
"""
    
    def _get_default_system_prompt(self) -> str:
        """
        Get the default system prompt for the RAG system.
        
        Returns:
            Default system prompt
        """
        return """
You are an expert OSINT (Open Source Intelligence) analyst specializing in cybersecurity intelligence.
Your task is to analyze the provided intelligence information and respond to queries with accurate, well-reasoned answers.

Guidelines:
1. Analyze the given context thoroughly before responding
2. Always cite your sources when providing information from the context
3. Maintain a professional and analytical tone
4. If the context doesn't contain sufficient information, acknowledge the limitations
5. Prioritize accuracy over comprehensiveness
6. Organize your response in a clear and structured manner
7. Focus on factual information rather than speculation
8. When dealing with technical content, ensure explanations are precise
9. Highlight connections between different pieces of information when relevant
10. Provide actionable insights when applicable

Your primary goal is to provide high-quality intelligence analysis based on the context provided.
"""