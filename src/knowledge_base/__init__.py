"""
Knowledge Base package for OSINT thesis project.
"""

from src.knowledge_base.simple_knowledge_base import SimpleKnowledgeBase
from src.knowledge_base.chunking import get_chunker
from src.knowledge_base.embedding import get_embedding_generator
from src.knowledge_base.storage import get_vector_storage
from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager

__all__ = [
    'SimpleKnowledgeBase',
    'get_chunker',
    'get_embedding_generator',
    'get_vector_storage',
    'KnowledgeBaseManager'
]