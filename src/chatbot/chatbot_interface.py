from typing import Dict, List, Any, Optional # Ensure List and Optional are imported
import logging
from .query_processor import QueryProcessor
from .response_generator import ResponseGenerator
# Assuming AgentManager and RagPipeline are correctly imported or passed if needed by methods
# from src.agent.agent_manager import AgentManager (example if needed)
# from src.rag.rag_pipeline import RagPipeline (example if needed)


logger = logging.getLogger(__name__)

class ChatbotInterface:
    """
    Core chatbot interface for OSINT system.
    Handles conversation management and integration with agent framework.
    This class is now designed to be more stateless regarding long-term conversation history,
    relying on history passed in via process_query.
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
        
        self.query_processor = QueryProcessor(rag_pipeline=self.rag_pipeline) # Pass RAG pipeline
        self.response_generator = ResponseGenerator(claude_service=self.claude_service) # Pass Claude service
        
        # This internal history is primarily for the agent's iterative context building if needed.
        # The UI (app.py) now manages the persistent chat session histories.
        self._internal_turn_history: List[Dict[str, Any]] = [] 
        logger.info("ChatbotInterface initialized")
        
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the internal turn history.
        This is mainly for system prompts or if the agent needs to build context internally.
        The primary conversation history is managed by the UI.
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": self._get_timestamp() # Keep timestamp for logging if needed
        }
        self._internal_turn_history.append(message)
        # logger.debug(f"Added message to ChatbotInterface internal turn history: {role}")
        
    def _get_timestamp(self) -> str:
        """Get the current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
        
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the internal turn history. Not for long-term session storage.
        """
        return self._internal_turn_history
    
    def clear_conversation(self) -> None:
        """Clear the internal turn history. Called when switching chats or clearing UI."""
        self._internal_turn_history = []
        logger.info("ChatbotInterface internal turn history cleared.")
        
    def process_query(self, query: str, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a user query through the OSINT system.
        
        Args:
            query: The user's query text
            conversation_history: The history of messages for the current chat session from the UI.
                                 This typically includes previous user queries and assistant responses.
                                 The current user query is the last item if appended by the caller.
                                 Or, it might be passed as `query` and not yet in `conversation_history`.
                                 For consistency, we'll assume `query` is the *new* prompt,
                                 and `conversation_history` is everything *before* it.
            
        Returns:
            The response from the system
        """
        # The `conversation_history` passed from `app.py` via `ChatbotManager` is the
        # state of the current chat *before* the current user's `query`.
        # The `QueryProcessor` might use this for context.
        
        # For the agent's ReAct loop, the history is built iteratively.
        # The initial prompt to the agent includes the current query.
        
        # It's important that `QueryProcessor` can use `conversation_history`
        # for things like pronoun resolution or contextual understanding.
        query_result = self.query_processor.process_query(query, conversation_history)
        logger.info(f"Query processed: type='{query_result.get('query_type', 'N/A')}', use_agent='{query_result.get('use_agent', False)}'")
        
        rag_result: Optional[Dict[str, Any]] = None
        agent_result: Optional[Dict[str, Any]] = None
        
        if query_result.get("use_agent") and self.agent_manager:
            agent_type = query_result.get("agent_type", "osint_analysis") # Allow QueryProcessor to suggest agent type
            
            logger.info(f"Executing agent: {agent_type}")
            # The agent's `execute` method typically builds its own internal history for the ReAct loop,
            # starting with the current query and potentially some high-level context.
            # The full `conversation_history` from the UI might be too verbose for every agent turn.
            # The `_enhanced_react_prompt` in `OsintAgent` can take `context` which could be
            # a summary or key parts of `conversation_history`.
            # For now, the agent starts fresh with the enhanced query.
            agent_context_docs: Optional[List[Dict[str, Any]]] = None # Placeholder if we decide to pass some history as context docs
            
            agent_result = self.agent_manager.execute_agent(
                agent_name=agent_type, 
                query=query_result["enhanced_query"],
                context=agent_context_docs 
            )
        else:
            if self.rag_pipeline:
                logger.info("Executing RAG pipeline")
                rag_result = self.rag_pipeline.process_query(query_result["enhanced_query"])
        
        response_data = self.response_generator.generate_response(
            query_result=query_result,
            rag_result=rag_result,
            agent_result=agent_result
        )
        
        # The UI (app.py) is responsible for adding the final user query and this assistant response
        # to its session state for the specific chat. This class remains stateless for long-term history.
        
        return response_data