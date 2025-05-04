import os
import json
import logging
import sys
from typing import Dict, Any, List
from pathlib import Path

# Add src directory to path to allow imports like src.knowledge_base...
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '.')) # Assumes script is in root
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from src.knowledge_base.knowledge_base_manager import KnowledgeBaseManager
except ImportError as e:
    print(f"Error importing KnowledgeBaseManager: {e}")
    print(f"Project Root: {project_root}")
    print(f"SRC Path: {src_path}")
    print(f"Sys Path: {sys.path}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_text_file(file_path: str) -> str:
    """Load a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        logger.warning(f"UTF-8 decoding failed for {file_path}. Trying latin-1.")
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Could not read file {file_path}: {e}")
        raise # Re-raise after logging

def create_document_content_from_file(file_path: str) -> Dict[str, Any]:
    """
    Create the 'content' part of a document object from a file.
    Handles NVD and MITRE JSON structures more specifically.

    Args:
        file_path: Path to the file

    Returns:
        Document content dictionary or None if failed/unsupported.
    """
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    title = os.path.splitext(file_name)[0].replace('_', ' ').replace('-', ' ').title()

    description_text = ""
    other_fields = {}

    if file_ext == '.json':
        try:
            data = load_json_file(file_path)
            is_nvd = 'vulnerabilities' in data and 'format' in data and 'NVD_CVE' in data['format']
            is_mitre = 'type' in data and data['type'] == 'bundle' and 'objects' in data

            if is_nvd:
                logger.info(f"Processing as NVD file: {file_name}")
                title = f"NVD Vulnerability Feed ({data.get('timestamp', 'unknown date')})"
                # Combine descriptions of all CVEs into one text block
                descriptions = []
                for vuln in data.get('vulnerabilities', []):
                    cve_item = vuln.get('cve', {})
                    cve_id = cve_item.get('id', 'Unknown CVE')
                    # Get english description
                    desc = ""
                    for desc_data in cve_item.get('descriptions', []):
                        if desc_data.get('lang') == 'en':
                            desc = desc_data.get('value', '')
                            break
                    if desc:
                         descriptions.append(f"--- {cve_id} ---\n{desc}\n")
                description_text = "\n".join(descriptions)
                if not description_text:
                     description_text = "No vulnerability descriptions found in the NVD file."
                other_fields['retrieved_at'] = data.get('retrieved_at')
                other_fields['vulnerability_count'] = len(data.get('vulnerabilities', []))


            elif is_mitre:
                logger.info(f"Processing as MITRE ATT&CK file: {file_name}")
                title = f"MITRE ATT&CK Enterprise ({data.get('spec_version', 'unknown version')})"
                # Combine descriptions of techniques/tactics etc.
                descriptions = []
                obj_types = {}
                for obj in data.get('objects', []):
                     obj_type = obj.get('type')
                     if obj_type:
                         obj_types[obj_type] = obj_types.get(obj_type, 0) + 1
                     name = obj.get('name', obj.get('id', 'Unknown Object'))
                     desc = obj.get('description', '')
                     if desc:
                         descriptions.append(f"--- {name} ({obj_type}) ---\n{desc}\n")
                description_text = "\n".join(descriptions)
                if not description_text:
                     description_text = "No descriptions found for MITRE objects."
                other_fields['object_counts'] = obj_types


            else: # Generic JSON or ArXiv JSON
                 logger.info(f"Processing as generic/ArXiv JSON: {file_name}")
                 title = data.get('title', title)
                 description_text = data.get('summary', data.get('description', ''))
                 if not description_text: # Fallback if still no description
                    description_text = f"JSON data for {title}. Keys: {list(data.keys())}"

                 other_fields['authors'] = data.get('authors')
                 other_fields['published_date'] = data.get('published')
                 other_fields['arxiv_id_clean'] = data.get('arxiv_id_clean')


        except Exception as e:
            logger.error(f"Error processing JSON file {file_path}: {e}", exc_info=True)
            return None

    elif file_ext in ['.txt', '.md']:
         try:
             description_text = load_text_file(file_path)
             if file_ext == '.md' and description_text.startswith('# '):
                 first_line = description_text.split('\n', 1)[0]
                 title = first_line.lstrip('# ').strip()
         except Exception as e:
              logger.error(f"Error loading text/markdown file {file_path}: {e}")
              return None


    else:
        logger.warning(f"Unsupported file type: {file_ext} for file {file_path}")
        return None

    # Construct the content dictionary
    doc_content_part = {
        "title": title,
        "description": description_text,
        **{k: v for k, v in other_fields.items() if v}
    }

    return doc_content_part


def ingest_documents_from_directory(kb_manager: KnowledgeBaseManager,
                                   directory: str,
                                   source_type: str, # This is the PRIMARY category (vulnerability, threat, research)
                                   recursive: bool = True) -> int:
    """Ingests documents, passing only content dict to kb_manager."""
    count = 0
    abs_directory = os.path.abspath(directory)

    if not os.path.exists(abs_directory):
        logger.warning(f"Input directory does not exist: {abs_directory}")
        return count

    logger.info(f"Scanning directory {abs_directory} for source type '{source_type}'")

    try:
        items = os.listdir(abs_directory)
    except Exception as e:
        logger.error(f"Could not list directory {abs_directory}: {e}")
        return count

    for item in items:
        item_path = os.path.join(abs_directory, item)

        if os.path.isdir(item_path) and recursive:
            # Recursively process subdirectories, maintaining the primary source_type
            logger.debug(f"Entering subdirectory: {item_path}")
            count += ingest_documents_from_directory(
                kb_manager, item_path, source_type, recursive)
            continue

        if not os.path.isfile(item_path):
            continue

        if item.startswith('.'):
            logger.debug(f"Skipping hidden file: {item_path}")
            continue

        logger.debug(f"Processing file: {item_path}")
        document_content = create_document_content_from_file(item_path)

        if document_content:
            try:
                # Use filename as source_name
                source_name = os.path.basename(item_path)
                doc_id, chunk_ids = kb_manager.add_document(
                    document=document_content, # Pass only the content part
                    source_type=source_type,
                    source_name=source_name
                )
                logger.info(f"Successfully added document ID {doc_id} ({len(chunk_ids)} chunks) from {item_path}")
                count += 1
            except Exception as e:
                logger.error(f"Error adding document from {item_path} to KB: {e}", exc_info=False) # Set exc_info=True for full traceback
        else:
             logger.warning(f"Could not create document content for file: {item_path}")


    logger.info(f"Finished directory {abs_directory}. Added {count} documents.")
    return count

def main():
    """Main function to ingest documents into the knowledge base."""
    logger.info("Starting document ingestion process...")

    # --- Configuration ---
    # Set the base directory where the 'knowledge_base' output folder resides or will be created.
    KB_OUTPUT_BASE_DIR = "data"
    # Define where to find the RAW input files, mapped to their intelligence category.
    SOURCE_MAP = {
        "data/input/nvd": "vulnerability",
        "data/input/mitre": "threat",
        "data/input/arxiv": "research",
       # "docs": "project_documentation" # Uncomment to ingest .md files from root 'docs' folder
    }
    # --- End Configuration ---

    abs_kb_output_dir = os.path.abspath(KB_OUTPUT_BASE_DIR)
    logger.info(f"Target Knowledge Base Directory: {os.path.join(abs_kb_output_dir, 'knowledge_base')}")

    try:
        # Initialize knowledge base manager
        kb_manager = KnowledgeBaseManager(base_dir=KB_OUTPUT_BASE_DIR)
    except Exception as e:
         logger.error(f"Failed to initialize KnowledgeBaseManager: {e}", exc_info=True)
         sys.exit(1)

    # Log initial stats
    try:
        initial_stats = kb_manager.get_stats()
        logger.info(f"Initial KB stats: {initial_stats['document_count']} documents, {initial_stats['chunk_count']} chunks.")
    except Exception as e:
         logger.error(f"Failed to get initial KB stats: {e}")
         # Continue ingestion anyway

    total_added_count = 0

    # Process each defined input directory
    for directory, source_type in SOURCE_MAP.items():
        count = ingest_documents_from_directory(kb_manager, directory, source_type)
        total_added_count += count

    logger.info(f"=== Ingestion Run Summary ===")
    logger.info(f"Total new documents added in this run: {total_added_count}")

    # Print final knowledge base stats
    try:
        final_stats = kb_manager.get_stats()
        print("\nKnowledge Base Statistics (After Ingestion Run):")
        print(f"Total Document count: {final_stats['document_count']}")
        print(f"Total Chunk count: {final_stats['chunk_count']}")
        print(f"Average chunks per document: {final_stats.get('avg_chunks_per_document', 0):.2f}") # Use .get for safety

        print("\nDocument distribution by source type:")
        source_dist = final_stats.get('by_source_type', {})
        if source_dist:
            for st, ct in source_dist.items():
                print(f"  {st}: {ct} documents")
        else:
            print("  No documents found or stats unavailable.")
    except Exception as e:
        logger.error(f"Failed to get final KB stats: {e}")


if __name__ == "__main__":
    main()