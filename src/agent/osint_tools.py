"""
OSINT-specific tools for the agent framework.
Provides specialized tools for intelligence gathering and analysis.
"""

import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

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
        limit = 5  # Default limit
        
        # Check if input contains JSON with additional parameters
        if input_data.startswith('{') and input_data.endswith('}'):
            try:
                params = json.loads(input_data)
                query = params.get('query', '')
                limit = params.get('limit', 5)
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
            # Handle different document structures
            # Some documents might be dictionaries directly
            if isinstance(doc, dict):
                doc_id = doc.get('id', f'Document {i+1}')
                source = doc.get('source', 'Unknown Source')
                doc_type = doc.get('type', 'Unknown Type')
                content = doc.get('content', '')
                
                if isinstance(content, dict):
                    # Handle nested content
                    content_str = str(content)
                else:
                    content_str = str(content)
                
                response += f"Document {i+1} (ID: {doc_id}):\n"
                response += f"Source: {source}\n"
                response += f"Type: {doc_type}\n"
                response += f"Content: {content_str[:300]}{'...' if len(content_str) > 300 else ''}\n\n"
            else:
                # Try to extract information based on common document attributes
                doc_id = getattr(doc, 'id', f'Document {i+1}')
                
                # Try different ways to access content
                if hasattr(doc, 'page_content'):
                    content = doc.page_content
                elif hasattr(doc, 'content'):
                    content = doc.content
                else:
                    content = str(doc)
                
                # Try to access metadata
                if hasattr(doc, 'metadata'):
                    metadata = doc.metadata
                    source = metadata.get('source', 'Unknown Source')
                    doc_type = metadata.get('doc_type', 'Unknown Type')
                else:
                    source = 'Unknown Source'
                    doc_type = 'Unknown Type'
                
                response += f"Document {i+1} (ID: {doc_id}):\n"
                response += f"Source: {source}\n"
                response += f"Type: {doc_type}\n"
                response += f"Content: {content[:300]}{'...' if len(content) > 300 else ''}\n\n"
        
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
        except Exception as e: # Catch broader exceptions during parsing
            # Make error more informative
            return f"Error: Input must be a valid JSON string containing an 'entities' list. Parsing failed: {str(e)}"

        if not entities or not isinstance(entities, list):
             # Make error more informative
            return "Error: No valid 'entities' list found in the provided JSON input."
        
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
            # Check if 'events' key exists and is a list
            if 'events' not in data or not isinstance(data['events'], list):
                 raise ValueError("Input JSON must contain an 'events' key with a list value.")
            events = data['events']
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received in create_timeline: {input_data[:100]}... Error: {e}")
            return f"Error: Input must be a valid JSON string. Parsing failed: {str(e)}"
        except ValueError as e: # Catch specific check error
            logger.error(f"Invalid data structure in create_timeline: {str(e)}")
            return f"Error: {str(e)}"
        except Exception as e: # Catch other potential errors during loading/parsing
            logger.error(f"Unexpected error parsing input for create_timeline: {e}")
            return f"Error: Could not parse input JSON for timeline: {str(e)}"


        if not events:
            return "No events provided in the input JSON for timeline creation."

        # Validate events
        valid_events = []
        invalid_event_found = False
        for i, event in enumerate(events):
            if isinstance(event, dict) and 'date' in event and 'description' in event:
                # Basic date validation placeholder - more robust parsing could be added
                if isinstance(event['date'], str) and isinstance(event['description'], str):
                     valid_events.append(event)
                else:
                     logger.warning(f"Event {i} has invalid data types for date/description.")
                     invalid_event_found = True
            else:
                logger.warning(f"Event {i} is missing 'date' or 'description' field.")
                invalid_event_found = True

        if not valid_events:
             if invalid_event_found:
                 return "Error: No valid events found in the input list. Each event must be an object with 'date' and 'description' strings."
             else: # Should not happen if events list was not empty, but good safety check
                 return "No processable events found."


        try:
            # Attempt to parse dates for better sorting, fallback to string sort
            def get_sort_key(ev):
                try:
                    # Attempt ISO format parsing first
                    return datetime.fromisoformat(ev['date'].replace('Z', '+00:00'))
                except ValueError:
                    # Fallback to simple string sorting if parsing fails
                    return ev['date']

            sorted_events = sorted(valid_events, key=get_sort_key)
        except Exception as e:
            logger.warning(f"Could not reliably sort events by date due to parsing issues ({e}), using basic string sort.")
            # Fallback to basic string sort if date parsing/comparison fails
            sorted_events = sorted(valid_events, key=lambda x: x['date'])


        # Format the timeline
        response = "Timeline of Events:\n\n"

        for event in sorted_events:
            # Ensure values are strings before formatting
            date_str = str(event.get('date', 'Unknown Date'))
            desc_str = str(event.get('description', 'No Description'))
            response += f"{date_str}: {desc_str}\n"

        if invalid_event_found:
             response += "\nNote: Some events in the input list were invalid or incomplete and were skipped."

        return response
    except Exception as e:
        logger.error(f"Error in create_timeline function: {str(e)}", exc_info=True)
        return f"Error creating timeline: {str(e)}"