import logging
from typing import Dict, Any, Optional, List # Ensure List is imported
from .chatbot_interface import ChatbotInterface

logger = logging.getLogger(__name__)

class ChatbotManager:
    """
    Manages the OSINT chatbot and handles integration with system components.
    Serves as the central point for launching and configuring the chatbot interface.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the chatbot manager.
        
        Args:
            config: Configuration options for the chatbot
        """
        self.config = config or {}
        self.chatbot: Optional[ChatbotInterface] = None # Added type hint for self.chatbot
        logger.info("ChatbotManager initialized")
    
    def setup_chatbot(self, agent_manager=None, rag_pipeline=None, claude_service=None) -> ChatbotInterface:
        """
        Set up and configure the chatbot with system components.
        
        Args:
            agent_manager: The agent manager for executing intelligence tasks
            rag_pipeline: The RAG pipeline for knowledge retrieval
            claude_service: Service for Claude integration
            
        Returns:
            Configured ChatbotInterface instance
        """
        logger.info("Setting up chatbot interface")
        
        # Create and configure the chatbot
        self.chatbot = ChatbotInterface(
            agent_manager=agent_manager,
            rag_pipeline=rag_pipeline,
            claude_service=claude_service
        )
        
        # Apply any additional configuration
        if "system_prompt" in self.config:
            self._set_system_prompt(self.config["system_prompt"])
            
        return self.chatbot
    
    def _set_system_prompt(self, prompt: str) -> None:
        """
        Set a system prompt to establish the chatbot's behavior.
        
        Args:
            prompt: The system prompt text
        """
        if self.chatbot:
            # This initial system message is part of the chatbot's setup, 
            # not part of a specific chat session's history.
            # If ChatbotInterface is truly stateless regarding history, this might be passed
            # to the LLM differently, perhaps as part of the initial system message in each call.
            # For now, we assume ChatbotInterface's add_message sets an initial internal state if needed.
            self.chatbot.add_message("system", prompt) 
            logger.info("System prompt set for ChatbotInterface (if it maintains internal state)")
    
    def get_chatbot(self) -> Optional[ChatbotInterface]:
        """
        Get the configured chatbot interface.
        
        Returns:
            The ChatbotInterface instance or None if not set up
        """
        return self.chatbot
    
    def process_query(self, query: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process a query through the chatbot, passing the relevant conversation history.
        
        Args:
            query: The user's query text
            conversation_history: The history of the current chat session from the UI
            
        Returns:
            The response from the chatbot
        """
        if not self.chatbot:
            logger.error("Chatbot not set up. Call setup_chatbot() first.")
            return {
                "response": "Error: Chatbot not initialized",
                "type": "error",
                "confidence": 0.0, # Ensure float
                "sources": []      # Ensure list
            }
            
        # Pass the conversation_history to the chatbot interface's process_query method
        return self.chatbot.process_query(query, conversation_history or [])