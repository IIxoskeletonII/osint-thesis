"""Configuration module for the OSINT system."""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
ROOT_DIR = Path(__file__).parent.parent.absolute()

# Data directories
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# LLM Configuration
LLM_CONFIG = {
    "model": os.getenv("LLM_MODEL", "claude-3-7-sonnet-20250219"),
    "temperature": float(os.getenv("LLM_TEMPERATURE", 0.2)),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", 4096)),
    "api_key": os.getenv("ANTHROPIC_API_KEY"),
}

# Vector Database Configuration
VECTOR_DB_CONFIG = {
    "milvus": {
        "host": os.getenv("MILVUS_HOST", "localhost"),
        "port": int(os.getenv("MILVUS_PORT", 19530)),
        "collection": os.getenv("MILVUS_COLLECTION", "osint_intelligence"),
    },
    "postgres": {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "database": os.getenv("POSTGRES_DB", "osint_knowledge_base"),
    }
}

# RAG Configuration
RAG_CONFIG = {
    "chunk_size": int(os.getenv("CHUNK_SIZE", 800)),
    "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", 100)),
    "embedding_model": os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
}

# Setup logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "osint_system.log")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("osint_system")