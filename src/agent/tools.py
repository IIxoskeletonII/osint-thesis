"""
Tools implementation for the OSINT system agents.
Provides a standardized interface for creating and using tools.
"""

import logging
from typing import Dict, Any, Callable, List

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Registry for tools that can be used by agents."""
    
    def __init__(self):
        """Initialize an empty tool registry."""
        self.tools = {}
        
    def register_tool(self, name: str, description: str, func: Callable):
        """
        Register a new tool in the registry.
        
        Args:
            name: Tool name (must be unique)
            description: Tool description
            func: Function that implements the tool
        """
        if name in self.tools:
            logger.warning(f"Tool '{name}' already exists and will be overwritten")
            
        self.tools[name] = {
            "name": name,
            "description": description,
            "function": func
        }
        logger.info(f"Registered tool: {name}")
        
    def get_tool(self, name: str) -> Dict:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool definition dictionary
            
        Raises:
            KeyError: If tool does not exist
        """
        if name not in self.tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self.tools[name]
    
    def list_tools(self) -> List[Dict]:
        """
        List all available tools.
        
        Returns:
            List of tool definitions
        """
        return [
            {"name": name, "description": details["description"]}
            for name, details in self.tools.items()
        ]
    
    def execute_tool(self, name: str, input_data: Any) -> Any:
        """
        Execute a tool with the given input.
        
        Args:
            name: Tool name
            input_data: Input data for the tool
            
        Returns:
            Tool execution result
            
        Raises:
            KeyError: If tool does not exist
        """
        tool = self.get_tool(name)
        logger.info(f"Executing tool: {name}")
        try:
            result = tool["function"](input_data)
            return result
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {str(e)}")
            return f"Error: {str(e)}"