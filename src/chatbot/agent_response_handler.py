"""
Agent response handler module for the OSINT system.
Handles the formatting and extraction of information from agent responses.
"""

import logging
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)

class AgentResponseHandler:
    """
    Handles the formatting and extraction of information from agent responses.
    """
    
    @staticmethod
    def extract_conclusion(agent_result: Dict[str, Any]) -> str:
        """
        Extract the conclusion from an agent result.
        
        Args:
            agent_result: The result from agent execution
            
        Returns:
            The extracted conclusion
        """
        if not agent_result:
            return "No agent result provided."
            
        # Try to get the conclusion directly
        conclusion = agent_result.get("conclusion")
        if conclusion:
            return conclusion
            
        # Try to extract from response field
        response = agent_result.get("response")
        if response:
            # If response is substantial, use it as the conclusion
            if len(response) > 100:
                return response
                
        # If no conclusion found, try to extract from the final step
        steps = agent_result.get("steps", [])
        if steps:
            final_step = steps[-1]
            final_result = final_step.get("result", "")
            
            # If the final result is substantial, use that
            if len(final_result) > 100:
                return final_result
                
            # If there's any observation, use that
            observation = final_step.get("observation", "")
            if observation:
                return observation
        
        # Try to extract from tool_calls
        tool_calls = agent_result.get("tool_calls", [])
        if tool_calls and len(tool_calls) > 0:
            # Use the result of the last tool call
            last_call = tool_calls[-1]
            if "result" in last_call and len(last_call["result"]) > 100:
                return f"Based on tool analysis, I found: {last_call['result']}"
        
        # If all else fails, use the query and a generic message
        query = agent_result.get("query", "")
        if query:
            return f"I've analyzed your query about '{query}' but couldn't find specific information in the knowledge base. Consider refining your question or providing additional context."
        
        # Last resort
        return "Based on the analysis, I couldn't find conclusive information in the available knowledge base. The system may need additional data sources to better answer this type of query."
    
    @staticmethod
    def format_agent_response(agent_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format agent result into a standard response format.
        
        Args:
            agent_result: The result from agent execution
            
        Returns:
            Formatted response dictionary
        """
        # Extract conclusion
        conclusion = AgentResponseHandler.extract_conclusion(agent_result)
        
        # Check if this appears to be a response based on general knowledge
        # rather than knowledge base information
        is_general_knowledge = AgentResponseHandler._is_general_knowledge_response(agent_result, conclusion)
        
        # Extract steps for transparency
        steps = agent_result.get("steps", [])
        step_summaries = []
        
        for i, step in enumerate(steps):
            action = step.get("action", "Unknown action")
            result_summary = step.get("result", "No result")
            
            # Truncate long results for display
            if len(result_summary) > 100:
                result_summary = result_summary[:100] + "..."
                
            step_summaries.append(f"Step {i+1}: {action} → {result_summary}")
        
        # Also check for tool_calls format
        tool_calls = agent_result.get("tool_calls", [])
        for i, call in enumerate(tool_calls):
            tool = call.get("tool", "Unknown tool")
            input_data = call.get("input", "No input")
            result = call.get("result", "No result")
            
            # Truncate long results for display
            if len(result) > 100:
                result = result[:100] + "..."
                
            step_summaries.append(f"Tool {i+1}: {tool}({input_data}) → {result}")
        
        # Extract sources
        sources = agent_result.get("sources", [])
        formatted_sources = []
        
        for source in sources:
            if isinstance(source, dict):
                source_name = source.get("name", "Unknown source")
                source_type = source.get("type", "Unknown type")
                formatted_sources.append(f"{source_name} ({source_type})")
            elif isinstance(source, str):
                formatted_sources.append(source)
        
        # Generate full response text
        response_text = conclusion
        
        # Add steps if available and this is not a general knowledge response
        if step_summaries and len(step_summaries) > 0 and not is_general_knowledge:
            response_text += "\n\n## Analysis Process:\n"
            response_text += "\n".join(step_summaries)
        
        # Determine response type
        if is_general_knowledge:
            response_type = "claude_fallback"
            confidence = 0.6
            if not formatted_sources:
                formatted_sources = ["Claude general knowledge"]
        else:
            response_type = "agent"
            confidence = agent_result.get("confidence", 0.7)
        
        return {
            "response": response_text,
            "type": response_type,
            "confidence": confidence,
            "sources": formatted_sources
        }
    
    @staticmethod
    def _is_general_knowledge_response(agent_result: Dict[str, Any], conclusion: str) -> bool:
        """
        Determine if the agent response appears to be based on general knowledge
        rather than information from the knowledge base.
        
        Args:
            agent_result: The result from agent execution
            conclusion: The extracted conclusion
            
        Returns:
            Boolean indicating if this is likely a general knowledge response
        """
        # Check if any tools found relevant information
        tool_calls = agent_result.get("tool_calls", [])
        if not tool_calls:
            # No tool calls means the agent didn't search the knowledge base
            return True
            
        # Check if tool calls found information
        for call in tool_calls:
            tool = call.get("tool", "")
            result = call.get("result", "")
            
            if tool == "search_kb" and result:
                # Check if the search found no results
                no_info_indicators = [
                    "no relevant information",
                    "couldn't find any",
                    "no information found",
                    "no results",
                    "nothing found",
                    "no matching",
                    "no data",
                    "search returned no"
                ]
                
                if any(indicator in result.lower() for indicator in no_info_indicators):
                    continue  # This search found nothing
                    
                # If we have a substantial result that doesn't indicate no information
                if len(result) > 100:
                    return False  # Found knowledge base info
        
        # Check if the response mentions using expertise or knowledge
        expertise_indicators = [
            "based on my research and expertise",
            "using my expertise",
            "based on my knowledge",
            "no official",
            "according to my understanding",
            "current status",
            "most recent official"
        ]
        
        if any(indicator in conclusion.lower() for indicator in expertise_indicators):
            return True
            
        # Check if any results were found at all
        steps = agent_result.get("steps", [])
        if not steps:
            return True
            
        # Check the results of each step
        for step in steps:
            action = step.get("action", "")
            result = step.get("result", "")
            
            if "search" in action.lower() and result:
                no_info_indicators = [
                    "no relevant information",
                    "couldn't find any",
                    "no information found",
                    "no results", 
                    "nothing found",
                    "no matching",
                    "no data"
                ]
                
                # If result doesn't indicate no information was found
                if not any(indicator in result.lower() for indicator in no_info_indicators):
                    # And it's a substantial result
                    if len(result) > 100:
                        return False  # Found knowledge base info
        
        # Default to assuming it's general knowledge if we can't determine otherwise
        return True