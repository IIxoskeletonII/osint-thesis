"""
LLM service module for the OSINT system.
Provides integration with Claude 3.7 Sonnet for intelligence analysis.
"""

from .claude_service import ClaudeService

__all__ = ['ClaudeService']