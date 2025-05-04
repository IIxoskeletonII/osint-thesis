"""
Response generator module for the OSINT chatbot interface.
Handles the generation and formatting of responses based on RAG and agent results.
"""

from typing import Dict, Any, List, Optional
import logging
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
        self.agent_response_handler = AgentResponseHandler()
        logger.info("ResponseGenerator initialized")
    
    def generate_response(self, 
                          query_result: Dict[str, Any], 
                          rag_result: Optional[Dict[str, Any]] = None,
                          agent_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a response based on the query results.
        
        Args:
            query_result: The processed query information
            rag_result: Results from the RAG pipeline (if used)
            agent_result: Results from the agent execution (if used)
            
        Returns:
            Dict containing the generated response and metadata
        """
        if agent_result:
            # Use agent result as the primary response source
            return self.agent_response_handler.format_agent_response(agent_result)
        elif rag_result:
            # Use RAG result for direct knowledge access
            # Check if RAG result has useful information
            if self._is_rag_result_useful(rag_result):
                return self._format_rag_response(query_result, rag_result)
            else:
                # Fallback to Claude if RAG doesn't have useful information
                return self._generate_claude_fallback(query_result)
        else:
            # Fallback to Claude if no results are available
            return self._generate_claude_fallback(query_result)
    
    def _is_rag_result_useful(self, rag_result: Dict[str, Any]) -> bool:
        """
        Determine if the RAG result contains useful information.
        
        Args:
            rag_result: Results from the RAG pipeline
            
        Returns:
            Boolean indicating if the result is useful
        """
        # Check if RAG response is available and not an error
        if "error" in rag_result:
            return False
            
        # Check if response exists
        if "response" not in rag_result:
            return False
            
        # Get the RAG response text
        response_text = rag_result.get("response", "")
        
        # Check if the response indicates no information was found
        no_info_indicators = [
            "couldn't find specific information",
            "don't have information",
            "no information available",
            "insufficient information",
            "no relevant information",
            "couldn't retrieve information",
            "couldn't find any relevant"
        ]
        
        if any(indicator in response_text.lower() for indicator in no_info_indicators):
            return False
            
        # Check if confidence is too low
        if rag_result.get("confidence", 0.5) < 0.3:
            return False
            
        # If we get here, the RAG result is potentially useful
        return True
    
    def _generate_claude_fallback(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a fallback response using Claude when knowledge base lacks information.
        
        Args:
            query_result: The processed query information
            
        Returns:
            Dict containing the Claude-generated response
        """
        if not self.claude_service:
            # If Claude service is not available, use the regular fallback
            return self._generate_fallback_response(query_result)
            
        original_query = query_result.get("original_query", "")
        enhanced_query = query_result.get("enhanced_query", original_query)
        
        logger.info(f"Generating Claude fallback response for: {enhanced_query}")
        
        try:
            # Prepare a prompt for Claude
            prompt = f"""
            As an OSINT and cybersecurity intelligence assistant, please answer the following query 
            using your general knowledge. This query couldn't be answered from our specialized 
            knowledge base, so we're relying on your expertise.
            
            Query: {enhanced_query}
            
            Please provide a comprehensive, accurate response focused on cybersecurity and 
            intelligence aspects. Include any relevant technical details, methodologies, or best 
            practices. If the question is outside of cybersecurity or intelligence domains, please 
            keep your response focused on relevant security implications.
            """
            
            # Get response from Claude
            response = self.claude_service.generate_text(prompt, max_tokens=1500)
            
            # Format the response
            return {
                "response": response,
                "type": "claude_fallback",
                "confidence": 0.6,  # Moderate confidence for Claude general knowledge
                "sources": ["Claude general knowledge"]
            }
            
        except Exception as e:
            logger.error(f"Error generating Claude fallback: {str(e)}")
            # If Claude fails, fall back to the regular fallback
            return self._generate_fallback_response(query_result)
    
    def _format_rag_response(self, query_result: Dict[str, Any], rag_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a response based on RAG results.
        
        Args:
            query_result: The processed query information
            rag_result: Results from the RAG pipeline
            
        Returns:
            Dict containing the formatted response
        """
        # Check if RAG response is available
        if "response" not in rag_result and "error" in rag_result:
            # Handle error case
            return {
                "response": f"I couldn't retrieve information from the knowledge base: {rag_result.get('error', 'Unknown error')}",
                "type": "error",
                "confidence": 0.1,
                "sources": []
            }
        
        # Extract the RAG response text
        response_text = rag_result.get("response", "No response generated from the knowledge base.")
        
        # Get the supporting documents
        documents = rag_result.get("retrieved_documents", rag_result.get("documents", []))
        formatted_sources = []
        
        for doc in documents:
            if isinstance(doc, dict):
                # Use our helper methods to extract document information
                doc_title = self._extract_doc_title(doc)
                doc_source = self._extract_doc_source(doc)
                doc_score = self._extract_doc_score(doc)
                
                formatted_sources.append(f"{doc_title} ({doc_source}) - Relevance: {doc_score:.2f}")
        
        return {
            "response": response_text,
            "type": "rag",
            "confidence": rag_result.get("confidence", 0.5),
            "sources": formatted_sources
        }
    
    def _extract_doc_title(self, doc: Dict[str, Any]) -> str:
        """Extract a meaningful title from a document."""
        # Try different ways to extract document title
        doc_title = doc.get("title", "")
        
        # Try to extract from document field if exists
        if not doc_title and "document" in doc:
            doc_title = doc["document"].get("title", "")
        
        # Try to extract from metadata if exists
        if not doc_title and "metadata" in doc:
            doc_title = doc["metadata"].get("title", "")
        
        # Try looking for a filename instead
        if not doc_title:
            if "source" in doc and doc["source"]:
                # Use filename as title if available
                doc_title = self._extract_filename(doc["source"])
            elif "document" in doc and "source" in doc["document"]:
                doc_title = self._extract_filename(doc["document"]["source"])
        
        # Last resort: Try to generate a title from content
        if not doc_title and "content" in doc:
            # Take first line or first 50 chars as title
            content = doc["content"]
            if isinstance(content, str) and content.strip():
                first_line = content.strip().split('\n')[0]
                doc_title = first_line[:50] + ('...' if len(first_line) > 50 else '')
        
        # Default if all else fails
        if not doc_title:
            doc_title = "Untitled document"
        
        return doc_title

    def _extract_doc_source(self, doc: Dict[str, Any]) -> str:
        """Extract a meaningful source from a document."""
        # Try different ways to extract document source
        doc_source = doc.get("source", "")
        
        # Try to extract from document field if exists
        if not doc_source and "document" in doc:
            doc_source = doc["document"].get("source", "")
        
        # Try to extract from metadata if exists
        if not doc_source and "metadata" in doc:
            if "source" in doc["metadata"]:
                doc_source = doc["metadata"]["source"]
            elif "filename" in doc["metadata"]:
                doc_source = doc["metadata"]["filename"]
        
        # If source looks like a filepath, extract just the filename
        if doc_source and ('/' in doc_source or '\\' in doc_source):
            doc_source = self._extract_filename(doc_source)
        
        # Default if all else fails
        if not doc_source:
            doc_source = "Unknown source"
        
        return doc_source

    def _extract_doc_score(self, doc: Dict[str, Any]) -> float:
        """Extract the similarity score from a document."""
        # Try different ways to extract score
        score = doc.get("score", doc.get("similarity", 0))
        
        # Try to extract from metadata if exists
        if score == 0 and "metadata" in doc:
            score = doc["metadata"].get("score", doc["metadata"].get("similarity", 0))
        
        return score

    def _extract_filename(self, path: str) -> str:
        """Extract filename from a path."""
        if not path:
            return ""
        
        # Split on both forward and backward slashes
        parts = path.replace('\\', '/').split('/')
        return parts[-1] if parts else path
    
    def _generate_fallback_response(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a fallback response when no results are available.
        
        Args:
            query_result: The processed query information
            
        Returns:
            Dict containing the fallback response
        """
        query_type = query_result.get("query_type", "general")
        original_query = query_result.get("original_query", "your query")
        domain_focus = query_result.get("domain_focus", "general")
        
        # Map domain focus to specific suggestions
        domain_suggestions = {
            "threat_intel": "I can help with information about threat actors, campaigns, and indicators of compromise.",
            "vulnerability": "I can provide information about common vulnerabilities, patch management, and mitigation strategies.",
            "malware": "I can offer insights on malware types, behaviors, and detection methods.",
            "network_security": "I can discuss network security architecture, protocols, and defense mechanisms.",
            "defense": "I can explain security controls, incident response procedures, and defensive strategies.",
            "compliance": "I can cover compliance frameworks, regulations, and security policies.",
            "identity": "I can address authentication methods, access control, and identity management."
        }
        
        # Default suggestion
        suggestion = domain_suggestions.get(domain_focus, "I can provide information on cybersecurity topics including threats, vulnerabilities, and security practices.")
        
        # Customize fallback message based on query type
        fallback_responses = {
            "informational": f"I don't have specific information about {original_query} in my knowledge base. {suggestion}",
            "procedural": f"I don't have specific procedural information about {original_query} in my knowledge base. Could you provide more details about what you're trying to accomplish?",
            "analytical": f"I don't have enough information to analyze {original_query} comprehensively. What specific aspects would you like me to focus on?",
            "comparative": f"I don't have sufficient information to compare {original_query}. Could you specify which particular aspects you'd like me to compare?",
            "listing": f"I don't have a comprehensive list of {original_query} in my knowledge base. Could you narrow down your request to a specific area of cybersecurity?",
            "keyword": f"I don't have much information about '{original_query}' in my current knowledge base. {suggestion}",
            "general": f"I don't have specific information on {original_query}. {suggestion}"
        }
        
        response_text = fallback_responses.get(query_type, fallback_responses["general"])
        
        # Add example reformulation suggestions
        response_text += "\n\nYou might try reformulating your question with more specific details, such as:"
        
        if query_type == "informational":
            response_text += "\n- What are the most common attack vectors used against web applications?"
            response_text += "\n- How do security researchers classify different types of threat actors?"
        elif query_type == "procedural":
            response_text += "\n- What steps should be taken when responding to a potential data breach?"
            response_text += "\n- How can I set up a basic network security monitoring system?"
        elif query_type == "analytical":
            response_text += "\n- What patterns have emerged in ransomware attacks against healthcare organizations?"
            response_text += "\n- How has the threat landscape evolved for cloud infrastructure over the past year?"
        
        return {
            "response": response_text,
            "type": "fallback",
            "confidence": 0.2,
            "sources": []
        }