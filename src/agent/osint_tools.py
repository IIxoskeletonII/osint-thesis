"""
OSINT-specific tools for the agent framework.
Provides specialized tools for intelligence gathering and analysis.
"""

import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.knowledge_base.simple_knowledge_base import SimpleKnowledgeBase

logger = logging.getLogger(__name__)

def search_knowledge_base(knowledge_base, input_data: str) -> str:
    """
    Search the knowledge base for relevant documents.
    
    Args:
        knowledge_base: KnowledgeBase instance
        input_data: Search query
        
    Returns:
        Formatted string with search results
    """
    try:
        # Parse input to get query and optional parameters
        query = input_data
        limit = 3  # Default limit
        
        # Check if input contains JSON with additional parameters
        if input_data.startswith('{') and input_data.endswith('}'):
            try:
                params = json.loads(input_data)
                query = params.get('query', '')
                limit = params.get('limit', 3)
            except:
                # If JSON parsing fails, treat the entire input as the query
                query = input_data
        
        # Perform the search
        results = knowledge_base.search(query, limit=limit)
        
        if not results:
            return "No relevant documents found."
        
        # Format the results
        response = f"Found {len(results)} relevant documents:\n\n"
        
        for i, doc in enumerate(results):
            source = doc.metadata.get('source', 'Unknown Source')
            doc_type = doc.metadata.get('doc_type', 'Unknown Type')
            
            response += f"Document {i+1}:\n"
            response += f"Source: {source}\n"
            response += f"Type: {doc_type}\n"
            response += f"Content: {doc.page_content[:300]}{'...' if len(doc.page_content) > 300 else ''}\n\n"
        
        return response
    except Exception as e:
        logger.error(f"Error in search_knowledge_base: {str(e)}")
        return f"Error searching knowledge base: {str(e)}"

def extract_entities(input_data: str) -> str:
    """
    Extract potential security-related entities from text.
    This is a simple pattern-based implementation.
    
    Args:
        input_data: Text to analyze
        
    Returns:
        Extracted entities as formatted string
    """
    try:
        # Define patterns for common security entities
        patterns = {
            'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'url': r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*',
            'cve': r'CVE-\d{4}-\d{4,7}',
            'hash_md5': r'\b[a-fA-F0-9]{32}\b',
            'hash_sha1': r'\b[a-fA-F0-9]{40}\b',
            'hash_sha256': r'\b[a-fA-F0-9]{64}\b',
        }
        
        # Extract entities
        entities = {}
        for entity_type, pattern in patterns.items():
            matches = re.findall(pattern, input_data)
            if matches:
                entities[entity_type] = list(set(matches))  # Remove duplicates
        
        if not entities:
            return "No security-related entities found in the text."
        
        # Format the results
        response = "Extracted security-related entities:\n\n"
        
        for entity_type, items in entities.items():
            response += f"{entity_type.replace('_', ' ').title()}:\n"
            for item in items:
                response += f"- {item}\n"
            response += "\n"
        
        return response
    except Exception as e:
        logger.error(f"Error in extract_entities: {str(e)}")
        return f"Error extracting entities: {str(e)}"

def analyze_relationships(input_data: str) -> str:
    """
    Analyze potential relationships between entities.
    This is a placeholder for a more sophisticated implementation.
    
    Args:
        input_data: JSON string with entities to analyze
        
    Returns:
        Analysis results as formatted string
    """
    try:
        # Parse input data
        try:
            data = json.loads(input_data)
            entities = data.get('entities', [])
        except:
            return "Error: Input must be a JSON string with an 'entities' list."
        
        if not entities:
            return "No entities provided for relationship analysis."
        
        # This is a simplified placeholder implementation
        # In a real system, this would use graph analysis or other techniques
        response = "Relationship Analysis:\n\n"
        response += "This is a simple placeholder analysis. In a production system, "
        response += "this would perform graph-based entity relationship analysis.\n\n"
        
        response += f"Identified {len(entities)} entities for analysis.\n"
        response += "Potential relationships would be identified based on:\n"
        response += "- Co-occurrence in documents\n"
        response += "- Temporal proximity\n"
        response += "- Known relationship patterns\n"
        response += "- Contextual analysis\n\n"
        
        response += "For demonstration purposes, here are the provided entities:\n"
        for i, entity in enumerate(entities):
            response += f"{i+1}. {entity}\n"
        
        return response
    except Exception as e:
        logger.error(f"Error in analyze_relationships: {str(e)}")
        return f"Error analyzing relationships: {str(e)}"

def create_timeline(input_data: str) -> str:
    """
    Create a timeline from events.
    
    Args:
        input_data: JSON string with events to analyze
        
    Returns:
        Timeline as formatted string
    """
    try:
        # Parse input data
        try:
            data = json.loads(input_data)
            events = data.get('events', [])
        except:
            return "Error: Input must be a JSON string with an 'events' list. Each event should have 'date' and 'description' fields."
        
        if not events:
            return "No events provided for timeline creation."
        
        # Validate events
        valid_events = []
        for event in events:
            if isinstance(event, dict) and 'date' in event and 'description' in event:
                valid_events.append(event)
        
        if not valid_events:
            return "No valid events found. Each event must have 'date' and 'description' fields."
        
        # Sort events by date
        # This is a simple implementation; a production system would have more robust date parsing
        try:
            sorted_events = sorted(valid_events, key=lambda x: x['date'])
        except:
            return "Error sorting events. Ensure dates are in a consistent format."
        
        # Format the timeline
        response = "Timeline of Events:\n\n"
        
        for event in sorted_events:
            response += f"{event['date']}: {event['description']}\n"
        
        return response
    except Exception as e:
        logger.error(f"Error in create_timeline: {str(e)}")
        return f"Error creating timeline: {str(e)}"