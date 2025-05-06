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
        knowledge_base: KnowledgeBase instance (likely KnowledgeBaseManager)
        input_data: Search query string (potentially JSON containing query and limit)

    Returns:
        Formatted string with search results for the Observation step,
        including document ID and original document path for better traceability.
    """
    try:
        query = input_data
        limit = 5  # Default limit for the tool search

        if input_data.strip().startswith('{') and input_data.strip().endswith('}'):
            try:
                params = json.loads(input_data)
                query = params.get('query', query)
                limit = params.get('limit', limit)
                logger.debug(f"Parsed JSON input: query='{query}', limit={limit}")
            except json.JSONDecodeError:
                logger.warning("Input looked like JSON but failed to parse. Treating entire string as query.")
                query = input_data # Ensure query is set back correctly
                limit = 5 # Reset limit to default

        if not query:
             return "Error: No query provided for knowledge base search."

        results = knowledge_base.search(query, limit=limit)

        if not results:
            return "No relevant documents found in the knowledge base for this query."

        response_parts = [f"Found {len(results)} relevant document(s):"]

        for i, result_item in enumerate(results):
            doc_id = result_item.get("id", f"Result_{i+1}") # This is usually the chunk_id
            similarity = result_item.get("similarity", 0.0)
            
            doc_data = result_item.get('document', {})
            doc_content_dict = doc_data.get('content', {})
            doc_metadata = doc_data.get('metadata', {})

            source = doc_metadata.get('source_name', 'Unknown Source') # Original source name (e.g., filename before ingestion)
            doc_type = doc_metadata.get('source_type', 'Unknown Type') # Original source type (e.g., 'vulnerability', 'research')
            title = doc_content_dict.get('title', f'Document {doc_id}') 
            
            # Extract text content robustly
            content_text_parts = []
            if isinstance(doc_content_dict, dict):
                preferred_fields = ['description', 'summary', 'abstract', 'text', 'content']
                main_content_found = False
                for field in preferred_fields:
                    if field in doc_content_dict and isinstance(doc_content_dict[field], str) and doc_content_dict[field].strip():
                        content_text_parts.append(doc_content_dict[field])
                        main_content_found = True
                        break 
                
                if not main_content_found:
                    temp_parts = []
                    for key, value in doc_content_dict.items():
                        if isinstance(value, str) and value.strip():
                            temp_parts.append(f"{key.capitalize()}: {value}")
                        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
                            temp_parts.append(f"{key.capitalize()}: {', '.join(value)}")
                    if temp_parts:
                        content_text_parts.append("\n".join(temp_parts))
            
            elif isinstance(doc_content_dict, str):
                content_text_parts.append(doc_content_dict)

            content_text = "\n".join(content_text_parts)
            
            if not content_text.strip() and isinstance(doc_content_dict, dict):
                try:
                    content_text = f"JSON Content: {json.dumps(doc_content_dict, indent=2, ensure_ascii=False)}"
                    logger.warning(f"No primary text found for doc {doc_id}, using JSON representation of content dict for snippet.")
                except TypeError:
                    content_text = "Complex non-serializable content structure."

            snippet = content_text.strip()[:350] + ('...' if len(content_text.strip()) > 350 else '')
            if not snippet.strip():
                 snippet = "[Content not extractable for snippet]"

            # Get original document path and ID from chunk's metadata
            original_doc_id_from_chunk = doc_metadata.get("original_doc_id", "N/A")
            original_doc_path_from_chunk = doc_metadata.get("original_document_path", "N/A") # This is what we added in chunking.py

            doc_identifier_info = f"Chunk ID: {doc_id}"
            if original_doc_id_from_chunk != "N/A" and original_doc_id_from_chunk != doc_id:
                doc_identifier_info += f" (Original Doc ID: {original_doc_id_from_chunk})"
            
            # Use the original_document_path for the File Path
            file_path_display = original_doc_path_from_chunk if original_doc_path_from_chunk != "N/A" else source

            response_parts.append(
                f"\nDocument {i+1}: {title}\n"
                f"Source Name: {source} (Type: {doc_type})\n" # Original source name
                f"File Path: {file_path_display}\n" # Path to the original document's JSON
                f"Relevance Score: {similarity:.4f}\n"
                f"{doc_identifier_info}\n"
                f"Content Snippet: {snippet}"
            )

        return "\n".join(response_parts)

    except Exception as e:
        logger.error(f"Error in search_knowledge_base tool: {str(e)}", exc_info=True)
        return f"Error executing knowledge base search: {str(e)}"

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
        
        entities = {}
        for entity_type, pattern in patterns.items():
            matches = re.findall(pattern, input_data)
            if matches:
                entities[entity_type] = list(set(matches))  # Remove duplicates
        
        if not entities:
            return "No security-related entities found in the text."
        
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
        try:
            data = json.loads(input_data)
            entities = data.get('entities', [])
        except Exception as e: 
            return f"Error: Input must be a valid JSON string containing an 'entities' list. Parsing failed: {str(e)}"

        if not entities or not isinstance(entities, list):
            return "Error: No valid 'entities' list found in the provided JSON input."
        
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
        try:
            data = json.loads(input_data)
            if 'events' not in data or not isinstance(data['events'], list):
                 raise ValueError("Input JSON must contain an 'events' key with a list value.")
            events = data['events']
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received in create_timeline: {input_data[:100]}... Error: {e}")
            return f"Error: Input must be a valid JSON string. Parsing failed: {str(e)}"
        except ValueError as e: 
            logger.error(f"Invalid data structure in create_timeline: {str(e)}")
            return f"Error: {str(e)}"
        except Exception as e: 
            logger.error(f"Unexpected error parsing input for create_timeline: {e}")
            return f"Error: Could not parse input JSON for timeline: {str(e)}"

        if not events:
            return "No events provided in the input JSON for timeline creation."

        valid_events = []
        invalid_event_found = False
        for i, event in enumerate(events):
            if isinstance(event, dict) and 'date' in event and 'description' in event:
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
             else: 
                 return "No processable events found."

        try:
            def get_sort_key(ev):
                try:
                    return datetime.fromisoformat(ev['date'].replace('Z', '+00:00'))
                except ValueError:
                    return ev['date']
            sorted_events = sorted(valid_events, key=get_sort_key)
        except Exception as e:
            logger.warning(f"Could not reliably sort events by date due to parsing issues ({e}), using basic string sort.")
            sorted_events = sorted(valid_events, key=lambda x: x['date'])

        response = "Timeline of Events:\n\n"
        for event in sorted_events:
            date_str = str(event.get('date', 'Unknown Date'))
            desc_str = str(event.get('description', 'No Description'))
            response += f"{date_str}: {desc_str}\n"

        if invalid_event_found:
             response += "\nNote: Some events in the input list were invalid or incomplete and were skipped."

        return response
    except Exception as e:
        logger.error(f"Error in create_timeline function: {str(e)}", exc_info=True)
        return f"Error creating timeline: {str(e)}"