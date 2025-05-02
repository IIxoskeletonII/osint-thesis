"""Data collection pipeline for OSINT data sources."""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

from src.data_collection.loaders.loader_factory import LoaderFactory
from src.data_collection.document_processor import process_document

logger = logging.getLogger(__name__)

class CollectionPipeline:
    """Pipeline for collecting and processing documents from various sources."""
    
    def __init__(self, output_dir: str):
        """
        Initialize the collection pipeline.
        
        Args:
            output_dir: Directory to store collected documents
        """
        self.output_dir = output_dir
        self.raw_dir = os.path.join(output_dir, 'raw')
        self.processed_dir = os.path.join(output_dir, 'processed')
        
        # Create directories if they don't exist
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
    
    def collect_from_source(self, source_path: str, source_name: Optional[str] = None, 
                          processor_configs: Optional[List[Dict[str, Any]]] = None,
                          loader_kwargs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Collect and process a document from a single source.
        
        Args:
            source_path: Path or URL to the document
            source_name: Optional name for the source
            processor_configs: List of processor configurations
            loader_kwargs: Additional parameters for the loader
            
        Returns:
            Dictionary with information about the collection results
        """
        start_time = datetime.now()
        loader_kwargs = loader_kwargs or {}
        
        self.logger.info(f"Collecting from source: {source_path}")
        
        # Create a unique ID for this collection
        collection_id = f"{int(start_time.timestamp())}_{os.path.basename(source_path) if os.path.exists(source_path) else 'web'}"
        
        try:
            # Load the document
            loader = LoaderFactory.get_loader(source_path, source_name)
            document = loader.load(source_path, **loader_kwargs)
            
            # Save the raw document
            raw_file_path = os.path.join(self.raw_dir, f"{collection_id}_raw.json")
            with open(raw_file_path, 'w', encoding='utf-8') as f:
                json.dump(document, f, indent=2, ensure_ascii=False)
            
            # Process the document
            processed_document = process_document(document, processor_configs)
            
            # Save the processed document
            processed_file_path = os.path.join(self.processed_dir, f"{collection_id}_processed.json")
            with open(processed_file_path, 'w', encoding='utf-8') as f:
                json.dump(processed_document, f, indent=2, ensure_ascii=False)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "status": "success",
                "collection_id": collection_id,
                "source_path": source_path,
                "source_type": processed_document["metadata"]["source_type"],
                "raw_file": raw_file_path,
                "processed_file": processed_file_path,
                "duration_seconds": duration,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting from {source_path}: {str(e)}")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "status": "failed",
                "collection_id": collection_id,
                "source_path": source_path,
                "error": str(e),
                "duration_seconds": duration,
                "timestamp": end_time.isoformat()
            }
    
    def collect_from_sources(self, source_paths: List[str], 
                           source_names: Optional[List[str]] = None,
                           processor_configs: Optional[List[Dict[str, Any]]] = None,
                           loader_kwargs: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Collect and process documents from multiple sources.
        
        Args:
            source_paths: List of paths or URLs to the documents
            source_names: Optional list of names for the sources
            processor_configs: List of processor configurations
            loader_kwargs: Additional parameters for the loaders
            
        Returns:
            List of dictionaries with information about each collection result
        """
        results = []
        
        for i, source_path in enumerate(source_paths):
            source_name = None
            if source_names and i < len(source_names):
                source_name = source_names[i]
                
            result = self.collect_from_source(
                source_path=source_path,
                source_name=source_name,
                processor_configs=processor_configs,
                loader_kwargs=loader_kwargs
            )
            
            results.append(result)
            
        return results
    
    def generate_collection_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary report of collection results.
        
        Args:
            results: List of collection results
            
        Returns:
            Dictionary with summary information
        """
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] == "failed"]
        
        source_types = {}
        for result in successful:
            source_type = result.get("source_type")
            if source_type:
                source_types[source_type] = source_types.get(source_type, 0) + 1
        
        total_duration = sum(r.get("duration_seconds", 0) for r in results)
        
        return {
            "total_sources": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "source_types": source_types,
            "total_duration_seconds": total_duration,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_collection_report(self, report: Dict[str, Any], filename: str = "collection_report.json") -> str:
        """
        Save a collection report to a file.
        
        Args:
            report: Collection report to save
            filename: Name of the file to save to
            
        Returns:
            Path to the saved report file
        """
        report_path = os.path.join(self.output_dir, filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        return report_path