"""
Claude 3.7 Sonnet integration for the OSINT system.
Provides a service for interacting with Anthropic's Claude API.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional

import anthropic
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ClaudeService:
    """Service for interacting with Claude 3.7 Sonnet."""
    
    def __init__(self, model="claude-3-7-sonnet-20250219"):
        """
        Initialize the Claude service.
        
        Args:
            model: Claude model to use (default is "claude-3-7-sonnet-20250219")
        """
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set. Please set it in your .env file.")
        
        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)
        logger.info(f"Claude service initialized with model: {model}")
        
    def generate(self, prompt: str, max_tokens: int = 4000, temperature: float = 0.7) -> str:
        """
        Generate a response from Claude.
        
        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens to generate in the response
            temperature: Temperature for generation (0.0-1.0, higher is more creative)
            
        Returns:
            Generated text response
        """
        logger.info(f"Generating response with Claude (max_tokens={max_tokens}, temp={temperature})")
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract the text content from the response
            content = response.content[0].text
            logger.info(f"Generated {len(content)} characters")
            return content
            
        except Exception as e:
            logger.error(f"Error generating response from Claude: {str(e)}")
            return f"Error: Failed to generate response from Claude. {str(e)}"
    
    def generate_with_tools(self, prompt: str, tools: List[Dict], max_tokens: int = 4000, temperature: float = 0.7) -> Dict:
        """
        Generate a response from Claude with tool use capability.
        
        Args:
            prompt: The prompt to send to Claude
            tools: List of tool definitions for Claude to use
            max_tokens: Maximum tokens to generate in the response
            temperature: Temperature for generation (0.0-1.0, higher is more creative)
            
        Returns:
            Response including text and any tool calls
        """
        logger.info(f"Generating response with Claude using tools (max_tokens={max_tokens}, temp={temperature})")
        
        try:
            # First, check what version of the anthropic library we're using
            client_version = getattr(anthropic, "__version__", "unknown")
            logger.info(f"Using anthropic library version: {client_version}")
            
            # Create a structured prompt that guides Claude to emulate tool use
            tools_description = "\n\n# Available Tools:\n"
            for i, tool in enumerate(tools):
                tools_description += f"{i+1}. **{tool['name']}**: {tool['description']}\n"
            
            tools_instructions = """
# Instructions for Analysis
1. Analyze the text carefully.
2. Identify which tool would be most appropriate for this task.
3. Show your reasoning for selecting the tool.
4. Indicate clearly which tool you would use in this format: "Using tool: [tool_name]"
5. Then provide a detailed analysis of what the tool would find, being as specific as possible.
"""
            
            enhanced_prompt = f"{prompt}\n\n{tools_description}\n\n{tools_instructions}"
            
            # Use regular API call with enhanced prompt
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": enhanced_prompt}
                ]
            )
            
            # Extract the text content
            response_text = response.content[0].text
            
            # Parse the response to extract tool calls
            tool_calls = []
            
            # Simple parsing to find tool usage
            for tool in tools:
                tool_name = tool["name"]
                if f"Using tool: {tool_name}" in response_text:
                    # Extract the text after the tool usage declaration
                    tool_parts = response_text.split(f"Using tool: {tool_name}", 1)
                    if len(tool_parts) > 1:
                        tool_output = tool_parts[1].strip()
                        # Extract until the next tool declaration or end of text
                        for other_tool in tools:
                            if other_tool["name"] != tool_name and f"Using tool: {other_tool['name']}" in tool_output:
                                tool_output = tool_output.split(f"Using tool: {other_tool['name']}", 1)[0].strip()
                        
                        tool_calls.append({
                            "name": tool_name,
                            "input": tool_output
                        })
            
            logger.info(f"Emulated {len(tool_calls)} tool calls from the response")
            
            return {
                "text": response_text,
                "tool_calls": tool_calls
            }
            
        except Exception as e:
            logger.error(f"Error generating response with tools from Claude: {str(e)}")
            return {
                "text": f"Error: Failed to generate response from Claude. {str(e)}",
                "tool_calls": []
            }