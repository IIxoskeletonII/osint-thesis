"""Utilities for file handling in the OSINT system."""
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, BinaryIO
import mimetypes

def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    Get the file extension from a path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension (lowercase, without the dot)
    """
    return os.path.splitext(str(file_path))[1].lower().lstrip('.')


def get_mime_type(file_path: Union[str, Path]) -> str:
    """
    Get the MIME type of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type of the file
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        # Default to octet-stream if unknown
        mime_type = 'application/octet-stream'
    return mime_type


def save_json(data: Any, file_path: Union[str, Path], indent: int = 2) -> None:
    """
    Save data as a JSON file.
    
    Args:
        data: Data to save
        file_path: Path to save the file
        indent: Indentation level for JSON formatting
    """
    path = Path(file_path)
    
    # Ensure the directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_json(file_path: Union[str, Path]) -> Any:
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loaded data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def file_exists(file_path: Union[str, Path]) -> bool:
    """
    Check if a file exists.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file exists, False otherwise
    """
    return Path(file_path).is_file()


def list_files(directory: Union[str, Path], 
               pattern: str = "*", 
               recursive: bool = False) -> List[Path]:
    """
    List files in a directory matching a pattern.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern to match files
        recursive: Whether to search recursively
        
    Returns:
        List of matching file paths
    """
    directory = Path(directory)
    
    if not directory.is_dir():
        raise ValueError(f"Directory not found: {directory}")
    
    if recursive:
        return list(directory.glob(f"**/{pattern}"))
    else:
        return list(directory.glob(pattern))