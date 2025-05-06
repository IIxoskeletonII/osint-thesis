import logging
from typing import Dict, Any, List, Optional
import random # For varied greetings
import os # For _extract_filename
import re # For cleaning response text in agent handler

from .agent_response_handler import AgentResponseHandler

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """
    Generates responses for the OSINT chatbot based on query results.
    Handles formatting, citation, and response assembly.
    """
    
    def __init__(self, claude_service=None):
        """
        Initialize the response generator.
        
        Args:
            claude_service: Service for generating responses with Claude
        """
        self.claude_service = claude_service
        self.agent_response_handler = AgentResponseHandler() # Instantiated here
        logger.info("ResponseGenerator initialized")

    def generate_greeting_response(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a simple greeting response.
        """
        greetings = [
            "Hello! How can I assist you with your OSINT research today?",
            "Hi there! What cybersecurity intelligence can I help you with?",
            "Greetings! I'm OSINT CyberVision, ready for your OSINT queries.",
            "Hello! I'm the OSINT Intelligence System, ready to help."
        ]
        return {
            "response": random.choice(greetings),
            "type": "greeting",
            "confidence": 1.0,
            "sources": []
        }
    
    def generate_response(self, 
                          query_result: Dict[str, Any], 
                          rag_result: Optional[Dict[str, Any]] = None,
                          agent_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a response based on the query results.
        """
        if query_result.get("query_type") == "greeting":
            return self.generate_greeting_response(query_result)

        if agent_result:
            if agent_result.get("status") == "error": # Check if agent itself had an error
                 return {
                    "response": f"Agent execution failed: {agent_result.get('error', 'Unknown agent error')}",
                    "type": "error",
                    "confidence": 0.1,
                    "sources": ["Agent Execution Error"]
                }
            return self.agent_response_handler.format_agent_response(agent_result)
        elif rag_result:
            if rag_result.get("error"): # Check if RAG itself had an error
                return {
                    "response": f"Knowledge base search failed: {rag_result.get('error', 'Unknown RAG error')}",
                    "type": "error",
                    "confidence": 0.1,
                    "sources": ["RAG Pipeline Error"]
                }
            if self._is_rag_result_useful(rag_result):
                return self._format_rag_response(query_result, rag_result)
            else:
                logger.info("RAG result not useful or empty, falling back to Claude general knowledge.")
                return self._generate_claude_fallback(query_result)
        else:
            logger.info("No agent or RAG result, generating Claude fallback.")
            return self._generate_claude_fallback(query_result)
    
    def _is_rag_result_useful(self, rag_result: Dict[str, Any]) -> bool:
        """
        Determine if the RAG result contains useful information.
        """
        if not rag_result or "error" in rag_result:
            return False
            
        if "response" not in rag_result or not rag_result["response"]:
            return False
            
        response_text = rag_result.get("response", "").lower()
        
        no_info_indicators = [
            "couldn't find specific information", "don't have information",
            "no information available", "insufficient information",
            "no relevant information", "couldn't retrieve information",
            "couldn't find any relevant", "i don't have access to information about that",
            "the provided context does not contain information", "context does not mention"
        ]
        
        if any(indicator in response_text for indicator in no_info_indicators):
            return False
            
        # Consider low confidence as not useful if LLM also indicates lack of info
        confidence = rag_result.get("confidence", 0.5)
        if confidence < 0.4 and any(indicator in response_text for indicator in ["i'm not sure", "it's unclear", "i cannot determine"]):
            return False
            
        return True
    
    def _generate_claude_fallback(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a fallback response using Claude when knowledge base lacks information or RAG fails.
        """
        if not self.claude_service:
            logger.warning("Claude service not available for fallback. Using generic fallback.")
            return self._generate_generic_fallback_response(query_result)
            
        original_query = query_result.get("original_query", "")
        enhanced_query = query_result.get("enhanced_query", original_query)
        
        logger.info(f"Generating Claude fallback response for: '{enhanced_query}'")
        
        try:
            prompt = f"""
            As an OSINT and cybersecurity intelligence assistant, please answer the following query 
            using your general knowledge. Our specialized knowledge base did not provide a sufficient answer.
            
            Query: {enhanced_query}
            
            Please provide a comprehensive, accurate response. If the query is about cybersecurity, 
            include relevant technical details, methodologies, or best practices. 
            If the query is outside typical cybersecurity domains, provide a helpful general response.
            Acknowledge if you are using general knowledge and cannot provide information from specific internal documents.
            """
            
            response_text = self.claude_service.generate(prompt, max_tokens=1000, temperature=0.5) # Adjusted parameters
            
            return {
                "response": response_text,
                "type": "claude_fallback",
                "confidence": 0.55, # Slightly higher than generic fallback
                "sources": ["Claude General Knowledge"]
            }
            
        except Exception as e:
            logger.error(f"Error generating Claude fallback: {str(e)}", exc_info=True)
            return self._generate_generic_fallback_response(query_result, error_message=str(e))

    def _generate_generic_fallback_response(self, query_result: Dict[str, Any], error_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a generic fallback response when Claude is also unavailable or fails.
        """
        original_query = query_result.get("original_query", "your query")
        response_text = f"I am currently unable to find specific information for '{original_query}' from my knowledge base or generate a general response."
        if error_message:
            response_text += f"\nDetails: {error_message}"
        response_text += "\n\nPlease try rephrasing your query or ask about a different topic."
        
        return {
            "response": response_text,
            "type": "fallback_error", # More specific type
            "confidence": 0.1,
            "sources": ["System Fallback"]
        }

    def _format_rag_response(self, query_result: Dict[str, Any], rag_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a response based on RAG results.
        """
        response_text = rag_result.get("response", "No response generated from the knowledge base.")
        documents = rag_result.get("retrieved_documents", []) # Corrected key
        
        formatted_sources = []
        for doc_data in documents: # Iterate through the list of document dicts
            # The actual document content and metadata might be nested
            doc = doc_data.get("document", doc_data) # Handle both flat and nested structures
            
            doc_title = self._extract_doc_title(doc)
            doc_source_name = self._extract_doc_source_name(doc) # Use new helper
            doc_score = doc_data.get("similarity", doc_data.get("score", 0.0)) # Get score from the outer dict
            
            source_display = f"{doc_title}"
            if doc_source_name and doc_source_name.lower() != doc_title.lower().replace(".json","").replace(".txt",""):
                 source_display += f" (Source File: {doc_source_name})"
            source_display += f" - Relevance: {doc_score:.2f}"
            formatted_sources.append(source_display)
        
        return {
            "response": response_text,
            "type": "rag",
            "confidence": rag_result.get("confidence", 0.7), # Default RAG confidence
            "sources": formatted_sources
        }
    
    def _extract_doc_title(self, doc: Dict[str, Any]) -> str:
        """Extract a meaningful title from a document dictionary."""
        content_data = doc.get("content", {})
        metadata = doc.get("metadata", {})
        
        title = content_data.get("title", metadata.get("title"))
        if title:
            return str(title) # Ensure string
        
        source_name = metadata.get("source_name", metadata.get("filename"))
        if source_name:
            name_part, _ = os.path.splitext(os.path.basename(str(source_name)))
            return name_part.replace('_', ' ').replace('-', ' ').title()
            
        doc_id = metadata.get("id", "UnknownID")
        return f"Document {doc_id}"

    def _extract_doc_source_name(self, doc: Dict[str, Any]) -> str:
        """Extract a meaningful source name (like filename) from a document dictionary."""
        metadata = doc.get("metadata", {})
        source_name = metadata.get("source_name", metadata.get("filename"))
        if source_name:
            return os.path.basename(str(source_name)) # Just the filename
        return "Unknown Source File"