from typing import Dict, List, Any, Optional
import logging
from .query_processor import QueryProcessor
from .response_generator import ResponseGenerator

logger = logging.getLogger(__name__)

class ChatbotInterface:
    """
    Core chatbot interface for OSINT system.
    Handles conversation management and integration with agent framework.
    """
    
    def __init__(self, agent_manager=None, rag_pipeline=None, claude_service=None):
        """
        Initialize the chatbot interface.
        
        Args:
            agent_manager: The agent manager for executing intelligence tasks
            rag_pipeline: The RAG pipeline for knowledge retrieval
            claude_service: Service for Claude integration
        """
        self.agent_manager = agent_manager
        self.rag_pipeline = rag_pipeline
        self.claude_service = claude_service
        
        # Initialize components
        self.query_processor = QueryProcessor(rag_pipeline=rag_pipeline)
        self.response_generator = ResponseGenerator(claude_service=claude_service)
        
        self.conversation_history = []
        logger.info("ChatbotInterface initialized")
        
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: The role of the message sender ('user' or 'system')
            content: The content of the message
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": self._get_timestamp()
        }
        self.conversation_history.append(message)
        
    def _get_timestamp(self) -> str:
        """Get the current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
        
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Returns:
            The list of messages in the conversation
        """
        return self.conversation_history
    
    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the OSINT system.
        
        Args:
            query: The user's query text
            
        Returns:
            The response from the system
        """
        # Add user query to conversation history
        self.add_message("user", query)
        
        # Process the query
        query_result = self.query_processor.process_query(query, self.conversation_history)
        logger.info(f"Query processed: {query_result['query_type']}, use agent: {query_result['use_agent']}")
        
        # Execute the appropriate pipeline based on query analysis
        rag_result = None
        agent_result = None
        
        if query_result["use_agent"] and self.agent_manager:
            # Use the agent for complex queries
            agent_type = "osint_analysis"  # Default agent type
            
            # Could select different agent types based on query
            if "timeline" in query.lower():
                agent_type = "timeline_analysis"
            elif any(term in query.lower() for term in ["relationship", "connection", "network"]):
                agent_type = "relationship_analysis"
                
            logger.info(f"Executing agent: {agent_type}")
            agent_result = self.agent_manager.execute_agent(
                agent_name=agent_type, 
                query=query_result["enhanced_query"]
            )
        else:
            # Use RAG for direct knowledge queries
            if self.rag_pipeline:
                logger.info("Executing RAG pipeline")
                rag_result = self.rag_pipeline.process_query(query_result["enhanced_query"])
        
        # Generate response based on results
        response_data = self.response_generator.generate_response(
            query_result=query_result,
            rag_result=rag_result,
            agent_result=agent_result
        )
        
        # Add system response to conversation history
        self.add_message("system", response_data["response"])
        
        return response_data