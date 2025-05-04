"""
Test script for the Agent Framework, using real KB and LLM components.
"""

import logging
import os
import sys
# import tempfile # No longer needed for KB
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__) # Added logger instance

# Add the src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '.')) # Assumes script is in root
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


# Load environment variables
load_dotenv()

# Import Real Services
try:
    from src.llm.claude_service import ClaudeService
    from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager
    from src.agent.agent_manager import AgentManager
except ImportError as e:
     logger.error(f"Import Error: {e}. Ensure the script is run from the project root or src is in PYTHONPATH.")
     sys.exit(1)


def test_agent_framework():
    """Test the agent framework with real components."""
    # Initialize components
    logger.info("Initializing components...") # Use logger

    # --- Use Real LLM Service ---
    logger.info("Initializing ClaudeService...") # Use logger
    try:
        # Requires ANTHROPIC_API_KEY in .env
        llm_service = ClaudeService()
    except ValueError as e:
        logger.error(f"Error initializing ClaudeService: {e}")
        logger.error("Agent execution test requiring LLM will fail. Ensure ANTHROPIC_API_KEY is set in .env")
        return # Exit if LLM is required and cannot be initialized
    except Exception as e:
        logger.error(f"Unexpected error initializing ClaudeService: {e}", exc_info=True)
        return

    logger.info("Initializing Knowledge Base Manager for 'data' directory...") # Use logger
    try:
        # Use the populated KB in 'data/knowledge_base/'
        kb_manager = KnowledgeBaseManager(
             base_dir="data",
             chunker_type="security",      # Match ingestion settings
             embedding_type="security",    # Match ingestion settings
             storage_type="simple"         # Match ingestion settings
        )
        # Verify KB has content
        stats = kb_manager.get_stats()
        logger.info(f"KB Stats: {stats['document_count']} docs, {stats['chunk_count']} chunks")
        if stats['document_count'] == 0 or stats['chunk_count'] == 0:
            logger.warning("Knowledge Base appears empty. Agent tests might not find data.")
            logger.warning("Run collectors and ingest_documents.py first.")

    except Exception as e:
        logger.error(f"Failed to initialize KnowledgeBaseManager: {e}", exc_info=True)
        return

    # --- Use Real Agent Manager ---
    logger.info("Initializing AgentManager...") # Use logger
    try:
        # Pass the real llm_service and kb_manager
        agent_manager = AgentManager(llm_service, kb_manager)
    except Exception as e:
        logger.error(f"Failed to initialize AgentManager: {e}", exc_info=True)
        return

    # List available tools (remains the same)
    logger.info("\nAvailable tools:") # Use logger
    tools = agent_manager.list_available_tools()
    for tool in tools:
        logger.info(f"- {tool['name']}: {tool['description']}") # Use logger

    # List available agents (remains the same)
    logger.info("\nAvailable agents:") # Use logger
    agents = agent_manager.list_available_agents()
    for agent in agents:
        logger.info(f"- {agent}") # Use logger

    # --- Skip Direct Tool Test for search_kb ---
    logger.info("\nTesting search_kb tool...") # Use logger
    logger.info("Direct search_kb tool test skipped (will be tested via agent execution).") # Use logger

    # Test extract_entities tool (remains the same)
    logger.info("\nTesting extract_entities tool...") # Use logger
    text_to_extract = """
    The attacker used IP 192.168.1.100 and sent emails from
    hacker@malicious.com with links to https://malware.example.com.
    The vulnerability CVE-2023-1234 was exploited and the malware had
    MD5 hash of 5f4dcc3b5aa765d61d8327deb882cf99.
    """
    try:
        entity_result = agent_manager.tool_registry.execute_tool(
            "extract_entities",
            text_to_extract
        )
        logger.info(f"Entity extraction result:\n{entity_result}") # Use logger
    except Exception as e:
         logger.error(f"Error testing extract_entities tool: {e}", exc_info=True)


    # --- Test Agent Execution with REAL LLM and KB ---
    logger.info("\nTesting agent execution with REAL LLM and KB...") # Use logger

    # Example Query 1: Requires searching the KB
    agent_query_kb = "What can you tell me about CVE-2025-1234 based on the knowledge base?"
    logger.info(f"\nExecuting Agent Query 1: '{agent_query_kb}'")
    try:
        result_kb = agent_manager.execute_agent(
            "osint_analysis", # Use the ReAct-style agent first
            agent_query_kb
        )
        logger.info("\n--- Agent Execution Result (KB Query) ---")
        logger.info(f"Query: {result_kb.get('query')}")
        logger.info(f"Response:\n{result_kb.get('response', 'No response field found.')}")
        logger.info("--- End Agent Execution Result ---")
    except Exception as e:
        logger.error(f"Agent execution failed for KB query: {str(e)}", exc_info=True) # Log full traceback on error

    # Example Query 2: More analytical, might use multiple tools or steps
    agent_query_analytical = "Analyze APT29's common attack methods mentioned in the data."
    logger.info(f"\nExecuting Agent Query 2: '{agent_query_analytical}'")
    try:
        result_analytical = agent_manager.execute_agent(
            "osint_analysis", # Or try "claude_analysis" if you want to compare
            agent_query_analytical
        )
        logger.info("\n--- Agent Execution Result (Analytical Query) ---")
        logger.info(f"Query: {result_analytical.get('query')}")
        logger.info(f"Response:\n{result_analytical.get('response', 'No response field found.')}")
        logger.info("--- End Agent Execution Result ---")
    except Exception as e:
         logger.error(f"Agent execution failed for analytical query: {str(e)}", exc_info=True)

    logger.info("\nAgent framework integration tests completed!") # Use logger

if __name__ == "__main__":
    test_agent_framework()