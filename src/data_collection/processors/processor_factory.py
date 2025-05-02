"""Factory for creating and combining document processors."""

import logging
from typing import Dict, Any, List, Union, Optional

from .base_processor import BaseProcessor
from .text_processor import TextProcessor
from .security_processor import SecurityProcessor

logger = logging.getLogger(__name__)

class ProcessorFactory:
    """Factory for creating document processors."""
    
    @staticmethod
    def get_processor(processor_type: str, processor_name: Optional[str] = None) -> BaseProcessor:
        """
        Get a processor instance based on type.
        
        Args:
            processor_type: Type of processor to create
            processor_name: Optional custom name for the processor
            
        Returns:
            Processor instance
        """
        if processor_type == 'text':
            return TextProcessor(processor_name or "text_processor")
        elif processor_type == 'security':
            return SecurityProcessor(processor_name or "security_processor")
        else:
            logger.warning(f"Unknown processor type: {processor_type}, defaulting to text processor")
            return TextProcessor(processor_name or "unknown_processor")
    
    @staticmethod
    def create_pipeline(processor_configs: List[Dict[str, Any]]) -> 'ProcessorPipeline':
        """
        Create a processor pipeline from configuration.
        
        Args:
            processor_configs: List of processor configurations
                Each configuration should have:
                - 'type': The processor type
                - 'name': Optional custom name for the processor
                - 'params': Optional parameters for processing (passed to process(), not __init__)
            
        Returns:
            Configured processor pipeline
        """
        processors = []
        processor_params = {}
        
        for i, config in enumerate(processor_configs):
            processor_type = config.get('type')
            if not processor_type:
                logger.warning("Processor configuration missing 'type', skipping")
                continue
            
            processor_name = config.get('name')
            params = config.get('params', {})
            
            processor = ProcessorFactory.get_processor(processor_type, processor_name)
            processors.append(processor)
            
            # Store params to use during processing
            if params:
                processor_params[i] = params
        
        return ProcessorPipeline(processors, processor_params)


class ProcessorPipeline:
    """Pipeline for applying multiple processors in sequence."""
    
    def __init__(self, processors: List[BaseProcessor], processor_params: Dict[int, Dict[str, Any]] = None):
        """
        Initialize the processor pipeline.
        
        Args:
            processors: List of processors to apply in sequence
            processor_params: Dictionary mapping processor index to processing parameters
        """
        self.processors = processors
        self.processor_params = processor_params or {}
        self.logger = logging.getLogger(__name__)
    
    def process(self, document: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Process a document through the entire pipeline.
        
        Args:
            document: Document to process
            **kwargs: Default parameters passed to all processors
            
        Returns:
            Processed document
        """
        processed_doc = document
        
        self.logger.info(f"Processing document through pipeline with {len(self.processors)} processors")
        
        for i, processor in enumerate(self.processors):
            try:
                # Combine default params with processor-specific params
                process_kwargs = kwargs.copy()
                if i in self.processor_params:
                    process_kwargs.update(self.processor_params[i])
                
                processed_doc = processor.process(processed_doc, **process_kwargs)
                self.logger.debug(f"Document processed with {processor.processor_name}")
            except Exception as e:
                self.logger.error(f"Error processing document with {processor.processor_name}: {str(e)}")
                # Continue with the next processor rather than failing the entire pipeline
        
        return processed_doc