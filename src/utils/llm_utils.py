"""Utilities for LLM interactions in the OSINT system."""
from typing import Any, Dict, List, Optional, Union
import json
import time

from anthropic import Anthropic
from config.config import LLM_CONFIG, logger

def initialize_llm_client() -> Anthropic:
    """
    Initialize the Anthropic client with the API key from configuration.
    
    Returns:
        Initialized Anthropic client
    """
    if not LLM_CONFIG.get("api_key"):
        raise ValueError("Anthropic API key is not set in configuration")
    
    return Anthropic(api_key=LLM_CONFIG["api_key"])


def extract_json_from_llm_response(response: str) -> Dict[str, Any]:
    """
    Extract JSON data from an LLM response.
    
    Args:
        response: The raw LLM response text
        
    Returns:
        Extracted JSON data as a dictionary
        
    Raises:
        ValueError: If no valid JSON could be extracted
    """
    # Find JSON blocks in markdown format
    json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    import re
    matches = re.findall(json_pattern, response)
    
    if matches:
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    # Try extracting JSON without markdown formatting
    try:
        # Look for first { and last }
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = response[start_idx:end_idx+1]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    
    raise ValueError("Could not extract valid JSON from LLM response")


def create_retry_decorator(max_retries: int = 3, 
                           initial_delay: float = 1.0,
                           backoff_factor: float = 2.0):
    """
    Create a decorator for retrying LLM API calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay with each retry
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"API call failed: {str(e)}")
                    retries += 1
                    
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded. Raising error.")
                        raise
                    
                    sleep_time = delay * (backoff_factor ** (retries - 1))
                    logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
        
        return wrapper
    
    return decorator


def format_prompt_with_context(query: str, 
                              context: List[Dict[str, Any]],
                              system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Format a prompt with context for the Claude LLM.
    
    Args:
        query: The user's query
        context: List of context documents with text and metadata
        system_prompt: Optional system prompt to override default
        
    Returns:
        Formatted messages for Claude API
    """
    if system_prompt is None:
        system_prompt = """You are an expert OSINT (Open Source Intelligence) analyst specializing in cybersecurity intelligence.
You analyze provided intelligence information and respond to queries with accurate, well-reasoned answers.
Always cite your sources when providing information from the context.
If you're unsure or don't have enough information, acknowledge the limitations in your response."""
    
    # Format context documents
    formatted_context = ""
    for i, doc in enumerate(context):
        source = doc.get('metadata', {}).get('source', f"Document {i+1}")
        formatted_context += f"\n\nSOURCE: {source}\n{doc['text']}\n"
    
    # Build the messages
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": f"Context information is below.\n{formatted_context}\n\nQuery: {query}\n\nPlease provide a detailed answer based on the context information provided."
        }
    ]
    
    return messages