import logging
import os
import sys
import unittest
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
if str(src_path.absolute()) not in sys.path:
    sys.path.append(str(src_path.absolute()))

from src.chatbot.query_processor import QueryProcessor
from src.chatbot.response_generator import ResponseGenerator
from src.chatbot.chatbot_interface import ChatbotInterface

class TestQueryProcessor(unittest.TestCase):
    """Test cases for the QueryProcessor class."""
    
    def setUp(self):
        self.processor = QueryProcessor()
        
    def test_query_type_detection(self):
        """Test that query types are correctly detected."""
        # Test informational queries
        info_query = "What is CVE-2021-44228?"
        result = self.processor.process_query(info_query, [])
        self.assertEqual(result["query_type"], "informational")
        
        # Test analytical queries
        analytical_query = "Analyze the relationship between recent ransomware attacks"
        result = self.processor.process_query(analytical_query, [])
        self.assertEqual(result["query_type"], "analytical")
        
        # Test procedural queries
        procedural_query = "How do I set up a secure VPN?"
        result = self.processor.process_query(procedural_query, [])
        self.assertEqual(result["query_type"], "procedural")
    
    def test_entity_extraction(self):
        """Test that entities are correctly extracted from queries."""
        query = "What is CVE-2021-44228 and how does it relate to Log4j?"
        result = self.processor.process_query(query, [])
        
        # Print entities to help debug
        print(f"Extracted entities: {result['entities']}")
        
        # Check that the CVE ID was extracted
        self.assertIn("CVE-2021-44228", result["entities"])
        
        # Check that Log4j was extracted as a potential named entity
        self.assertIn("Log4j", result["entities"])

class TestResponseGenerator(unittest.TestCase):
    """Test cases for the ResponseGenerator class."""
    
    def setUp(self):
        self.generator = ResponseGenerator()
    
    def test_fallback_response(self):
        """Test that fallback responses are generated correctly."""
        query_result = {"query_type": "informational", "original_query": "What is XYZ?"}
        response = self.generator._generate_fallback_response(query_result)
        
        # Check that a response was generated
        self.assertIsNotNone(response["response"])
        
        # Check that it's marked as a fallback
        self.assertEqual(response["type"], "fallback")
    
    def test_rag_response_formatting(self):
        """Test that RAG responses are formatted correctly."""
        query_result = {"query_type": "informational"}
        rag_result = {
            "response": "XYZ is a security concept.",
            "documents": [
                {"title": "Security Basics", "source": "Internal KB", "score": 0.85}
            ]
        }
        
        response = self.generator._format_rag_response(query_result, rag_result)
        
        # Check that the response includes the RAG result
        self.assertIn("XYZ is a security concept", response["response"])
        
        # Check that sources are included
        self.assertIn("Security Basics", response["response"])

class TestChatbotInterface(unittest.TestCase):
    """Test cases for the ChatbotInterface class."""
    
    def setUp(self):
        # Initialize with mock components
        self.chatbot = ChatbotInterface()
    
    def test_conversation_history(self):
        """Test that conversation history is correctly managed."""
        # Add messages
        self.chatbot.add_message("user", "Hello")
        self.chatbot.add_message("system", "Hi there")
        
        # Check history length
        history = self.chatbot.get_conversation_history()
        self.assertEqual(len(history), 2)
        
        # Check message content
        self.assertEqual(history[0]["content"], "Hello")
        self.assertEqual(history[1]["content"], "Hi there")
        
        # Test clear functionality
        self.chatbot.clear_conversation()
        self.assertEqual(len(self.chatbot.get_conversation_history()), 0)

if __name__ == "__main__":
    unittest.main()