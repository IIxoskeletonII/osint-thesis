"""
Test script for the data collection pipeline.
"""

import os
import sys
import logging
import json
from datetime import datetime

# Configure basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import our CollectionPipeline
from src.data_collection.collection_pipeline import CollectionPipeline

def main():
    print("Testing collection pipeline...")
    
    # Create a temp directory for outputs
    output_dir = "test_collection_output"
    os.makedirs(output_dir, exist_ok=True)
    
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
        
        # Create a simple text file
        with open("simple_test.txt", 'w', encoding='utf-8') as f:
            f.write("This is a simple test document without security content.")
        
        # Initialize the collection pipeline
        pipeline = CollectionPipeline(output_dir)
        
        # Define processor configs with security focus
        processor_configs = [
            {'type': 'text', 'params': {'normalize_whitespace': True}},
            {'type': 'security', 'params': {'extract_indicators': True, 'score_security_relevance': True}}
        ]
        
        # Collect from multiple sources
        source_paths = [test_file, "simple_test.txt"]
        source_names = ["security_document", "simple_document"]
        
        print("\nCollecting from sources...")
        results = pipeline.collect_from_sources(
            source_paths=source_paths,
            source_names=source_names,
            processor_configs=processor_configs
        )
        
        # Generate and save a report
        report = pipeline.generate_collection_report(results)
        report_path = pipeline.save_collection_report(report)
        
        # Print results
        print("\nCollection Results:")
        for i, result in enumerate(results):
            print(f"\nSource {i+1}: {result['source_path']}")
            print(f"  Status: {result['status']}")
            print(f"  Collection ID: {result['collection_id']}")
            if result['status'] == 'success':
                print(f"  Source Type: {result['source_type']}")
                
                # Load and print some information from the processed document
                with open(result['processed_file'], 'r', encoding='utf-8') as f:
                    processed_doc = json.load(f)
                
                # Print security relevance if available
                if "security_metadata" in processed_doc["metadata"]:
                    security_metadata = processed_doc["metadata"]["security_metadata"]
                    if "security_relevance_score" in security_metadata:
                        print(f"  Security Relevance: {security_metadata['security_relevance_score']}")
                    
                    # Print indicators if available
                    if "indicators" in security_metadata:
                        indicators = security_metadata["indicators"]
                        indicator_count = sum(len(iocs) for iocs in indicators.values())
                        print(f"  Indicators Found: {indicator_count}")
        
        print(f"\nCollection report saved to: {report_path}")
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Clean up test files
        if os.path.exists(test_file):
            os.remove(test_file)
        if os.path.exists("simple_test.txt"):
            os.remove("simple_test.txt")
        
        print("\nTest files cleaned up.")

if __name__ == "__main__":
    main()