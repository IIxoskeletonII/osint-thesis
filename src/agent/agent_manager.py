"""
Agent Manager module for the OSINT system.
Provides centralized management of agents and tools.
"""

import logging
from typing import Dict, Any, List, Optional

from langchain.schema import Document

from src.agent.base_agent import BaseAgent
from src.agent.osint_agent import OsintAnalysisAgent
from src.agent.tools import ToolRegistry
from src.agent.osint_tools import search_knowledge_base, extract_entities, analyze_relationships, create_timeline
from src.knowledge_base.simple_knowledge_base import SimpleKnowledgeBase

# Import Claude components if available
try:
    from src.llm.claude_service import ClaudeService
    from src.agent.claude_agent import ClaudeAgent
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Manager for OSINT agents and tools.
    Provides centralized access to agent capabilities.
    """
    
    def __init__(self, llm_service, knowledge_base):
        """
        Initialize the agent manager.
        
        Args:
            llm_service: LLM service for agent reasoning
            knowledge_base: Knowledge base for document retrieval
        """
        self.llm_service = llm_service
        self.knowledge_base = knowledge_base
        self.tool_registry = ToolRegistry()
        self.agents = {}
        
        # Register default tools
        self._register_default_tools()
        
        # Create default agents
        self._create_default_agents()
    
    def _register_default_tools(self):
        """Register the default tools for OSINT analysis."""
        # Register knowledge base search tool
        self.tool_registry.register_tool(
            name="search_kb",
            description="Search the knowledge base for documents relevant to a query. Input should be a search query string. Use this FIRST to find information before attempting analysis.",
            func=lambda input_data: search_knowledge_base(self.knowledge_base, input_data)
        )

        # Register entity extraction tool
        self.tool_registry.register_tool(
            name="extract_entities",
            description="Extract specific security-related entities (IPs, emails, URLs, CVEs, file hashes) from a given block of text. Input MUST be the text to analyze.",
            func=extract_entities
        )

        # Register relationship analysis tool
        self.tool_registry.register_tool(
            name="analyze_relationships",
            description="Analyze relationships between entities provided in the input. Input MUST be a JSON string containing an 'entities' list (e.g., {'entities': ['CVE-xxxx', 'APTxx']}). Does NOT search the knowledge base.",
            func=analyze_relationships # This function is still a placeholder
        )

        # Register timeline creation tool
        self.tool_registry.register_tool(
            name="create_timeline",
            description="Create a chronological timeline from a list of events provided in the input. Input MUST be a JSON string containing an 'events' list, where each event has 'date' and 'description'. Does NOT search the knowledge base.",
            func=create_timeline # This function is still a placeholder
        )
    
    def _create_default_agents(self):
        """Create the default agents."""
        # Create OSINT analysis agent
        self.agents["osint_analysis"] = OsintAnalysisAgent(
            llm_service=self.llm_service,
            knowledge_base=self.knowledge_base,
            tool_registry=self.tool_registry
        )
        
        # Try to create a Claude agent if Claude is available
        if CLAUDE_AVAILABLE:
            try:
                claude_service = ClaudeService()
                self.agents["claude_analysis"] = ClaudeAgent(
                    claude_service=claude_service,
                    knowledge_base=self.knowledge_base,
                    tool_registry=self.tool_registry
                )
                logger.info("Claude agent created successfully")
            except Exception as e:
                logger.warning(f"Failed to create Claude agent: {str(e)}")
    
    def list_available_agents(self) -> List[str]:
        """
        List all available agents.
        
        Returns:
            List of agent names
        """
        return list(self.agents.keys())
    
    def list_available_tools(self) -> List[Dict]:
        """
        List all available tools.
        
        Returns:
            List of tool definitions
        """
        return self.tool_registry.list_tools()
    
    def execute_agent(
        self, 
        agent_name: str, 
        query: str, 
        context: Optional[List[Document]] = None
    ) -> Dict:
        """
        Execute an agent on a query.
        
        Args:
            agent_name: Name of the agent to execute
            query: User query
            context: Optional context documents
            
        Returns:
            Agent execution results
            
        Raises:
            KeyError: If agent does not exist
        """
        if agent_name not in self.agents:
            raise KeyError(f"Agent '{agent_name}' not found")
        
        logger.info(f"Executing agent '{agent_name}' on query: {query}")
        
        result = self.agents[agent_name].execute(query, context)
        return result
    
    def register_custom_tool(self, name: str, description: str, func: callable):
        """
        Register a custom tool.
        
        Args:
            name: Tool name
            description: Tool description
            func: Tool function
        """
        self.tool_registry.register_tool(name, description, func)
        logger.info(f"Registered custom tool: {name}")