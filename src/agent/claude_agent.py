"""
Claude-powered OSINT agent for intelligence analysis.
Provides advanced capabilities using Claude's API directly.
"""

import logging
import json
from typing import Dict, List, Any, Optional

from langchain.schema import Document

from src.agent.base_agent import BaseAgent
from src.agent.tools import ToolRegistry
from src.llm.claude_service import ClaudeService

logger = logging.getLogger(__name__)

class ClaudeAgent(BaseAgent):
    """Agent powered by Claude 3.7 for OSINT analysis."""
    
    def __init__(self, claude_service: ClaudeService, knowledge_base, tool_registry: ToolRegistry):
        """
        Initialize the Claude-powered agent.
        
        Args:
            claude_service: Claude service for LLM capabilities
            knowledge_base: Knowledge base for document retrieval
            tool_registry: ToolRegistry instance for tool access
        """
        super().__init__(claude_service)
        self.claude_service = claude_service
        self.knowledge_base = knowledge_base
        self.tool_registry = tool_registry
        self._register_default_tools()
        
    def _register_default_tools(self):
        """Register the default tools for the Claude agent."""
        # Convert tool registry tools to the format expected by the base agent
        for name, details in self.tool_registry.tools.items():
            self.add_tool({
                "name": details["name"],
                "description": details["description"]
            })
    
    def _format_tools_for_claude(self) -> List[Dict]:
        """Format tools into a list of tool definitions for Claude API."""
        claude_tools = []
        for tool in self.tools:
            claude_tools.append({
                "name": tool["name"],
                "description": tool["description"]
            })
        return claude_tools
    
    def _enhanced_claude_prompt(self, query: str, context: Optional[List[Document]] = None) -> str:
        """
        Create an enhanced prompt for Claude.
        
        Args:
            query: The user's query
            context: Optional context documents
            
        Returns:
            Formatted prompt for Claude
        """
        # Format context if provided
        context_str = ""
        if context:
            context_str = "## Intelligence Context Information:\n"
            for i, doc in enumerate(context):
                source = doc.metadata.get('source', 'Unknown Source')
                doc_type = doc.metadata.get('doc_type', 'Unknown Type')
                context_str += f"Document {i+1} from {source} ({doc_type}):\n{doc.page_content}\n\n"
        
        # Build the enhanced prompt
        prompt = f"""
You are an expert OSINT (Open Source Intelligence) analyst specializing in cybersecurity intelligence.
Your task is to analyze intelligence information and answer security-related questions.

# Analysis Process
1. Carefully think about the query and what intelligence you need
2. Use appropriate tools when necessary to gather and analyze information
3. Consider multiple perspectives and potential connections
4. Provide a comprehensive and nuanced analysis
5. Cite specific sources and evidence for your conclusions
6. Express appropriate confidence levels based on the available evidence

{context_str}

# Intelligence Query
{query}

Please provide a thorough analysis based on the available information.
"""
        
        return prompt
    
    def execute(self, query: str, context: Optional[List[Document]] = None) -> Dict:
        """
        Execute the Claude agent on a query.
        
        Args:
            query: The user's query
            context: Optional context documents
            
        Returns:
            Agent execution results
        """
        logger.info(f"Executing Claude agent on query: {query}")
        
        # Create the initial prompt
        prompt = self._enhanced_claude_prompt(query, context)
        
        # Get Claude tools
        claude_tools = self._format_tools_for_claude()
        
        # Execute with Claude's native tool calling capability
        response = self.claude_service.generate_with_tools(prompt, claude_tools)
        
        # Process tool calls if any
        processed_tool_calls = []
        
        for tool_call in response.get("tool_calls", []):
            tool_name = tool_call["name"]
            tool_input = tool_call["input"]
            
            try:
                # Execute the tool
                tool_result = self.tool_registry.execute_tool(tool_name, tool_input["input"])
                
                processed_tool_calls.append({
                    "tool": tool_name,
                    "input": tool_input["input"],
                    "result": tool_result
                })
                
            except KeyError:
                processed_tool_calls.append({
                    "tool": tool_name,
                    "input": tool_input["input"],
                    "result": f"Error: Tool '{tool_name}' not found."
                })
        
        # If we have tool calls, send a follow-up to Claude with the results
        if processed_tool_calls:
            # Format tool results
            tool_results_str = "# Tool Results\n\n"
            for call in processed_tool_calls:
                tool_results_str += f"## {call['tool']}\n"
                tool_results_str += f"Input: {call['input']}\n"
                tool_results_str += f"Result: {call['result']}\n\n"
            
            # Create follow-up prompt
            follow_up_prompt = f"""
{prompt}

{tool_results_str}

Based on the query and the tool results, please provide your final analysis.
"""
            
            # Get final response from Claude
            final_response = self.claude_service.generate(follow_up_prompt)
            
            return {
                "query": query,
                "tool_calls": processed_tool_calls,
                "response": final_response
            }
        
        # If no tool calls, just return the initial response
        return {
            "query": query,
            "tool_calls": [],
            "response": response["text"]
        }