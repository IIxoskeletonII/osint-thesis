import requests
import xml.etree.ElementTree as ET
import json
import os
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ARXIV_API_URL = "http://export.arxiv.org/api/query"
CATEGORY = "cs.CR" # Computer Security and Cryptography
MAX_RESULTS = 50   # Number of recent papers to fetch for PoC
OUTPUT_DIR = os.path.join("data", "input", "arxiv")
REQUEST_DELAY = 3  # Seconds between requests (ArXiv guideline)

# Namespace for Atom feed
ATOM_NAMESPACE = {'atom': 'http://www.w3.org/2005/Atom'}

def fetch_arxiv_data():
    """Fetches recent papers from ArXiv API for cs.CR category."""
    logger.info(f"Fetching latest {MAX_RESULTS} papers from ArXiv category: {CATEGORY}")

    params = {
        'search_query': f'cat:{CATEGORY}',
        'sortBy': 'submittedDate',
        'sortOrder': 'descending',
        'max_results': MAX_RESULTS,
        'start': 0
    }

    try:
        # Adhere to ArXiv's request rate limits
        logger.info(f"Waiting {REQUEST_DELAY} seconds before ArXiv request...")
        time.sleep(REQUEST_DELAY)

        response = requests.get(ARXIV_API_URL, params=params, timeout=60)
        response.raise_for_status()
        logger.info("Successfully fetched data from ArXiv API.")
        return response.text # Return XML content as text

    except requests.exceptions.RequestException as e:
        logger.error(f"ArXiv API request failed: {e}")
        return None
    except Exception as e:
         logger.error(f"An unexpected error occurred during ArXiv fetch: {e}")
         return None

def parse_and_save_arxiv_entries(xml_data):
    """Parses ArXiv Atom XML and saves each entry as a JSON file."""
    if not xml_data:
        logger.warning("No XML data received from ArXiv, skipping parsing.")
        return 0

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    count = 0

    try:
        root = ET.fromstring(xml_data)
        entries = root.findall('atom:entry', ATOM_NAMESPACE)
        logger.info(f"Found {len(entries)} entries in ArXiv feed.")

        for entry in entries:
            try:
                arxiv_id_url = entry.find('atom:id', ATOM_NAMESPACE).text
                # Extract ID like '1234.56789' or 'cond-mat/0703101'
                arxiv_id = arxiv_id_url.split('/abs/')[-1]
                # Sanitize ID for filename
                safe_filename_id = arxiv_id.replace('/', '_').replace('.', '_')

                title = entry.find('atom:title', ATOM_NAMESPACE).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', ATOM_NAMESPACE).text.strip().replace('\n', ' ')
                published = entry.find('atom:published', ATOM_NAMESPACE).text
                authors = [author.find('atom:name', ATOM_NAMESPACE).text for author in entry.findall('atom:author', ATOM_NAMESPACE)]

                paper_data = {
                    'title': title,
                    'authors': authors,
                    'summary': summary, # Often referred to as abstract
                    'published': published,
                    'id': arxiv_id_url, # Link to abstract page
                    'arxiv_id_clean': arxiv_id
                }

                filename = f"arxiv_{safe_filename_id}.json"
                filepath = os.path.join(OUTPUT_DIR, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(paper_data, f, indent=2, ensure_ascii=False)
                count += 1

            except Exception as e:
                entry_id = entry.find('atom:id', ATOM_NAMESPACE).text if entry.find('atom:id', ATOM_NAMESPACE) is not None else 'unknown'
                logger.error(f"Failed to process ArXiv entry {entry_id}: {e}")

        logger.info(f"Successfully parsed and saved {count} ArXiv papers.")
        return count

    except ET.ParseError as e:
        logger.error(f"Failed to parse ArXiv XML response: {e}")
        return 0
    except Exception as e:
        logger.error(f"An unexpected error occurred during ArXiv parsing: {e}")
        return 0


if __name__ == "__main__":
    logger.info("--- Starting ArXiv Data Collection ---")
    xml_content = fetch_arxiv_data()
    papers_saved = parse_and_save_arxiv_entries(xml_content)
    logger.info(f"--- Finished ArXiv Data Collection ({papers_saved} papers saved) ---")