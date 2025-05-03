"""
Test script for the Claude 3.7 integration.
"""

import logging
import os
import sys
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Load environment variables
load_dotenv()

def test_claude_integration():
    """Test the Claude 3.7 integration."""
    print("Testing Claude 3.7 integration...")
    
    # Check if API key is available
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not found in environment variables. Skipping Claude integration test.")
        print("Please add your API key to the .env file to test the integration.")
        return
    
    # Import Claude service
    from src.llm.claude_service import ClaudeService
    
    # Create Claude service
    claude_service = ClaudeService()
    
    # Test basic text generation
    print("\nTesting basic text generation...")
    prompt = "What are common OSINT techniques for cybersecurity research?"
    
    response = claude_service.generate(prompt, max_tokens=250)
    print(f"Claude response: {response}")
    
    # Test tool use capability
    print("\nTesting tool use capability...")
    tools = [
        {
            "name": "extract_entities",
            "description": "Extract security-related entities from text."
        }
    ]
    
    tool_prompt = """
    I need to analyze this text for security-related entities:
    
    The attacker used IP 192.168.1.100 and sent emails from hacker@malicious.com with links to 
    https://malware.example.com. The vulnerability CVE-2023-1234 was exploited.
    """
    
    tool_response = claude_service.generate_with_tools(tool_prompt, tools)
    print("\nClaude tool response:")
    print(f"Text: {tool_response['text']}")
    print("Tool calls:")
    for call in tool_response['tool_calls']:
        print(f"- {call['name']}: {call['input']}")
    
    print("\nClaude integration test completed!")

if __name__ == "__main__":
    test_claude_integration()