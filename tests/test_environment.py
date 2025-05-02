"""Test the environment setup for the OSINT system."""
import unittest
import importlib
import os
import sys


class TestEnvironment(unittest.TestCase):
    """Test the environment setup."""
    
    def test_dependencies_installed(self):
        """Test that required dependencies are installed."""
        required_modules = [
            'langchain',
            'langchain_core',
            'langchain_community',
            'langchain_anthropic',
            'anthropic',
            'dotenv',
        ]
        
        for module_name in required_modules:
            try:
                importlib.import_module(module_name)
            except ImportError:
                self.fail(f"Required module {module_name} is not installed")
    
    def test_environment_variables(self):
        """Test that required environment variables are set."""
        # Check if .env file exists
        self.assertTrue(os.path.exists('.env'), 
                        "Environment file (.env) is missing")
        
        # Import dotenv and load variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check if ANTHROPIC_API_KEY is set
        self.assertIsNotNone(os.getenv('ANTHROPIC_API_KEY'), 
                            "ANTHROPIC_API_KEY is not set in .env file")
    
    def test_directory_structure(self):
        """Test that the project directory structure is correct."""
        required_dirs = [
            'src',
            'src/utils',
            'src/data_collection',
            'src/knowledge_base',
            'src/rag',
            'src/agent',
            'src/chatbot',
            'src/integration',
            'data',
            'data/raw',
            'data/processed',
            'config',
            'tests',
        ]
        
        for dir_path in required_dirs:
            self.assertTrue(os.path.isdir(dir_path), 
                           f"Required directory {dir_path} is missing")


if __name__ == "__main__":
    unittest.main()