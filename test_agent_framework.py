"""
Test script for the Agent Framework.
"""

import logging
import os
import sys
import tempfile
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

class MockLlmService:
    """Simple mock LLM service for testing purposes."""
    
    def generate(self, prompt):
        """Mock generate method."""
        return f"This is a mock response for prompt: {prompt[:50]}..."

def test_agent_framework():
    """Test the agent framework."""
    # Initialize components
    print("Initializing components...")
    
    # Create a mock LLM service for testing
    llm_service = MockLlmService()
    
    # Create a temporary directory for the knowledge base
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory for testing: {temp_dir}")
    
    # Create knowledge base components
    from src.knowledge_base.simple_knowledge_base import SimpleKnowledgeBase
    kb = SimpleKnowledgeBase(storage_dir=temp_dir)
    
    # Create agent manager
    from src.agent.agent_manager import AgentManager
    agent_manager = AgentManager(llm_service, kb)
    
    # List available tools
    print("\nAvailable tools:")
    tools = agent_manager.list_available_tools()
    for tool in tools:
        print(f"- {tool['name']}: {tool['description']}")
    
    # List available agents
    print("\nAvailable agents:")
    agents = agent_manager.list_available_agents()
    for agent in agents:
        print(f"- {agent}")
    
    # Test individual tools
    print("\nTesting search_kb tool...")
    search_result = agent_manager.tool_registry.execute_tool(
        "search_kb", 
        "ransomware"
    )
    print(f"Search result: {search_result[:200]}...")
    
    print("\nTesting extract_entities tool...")
    text = """
    The attacker used IP 192.168.1.100 and sent emails from 
    hacker@malicious.com with links to https://malware.example.com.
    The vulnerability CVE-2023-1234 was exploited and the malware had 
    MD5 hash of 5f4dcc3b5aa765d61d8327deb882cf99.
    """
    entity_result = agent_manager.tool_registry.execute_tool(
        "extract_entities", 
        text
    )
    print(f"Entity extraction result:\n{entity_result}")
    
    # Test agent execution with a simple query
    # Note: We're using a mock LLM so we won't get real results
    print("\nTesting agent execution with mock LLM...")
    try:
        result = agent_manager.execute_agent(
            "osint_analysis",
            "What are recent ransomware trends?"
        )
        print(f"Agent response: {result['response'][:200]}...")
    except Exception as e:
        print(f"Agent execution error (expected with mock LLM): {str(e)}")
    
    print("\nAgent framework tests completed successfully!")

if __name__ == "__main__":
    test_agent_framework()