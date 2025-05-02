"""Utilities for data processing in the OSINT system."""
import re
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        filename: The string to sanitize
        
    Returns:
        A sanitized string safe for use as a filename
    """
    # Replace invalid filename characters
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # Trim whitespace and limit length
    sanitized = sanitized.strip().replace(" ", "_")
    # Ensure the filename isn't too long (max 255 chars)
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    return sanitized


def generate_file_hash(content: Union[str, bytes], hash_type: str = 'sha256') -> str:
    """
    Generate a hash for file content.
    
    Args:
        content: The content to hash
        hash_type: The type of hash to use (md5, sha1, sha256)
        
    Returns:
        Hexadecimal string representation of the hash
    """
    if hash_type not in ['md5', 'sha1', 'sha256']:
        raise ValueError(f"Unsupported hash type: {hash_type}")
    
    if isinstance(content, str):
        content = content.encode('utf-8')
    
    if hash_type == 'md5':
        return hashlib.md5(content).hexdigest()
    elif hash_type == 'sha1':
        return hashlib.sha1(content).hexdigest()
    else:  # sha256
        return hashlib.sha256(content).hexdigest()


def ensure_directory(directory_path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        Path object of the directory
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_timestamp(timestamp: Optional[datetime] = None, format_str: str = "%Y-%m-%d_%H-%M-%S") -> str:
    """
    Format a timestamp for filenames or display.
    
    Args:
        timestamp: Datetime object (default: current time)
        format_str: Format string for the timestamp
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now()
    return timestamp.strftime(format_str)