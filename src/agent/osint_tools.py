import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def search_knowledge_base(knowledge_base, input_data: str) -> Dict[str, Any]:
    """
    Search the knowledge base for relevant documents.

    Args:
        knowledge_base: KnowledgeBase instance (likely KnowledgeBaseManager)
        input_data: Search query string (potentially JSON containing query and limit)

    Returns:
        A dictionary containing:
            "observation_text": Formatted string with search results for the LLM Observation step.
            "structured_results": A list of dictionaries, each representing a found document
                                  with its details (title, source, path, score, etc.).
    """
    query = input_data
    limit = 5
    observation_text = "No relevant documents found in the knowledge base for this query." # Default
    structured_results_for_agent = []

    try:
        if input_data.strip().startswith('{') and input_data.strip().endswith('}'):
            try:
                params = json.loads(input_data)
                query = params.get('query', query)
                limit = params.get('limit', limit)
                logger.debug(f"Parsed JSON input: query='{query}', limit={limit}")
            except json.JSONDecodeError:
                logger.warning("Input looked like JSON but failed to parse. Treating entire string as query.")
                # query is already input_data
                limit = 5

        if not query:
            observation_text = "Error: No query provided for knowledge base search."
            return {
                "observation_text": observation_text,
                "structured_results": []
            }

        kb_results = knowledge_base.search(query, limit=limit)

        if kb_results:
            response_parts_temp = [f"Found {len(kb_results)} relevant document(s):"]
            
            for i, result_item in enumerate(kb_results):
                chunk_id_for_log = f"Result_{i+1}_unparsed"
                try:
                    chunk_id = result_item.get("id", f"Result_{i+1}")
                    chunk_id_for_log = chunk_id # Update for more specific logging if ID is found
                    similarity = result_item.get("similarity", 0.0)
                    
                    doc_data = result_item.get('document', {})
                    chunk_content_fields = doc_data.get('content', {})
                    chunk_metadata = doc_data.get('metadata', {})

                    source_name = chunk_metadata.get('source_name', 'Unknown Source')
                    source_type = chunk_metadata.get('source_type', 'Unknown Type')
                    chunk_title = chunk_content_fields.get('title', f'Document {chunk_id}')
                    
                    original_doc_id = chunk_metadata.get("original_doc_id", "N/A")
                    original_document_path = chunk_metadata.get("original_document_path", "N/A")
                    
                    doc_identifier_info = f"Chunk ID: {chunk_id}"
                    if original_doc_id != "N/A" and original_doc_id != chunk_id:
                        doc_identifier_info += f" (Original Doc ID: {original_doc_id})"
                    
                    file_path_display = original_document_path if original_document_path != "N/A" else source_name
                    
                    current_doc_obs_parts = [ # Initialize for each document
                        f"\nDocument {i+1}: {chunk_title}",
                        f"Source Name: {source_name} (Type: {source_type})",
                        f"File Path: {file_path_display}",
                        f"Relevance Score: {similarity:.4f}",
                        doc_identifier_info
                    ]

                    content_text_parts_local = []
                    if isinstance(chunk_content_fields, dict):
                        preferred_fields = ['description', 'summary', 'abstract', 'text', 'content_text']
                        main_content_found = False
                        for field in preferred_fields:
                            if field in chunk_content_fields and isinstance(chunk_content_fields[field], str) and chunk_content_fields[field].strip():
                                content_text_parts_local.append(chunk_content_fields[field])
                                main_content_found = True
                                break
                        if not main_content_found:
                            temp_parts = []
                            for key, value in chunk_content_fields.items():
                                if key == "title": continue
                                if isinstance(value, str) and value.strip(): temp_parts.append(f"{key.capitalize()}: {value}")
                                elif isinstance(value, list) and all(isinstance(item, str) for item in value): temp_parts.append(f"{key.capitalize()}: {', '.join(value)}")
                            if temp_parts: content_text_parts_local.append("\n".join(temp_parts))
                    elif isinstance(chunk_content_fields, str):
                        content_text_parts_local.append(chunk_content_fields)
                    
                    content_text_for_snippet = "\n".join(content_text_parts_local)
                    if not content_text_for_snippet.strip() and isinstance(chunk_content_fields, dict):
                        try: content_text_for_snippet = f"JSON Content: {json.dumps(chunk_content_fields, indent=2, ensure_ascii=False)}"
                        except TypeError: content_text_for_snippet = "Complex non-serializable content structure."

                    snippet = content_text_for_snippet.strip()[:350] + ('...' if len(content_text_for_snippet.strip()) > 350 else '')
                    if not snippet.strip(): snippet = "[Content not extractable for snippet]"
                    current_doc_obs_parts.append(f"Content Snippet: {snippet}")

                    doc_detail_for_agent = {
                        "id": chunk_id,
                        "title": chunk_title,
                        "original_doc_title": chunk_content_fields.get('title', 'N/A').split(" (Part")[0],
                        "source_name": source_name,
                        "source_type": source_type,
                        "file_path": original_document_path,
                        "original_doc_id": original_doc_id,
                        "similarity": similarity,
                        "content_snippet_for_agent_reference": snippet
                    }
                    structured_results_for_agent.append(doc_detail_for_agent)
                    response_parts_temp.append("\n".join(current_doc_obs_parts))

                except Exception as e_inner:
                    logger.error(f"Error processing individual search result item (logged as {chunk_id_for_log}): {e_inner}", exc_info=True)
                    response_parts_temp.append(f"\nDocument {i+1} (ID: {chunk_id_for_log}): Error processing this item - {e_inner}")
            
            observation_text = "\n".join(response_parts_temp)

    except Exception as e_outer:
        logger.error(f"Outer error in search_knowledge_base tool: {str(e_outer)}", exc_info=True)
        observation_text = f"Error executing knowledge base search: {str(e_outer)}"
        structured_results_for_agent = [] 
    
    return {
        "observation_text": observation_text.strip(),
        "structured_results": structured_results_for_agent
    }

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
                    # Attempt ISO format parsing first, handling potential 'Z' for UTC
                    date_str = ev['date']
                    if date_str.endswith('Z'): # Replace Z with +00:00 for fromisoformat
                        date_str = date_str[:-1] + '+00:00'
                    return datetime.fromisoformat(date_str)
                except ValueError:
                    # Fallback to simple string sorting if detailed parsing fails
                    logger.warning(f"Could not parse date string '{ev['date']}' for sorting, using string comparison.")
                    return ev['date'] 
            sorted_events = sorted(valid_events, key=get_sort_key)
        except Exception as e: # Catch any error during sorting
            logger.warning(f"Could not reliably sort events by date due to parsing/comparison issues ({e}), using basic string sort.")
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