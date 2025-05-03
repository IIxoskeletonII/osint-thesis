"""
Specialized OSINT agent for intelligence analysis.
Provides capabilities for complex intelligence gathering and analysis tasks.
"""

import logging
import json
from typing import Dict, List, Any, Optional

from langchain.schema import Document

from src.agent.base_agent import BaseAgent
from src.agent.tools import ToolRegistry
from src.knowledge_base.simple_knowledge_base import SimpleKnowledgeBase

logger = logging.getLogger(__name__)

class OsintAnalysisAgent(BaseAgent):
    """Agent specialized for OSINT analysis tasks."""
    
    def __init__(self, llm_service, knowledge_base, tool_registry: ToolRegistry):
        """
        Initialize the OSINT analysis agent.
        
        Args:
            llm_service: The LLM service used for reasoning and generation
            knowledge_base: KnowledgeBase instance for document retrieval
            tool_registry: ToolRegistry instance for tool access
        """
        super().__init__(llm_service)
        self.knowledge_base = knowledge_base
        self.tool_registry = tool_registry
        self._register_default_tools()
        
    def _register_default_tools(self):
        """Register the default tools for the OSINT agent."""
        # Convert tool registry tools to the format expected by the base agent
        for name, details in self.tool_registry.tools.items():
            self.add_tool({
                "name": details["name"],
                "description": details["description"]
            })
    
    def _enhanced_react_prompt(self, query: str, context: Optional[List[Document]] = None) -> str:
        """
        Create an enhanced ReAct-style prompt for OSINT analysis.
        
        Args:
            query: The user's query
            context: Optional context documents
            
        Returns:
            Formatted prompt for the LLM
        """
        # Format context if provided
        context_str = ""
        if context:
            context_str = "## Intelligence Context Information:\n"
            for i, doc in enumerate(context):
                source = doc.metadata.get('source', 'Unknown Source')
                doc_type = doc.metadata.get('doc_type', 'Unknown Type')
                context_str += f"Document {i+1} from {source} ({doc_type}):\n{doc.page_content}\n\n"
        
        # Format tools
        tools_str = self._format_tools_for_prompt()
        
        # Build the enhanced ReAct prompt
        prompt = f"""
You are an expert OSINT analyst specializing in cybersecurity intelligence.
Your task is to analyze intelligence information and answer security-related questions.

# Available Tools
You have access to the following tools to assist with your analysis:

{tools_str}

# Instructions for Tool Use
To use a tool, follow this format:
Thought: [Your reasoning about what needs to be done]
Action: [tool_name]
Action Input: [input for the tool, formatted according to the tool's requirements]
Observation: [Result from using the tool will appear here]

# Analysis Process
1. Carefully think about the query and what intelligence you need
2. Use appropriate tools to gather and analyze information
3. Consider multiple perspectives and potential connections
4. Provide a comprehensive and nuanced analysis
5. Cite specific sources and evidence for your conclusions
6. Express appropriate confidence levels based on the available evidence

{context_str}

# Intelligence Query
{query}

Let's analyze this systematically:
Thought: """
        
        return prompt
    
    def execute(self, query: str, context: Optional[List[Document]] = None) -> Dict:
        """
        Execute the OSINT analysis agent on a query.
        
        Args:
            query: The user's query
            context: Optional context documents
            
        Returns:
            Agent execution results including thoughts, actions, and final response
        """
        logger.info(f"Executing OSINT analysis agent on query: {query}")
        
        # Create the initial prompt
        prompt = self._enhanced_react_prompt(query, context)
        max_iterations = 5
        current_prompt = prompt
        
        # Track the full conversation
        conversation_log = []
        conversation_log.append({"role": "system", "content": current_prompt})
        
        # Execute agent with a limited number of steps
        for i in range(max_iterations):
            # Get response from LLM
            llm_response = self.llm_service.generate(current_prompt)
            
            # Parse the response
            parsed = self._parse_llm_response(llm_response)
            
            # Check if we have a final response
            if parsed["final_response"] and not parsed["actions"]:
                # We have a final answer with no more actions
                conversation_log.append({"role": "assistant", "content": llm_response})
                
                return {
                    "query": query,
                    "conversation": conversation_log,
                    "thoughts": parsed["thoughts"],
                    "actions": parsed["actions"],
                    "response": parsed["final_response"]
                }
            
            # If we have actions, execute the last one
            if parsed["actions"]:
                action = parsed["actions"][-1]
                tool_name = action["action"]
                tool_input = action["input"]
                
                # Log the assistant's thinking
                conversation_log.append({"role": "assistant", "content": llm_response})
                
                try:
                    # Execute the tool
                    tool_result = self.tool_registry.execute_tool(tool_name, tool_input)
                    
                    # Add the observation to the prompt
                    current_prompt = f"{current_prompt}\n{llm_response}\nObservation: {tool_result}\nThought: "
                    
                    # Log the tool result
                    conversation_log.append({"role": "system", "content": f"Observation: {tool_result}"})
                except KeyError:
                    # Tool not found
                    error_msg = f"Error: Tool '{tool_name}' not found. Please use one of the available tools."
                    current_prompt = f"{current_prompt}\n{llm_response}\nObservation: {error_msg}\nThought: "
                    conversation_log.append({"role": "system", "content": f"Observation: {error_msg}"})
            else:
                # No actions but also no final response, add to prompt
                conversation_log.append({"role": "assistant", "content": llm_response})
                current_prompt = f"{current_prompt}\n{llm_response}\nThought: "
        
        # If we reach here, we've hit the maximum iterations
        final_response = "I've reached the maximum number of analysis steps. Here's my current understanding:\n\n"
        final_response += parsed.get("final_response", "Based on the information gathered, I cannot provide a definitive answer at this time.")
        
        return {
            "query": query,
            "conversation": conversation_log,
            "thoughts": parsed["thoughts"],
            "actions": parsed["actions"],
            "response": final_response,
            "status": "max_iterations_reached"
        }