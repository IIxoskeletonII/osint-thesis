"""
Simple test script for document processors.
"""

import os
import sys
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import our classes
from src.data_collection.loaders.text_loader import TextLoader
from src.data_collection.document_processor import process_document

def main():
    print("Testing document processors...")
    
    # Create a test file with security-related content
    test_content = """
    # Security Analysis Report
    
    ## Overview
    This document analyzes the recent vulnerability CVE-2023-1234 that affects multiple systems.
    
    ## Indicators of Compromise
    - IP Address: 192.168.1.100
    - Domain: malicious-domain.com
    - Email: attacker@evil.com
    - MD5 Hash: 5f4dcc3b5aa765d61d8327deb882cf99
    
    ## Mitigation
    Apply the latest security patches and monitor for suspicious connections to 203.0.113.42.
    
    The ransomware attack used a zero-day exploit targeting web servers.
    """
    
    test_file = "security_test.txt"
    
    try:
        # Create the test file
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Load the document
        loader = TextLoader()
        document = loader.load(test_file)
        
        print("\nOriginal document loaded:")
        print(f"Content length: {len(document['content'])} characters")
        
        # Process with default processors
        print("\nProcessing document...")
        processed_doc = process_document(document)
        
        # Print the results
        print("\nProcessing Results:")
        
        # Text processing stats
        if "text_processing_stats" in processed_doc["metadata"]:
            stats = processed_doc["metadata"]["text_processing_stats"]
            print("\nText Processing Stats:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        # Security metadata
        if "security_metadata" in processed_doc["metadata"]:
            security_data = processed_doc["metadata"]["security_metadata"]
            
            print("\nSecurity Metadata:")
            for key, value in security_data.items():
                if key == "indicators":
                    print("  Indicators of Compromise:")
                    for ioc_type, iocs in value.items():
                        print(f"    {ioc_type}: {', '.join(iocs[:3])}{'...' if len(iocs) > 3 else ''}")
                elif key == "cves":
                    print("  CVEs Found:")
                    for cve in value:
                        print(f"    {cve['cve_id']}")
                else:
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