"""
Agent module for the OSINT system.
Provides agent functionality for autonomous intelligence gathering and analysis.
"""

from .base_agent import BaseAgent
from .tools import ToolRegistry
from .osint_agent import OsintAnalysisAgent
from .agent_manager import AgentManager
from .osint_tools import search_knowledge_base, extract_entities, analyze_relationships, create_timeline

__all__ = [
    'BaseAgent',
    'ToolRegistry',
    'OsintAnalysisAgent', 
    'AgentManager',
    'search_knowledge_base',
    'extract_entities',
    'analyze_relationships',
    'create_timeline'
]