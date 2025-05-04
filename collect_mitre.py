import requests
import json
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
MITRE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
OUTPUT_DIR = os.path.join("data", "input", "mitre")
FILENAME = "enterprise-attack.json"

def fetch_and_save_mitre_data():
    """Fetches the MITRE ATT&CK Enterprise JSON and saves it."""
    logger.info(f"Attempting to download MITRE ATT&CK data from {MITRE_URL}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, FILENAME)

    try:
        response = requests.get(MITRE_URL, timeout=60)
        response.raise_for_status() # Check for HTTP errors

        # Try to parse JSON to ensure it's valid before saving
        data = response.json()
        logger.info("Successfully downloaded and parsed MITRE ATT&CK data.")

        # Save the valid JSON data
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"MITRE ATT&CK data saved to {filepath}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download MITRE data: {e}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Downloaded MITRE data is not valid JSON: {e}")
        return False
    except IOError as e:
        logger.error(f"Failed to save MITRE data to {filepath}: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    logger.info("--- Starting MITRE ATT&CK Data Collection ---")
    success = fetch_and_save_mitre_data()
    if success:
        logger.info("--- Finished MITRE ATT&CK Data Collection Successfully ---")
    else:
        logger.error("--- MITRE ATT&CK Data Collection Failed ---")