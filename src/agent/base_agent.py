"""
Base Agent implementation for the OSINT system.
This module provides the foundation for agent-based intelligence gathering and analysis.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Callable

from langchain.schema import Document

logger = logging.getLogger(__name__)

class BaseAgent:
    """Base class for all agents in the OSINT system."""
    
    def __init__(self, llm_service, tools: List[Dict] = None):
        """
        Initialize the base agent.
        
        Args:
            llm_service: The LLM service used for reasoning and generation
            tools: List of tools available to the agent
        """
        self.llm_service = llm_service
        self.tools = tools or []
        self.thought_history = []
        
    def add_tool(self, tool: Dict):
        """
        Add a tool to the agent's toolkit.
        
        Args:
            tool: Tool definition including name, description, and function
        """
        self.tools.append(tool)
        
    def _format_tools_for_prompt(self) -> str:
        """Format tools into a string representation for the prompt."""
        tools_str = ""
        for i, tool in enumerate(self.tools):
            tools_str += f"{i+1}. {tool['name']}: {tool['description']}\n"
        return tools_str
        
    def _react_prompt(self, query: str, context: Optional[List[Document]] = None) -> str:
        """
        Create a ReAct-style prompt for the agent.
        
        Args:
            query: The user's query
            context: Optional context documents
            
        Returns:
            Formatted prompt for the LLM
        """
        # Format context if provided
        context_str = ""
        if context:
            context_str = "Context Information:\n"
            for i, doc in enumerate(context):
                source = doc.metadata.get('source', 'Unknown Source')
                context_str += f"Document {i+1} from {source}:\n{doc.page_content}\n\n"
        
        # Format tools
        tools_str = self._format_tools_for_prompt()
        
        # Build the ReAct prompt
        prompt = f"""
You are an expert OSINT analyst tasked with answering intelligence questions.
You have access to the following tools:

{tools_str}

To use a tool, use the format:
Thought: I need to find out X
Action: tool_name
Action Input: input for the tool
Observation: [Result from using the tool]

Follow this process:
1. Think about the problem
2. Decide if you need to use a tool
3. Use the tool and observe the result
4. Continue this process until you have enough information
5. When you have the answer, respond directly to the query

{context_str}

User Query: {query}

Let's work through this step by step:
Thought: """
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        Parse the LLM's response to extract thoughts, actions, and final response.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Parsed components of the response
        """
        # Simple parsing implementation
        # This would be enhanced in a production system
        result = {
            "thoughts": [],
            "actions": [],
            "final_response": ""
        }
        
        # Extract thought-action pairs
        current_thought = ""
        current_action = ""
        current_action_input = ""
        
        lines = response.split("\n")
        parsing_final = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("Thought:"):
                if current_thought:
                    result["thoughts"].append(current_thought)
                current_thought = line[len("Thought:"):].strip()
            
            elif line.startswith("Action:"):
                current_action = line[len("Action:"):].strip()
            
            elif line.startswith("Action Input:"):
                current_action_input = line[len("Action Input:"):].strip()
                if current_thought and current_action:
                    result["actions"].append({
                        "thought": current_thought,
                        "action": current_action,
                        "input": current_action_input
                    })
                    current_thought = ""
                    current_action = ""
                    current_action_input = ""
            
            elif parsing_final or (not line.startswith(("Thought:", "Action:", "Action Input:", "Observation:"))):
                parsing_final = True
                if line:
                    result["final_response"] += line + "\n"
        
        # Add any remaining thought
        if current_thought:
            result["thoughts"].append(current_thought)
            
        result["final_response"] = result["final_response"].strip()
        
        return result
    
    def execute(self, query: str, context: Optional[List[Document]] = None) -> Dict:
        """
        Execute the agent on a query.
        
        Args:
            query: The user's query
            context: Optional context documents
            
        Returns:
            Agent execution results including thoughts, actions, and final response
        """
        logger.info(f"Executing agent on query: {query}")
        
        # Create the initial prompt
        prompt = self._react_prompt(query, context)
        
        # Get response from LLM
        llm_response = self.llm_service.generate(prompt)
        
        # Parse the response
        parsed_response = self._parse_llm_response(llm_response)
        
        return {
            "query": query,
            "thoughts": parsed_response["thoughts"],
            "actions": parsed_response["actions"],
            "response": parsed_response["final_response"]
        }