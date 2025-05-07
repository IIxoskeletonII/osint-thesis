import requests
import json
import os
import logging
import time
from datetime import datetime, timedelta, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
OUTPUT_DIR = os.path.join("data", "input", "nvd")
DAYS_TO_FETCH = 30 # Fetch data for the last 30 days (adjust as needed for PoC)
RESULTS_PER_PAGE = 2000 # Max allowed by API
REQUEST_DELAY = 6 # Seconds between requests (NVD requests 6 seconds without API key)

def fetch_nvd_data(start_date, end_date):
    """Fetches CVE data from NVD API for a given date range."""
    logger.info(f"Fetching NVD data from {start_date} to {end_date}")
    all_vulnerabilities = []
    start_index = 0

    # Format dates for API query (ISO 8601 format, URL encoded)
    # NVD API expects UTC timezone explicitly
    start_date_str = start_date.isoformat(timespec='seconds').replace('+00:00', 'Z')
    end_date_str = end_date.isoformat(timespec='seconds').replace('+00:00', 'Z')
    

    while True:
        params = {
            'pubStartDate': start_date_str,
            'pubEndDate': end_date_str,
            'resultsPerPage': RESULTS_PER_PAGE,
            'startIndex': start_index
        }
        logger.info(f"Requesting NVD API with startIndex: {start_index}")

        try:
            response = requests.get(NVD_API_URL, params=params, timeout=60) # Increased timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            vulnerabilities = data.get('vulnerabilities', [])
            all_vulnerabilities.extend(vulnerabilities)
            logger.info(f"Fetched {len(vulnerabilities)} vulnerabilities.")

            total_results = data.get('totalResults', 0)
            start_index += len(vulnerabilities)

            if start_index >= total_results or not vulnerabilities:
                logger.info("Finished fetching all pages.")
                break

            # Respect NVD rate limits
            logger.info(f"Waiting {REQUEST_DELAY} seconds before next request...")
            time.sleep(REQUEST_DELAY)

        except requests.exceptions.RequestException as e:
            logger.error(f"NVD API request failed: {e}")
            break # Exit loop on error
        except json.JSONDecodeError as e:
             logger.error(f"Failed to decode NVD API response: {e}")
             logger.debug(f"Response text: {response.text[:500]}...") # Log beginning of bad response
             break
        except Exception as e:
             logger.error(f"An unexpected error occurred during NVD fetch: {e}")
             break


    logger.info(f"Total vulnerabilities fetched: {len(all_vulnerabilities)}")
    return all_vulnerabilities

def save_nvd_data(vulnerabilities):
    """Saves the fetched vulnerabilities to a JSON file."""
    if not vulnerabilities:
        logger.warning("No vulnerabilities fetched, nothing to save.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nvd_cves_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # Structure the output to be easily processable later
    output_data = {
        "format": "NVD_CVE",
        "version": "2.0",
        "retrieved_at": datetime.now().isoformat(),
        "vulnerabilities": vulnerabilities # Save the list directly
    }

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved {len(vulnerabilities)} vulnerabilities to {filepath}")
    except IOError as e:
        logger.error(f"Failed to save NVD data to {filepath}: {e}")

if __name__ == "__main__":
    logger.info("--- Starting NVD Data Collection ---")
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=DAYS_TO_FETCH)
    
    fetched_data = fetch_nvd_data(start_time, end_time)
    save_nvd_data(fetched_data)
    logger.info("--- Finished NVD Data Collection ---")