"""
Simple test script for the text loader.
This script tests the TextLoader directly without using relative imports.
"""

import os
import sys
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add the project directory to the Python path to allow absolute imports
sys.path.insert(0, os.path.abspath('.'))

# Import our TextLoader class
from src.data_collection.loaders.text_loader import TextLoader

def main():
    print("Testing TextLoader...")
    
    # Create a test file
    test_content = "This is a test document.\nIt has multiple lines.\nEnd of test."
    test_file = "test_document.txt"
    
    try:
        # Create the test file
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Create a TextLoader and load the document
        loader = TextLoader()
        document = loader.load(test_file)
        
        # Print the results
        print("\nResults:")
        print(f"Content: {document['content']}")
        print("\nMetadata:")
        for key, value in document['metadata'].items():
            print(f"  {key}: {value}")
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    main()