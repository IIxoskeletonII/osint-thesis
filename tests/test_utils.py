"""Tests for utility functions in the OSINT system."""
import os
import json
import sys
import logging

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tempfile
from datetime import datetime
from pathlib import Path
import unittest

# Import utility modules
from src.utils.logging_utils import setup_logger
from src.utils.data_utils import (
    sanitize_filename, 
    generate_file_hash, 
    ensure_directory, 
    format_timestamp
)
from src.utils.file_utils import (
    get_file_extension,
    get_mime_type,
    save_json,
    load_json,
    file_exists,
    list_files
)


class TestLoggingUtils(unittest.TestCase):
    """Test logging utility functions."""
    
    def test_setup_logger(self):
        """Test setup_logger function."""
        # Create a temporary log file
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as temp_file:
            log_path = temp_file.name
        
        try:
            # Set up logger with file and console handlers
            logger = setup_logger("test_logger", log_path, logging.DEBUG)
            
            # Check logger properties
            self.assertEqual(logger.name, "test_logger")
            self.assertEqual(logger.level, logging.DEBUG)
            
            # Check that handlers are created
            self.assertEqual(len(logger.handlers), 2)
            
            # Log a test message
            test_message = "Test log message"
            logger.info(test_message)
            
            # Check that message was written to file
            with open(log_path, 'r') as f:
                log_content = f.read()
                self.assertIn(test_message, log_content)
        
        finally:
            # Allow some time for file to be released
            import time
            time.sleep(0.1)
            
            # Clean up
            try:
                if os.path.exists(log_path):
                    os.remove(log_path)
            except PermissionError:
                # If we still can't delete it, just report but don't fail the test
                print(f"NOTE: Could not delete temporary log file: {log_path}")


class TestDataUtils(unittest.TestCase):
    """Test data utility functions."""
    
    def test_sanitize_filename(self):
        """Test sanitize_filename function."""
        # Test with invalid characters
        self.assertEqual(sanitize_filename("file/with\\invalid:chars"), "file_with_invalid_chars")
        
        # Test with spaces
        self.assertEqual(sanitize_filename("file with spaces"), "file_with_spaces")
        
        # Test with long filename
        long_name = "a" * 300
        self.assertEqual(len(sanitize_filename(long_name)), 255)
    
    def test_generate_file_hash(self):
        """Test generate_file_hash function."""
        # Test with string content
        content = "test content"
        sha256_hash = generate_file_hash(content)
        self.assertEqual(len(sha256_hash), 64)  # SHA-256 hash is 64 characters
        
        # Test with binary content
        binary_content = b"binary test content"
        sha256_hash = generate_file_hash(binary_content)
        self.assertEqual(len(sha256_hash), 64)
        
        # Test with different hash types
        md5_hash = generate_file_hash(content, hash_type='md5')
        self.assertEqual(len(md5_hash), 32)  # MD5 hash is 32 characters
        
        # Test with invalid hash type
        with self.assertRaises(ValueError):
            generate_file_hash(content, hash_type='invalid')
    
    def test_ensure_directory(self):
        """Test ensure_directory function."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test creating a new directory
            new_dir = Path(temp_dir) / "test_dir"
            result = ensure_directory(new_dir)
            
            # Check that directory was created
            self.assertTrue(new_dir.is_dir())
            self.assertEqual(result, new_dir)
            
            # Test with existing directory
            result = ensure_directory(new_dir)
            self.assertEqual(result, new_dir)
    
    def test_format_timestamp(self):
        """Test format_timestamp function."""
        # Test with custom timestamp and format
        dt = datetime(2025, 1, 1, 12, 30, 45)
        self.assertEqual(format_timestamp(dt, "%Y-%m-%d"), "2025-01-01")
        self.assertEqual(format_timestamp(dt, "%H:%M:%S"), "12:30:45")
        
        # Test with default format
        self.assertEqual(format_timestamp(dt), "2025-01-01_12-30-45")
        
        # Test without providing timestamp (current time)
        current_ts = format_timestamp()
        self.assertTrue(len(current_ts) > 0)


class TestFileUtils(unittest.TestCase):
    """Test file utility functions."""
    
    def test_get_file_extension(self):
        """Test get_file_extension function."""
        self.assertEqual(get_file_extension("file.txt"), "txt")
        self.assertEqual(get_file_extension("file.PDF"), "pdf")
        self.assertEqual(get_file_extension("/path/to/file.json"), "json")
        self.assertEqual(get_file_extension("file_without_extension"), "")
    
    def test_get_mime_type(self):
        """Test get_mime_type function."""
        self.assertEqual(get_mime_type("file.txt"), "text/plain")
        self.assertEqual(get_mime_type("file.json"), "application/json")
        self.assertEqual(get_mime_type("file.pdf"), "application/pdf")
        self.assertEqual(get_mime_type("file.unknown"), "application/octet-stream")
    
    def test_save_and_load_json(self):
        """Test save_json and load_json functions."""
        # Create test data
        test_data = {"key": "value", "list": [1, 2, 3], "nested": {"a": 1}}
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            json_path = temp_file.name
        
        try:
            # Save JSON
            save_json(test_data, json_path)
            
            # Check that file exists
            self.assertTrue(os.path.exists(json_path))
            
            # Load JSON
            loaded_data = load_json(json_path)
            
            # Check that data matches
            self.assertEqual(loaded_data, test_data)
            
            # Test with nonexistent file
            with self.assertRaises(FileNotFoundError):
                load_json("nonexistent.json")
        
        finally:
            # Clean up
            if os.path.exists(json_path):
                os.remove(json_path)
    
    def test_file_exists(self):
        """Test file_exists function."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file_path = temp_file.name
        
        try:
            # Check that file exists
            self.assertTrue(file_exists(file_path))
            
            # Check nonexistent file
            self.assertFalse(file_exists("nonexistent.file"))
        
        finally:
            # Clean up
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def test_list_files(self):
        """Test list_files function."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files
            file1 = Path(temp_dir) / "file1.txt"
            file2 = Path(temp_dir) / "file2.json"
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            file3 = subdir / "file3.txt"
            
            # Write to files
            file1.write_text("content1")
            file2.write_text("content2")
            file3.write_text("content3")
            
            # Test without recursion
            files = list_files(temp_dir, pattern="*.txt")
            self.assertEqual(len(files), 1)
            self.assertIn(file1, files)
            
            # Test with recursion
            files = list_files(temp_dir, pattern="*.txt", recursive=True)
            self.assertEqual(len(files), 2)
            self.assertIn(file1, files)
            self.assertIn(file3, files)
            
            # Test with non-matching pattern
            files = list_files(temp_dir, pattern="*.csv")
            self.assertEqual(len(files), 0)
            
            # Test with invalid directory
            with self.assertRaises(ValueError):
                list_files("nonexistent_dir")


if __name__ == "__main__":
    unittest.main()