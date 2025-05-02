"""Utilities for API interactions in the OSINT system."""
import time
from typing import Any, Callable, Dict, Optional, TypeVar

# Type variable for generic function
T = TypeVar('T')

def handle_rate_limits(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    status_codes: Optional[list] = None
) -> Callable[..., T]:
    """
    Decorator to handle rate limits and retries for API calls.
    
    Args:
        func: The function to decorate
        max_retries: Maximum number of retries
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay with each retry
        status_codes: List of status codes to retry on (default: [429, 500, 502, 503, 504])
        
    Returns:
        Decorated function
    """
    if status_codes is None:
        status_codes = [429, 500, 502, 503, 504]
    
    def wrapper(*args: Any, **kwargs: Any) -> T:
        retries = 0
        delay = initial_delay
        
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check if exception has a status_code attribute (like requests.exceptions.HTTPError)
                status_code = getattr(e, 'status_code', None)
                if hasattr(e, 'response'):
                    status_code = getattr(e.response, 'status_code', None)
                
                # If we've exhausted retries or this isn't a retryable error, raise
                if retries >= max_retries or (status_code and status_code not in status_codes):
                    raise
                
                # Exponential backoff
                time.sleep(delay)
                delay *= backoff_factor
                retries += 1
    
    return wrapper


def validate_api_key(api_key: str, key_name: str = "API key") -> None:
    """
    Validate that an API key is present and in expected format.
    
    Args:
        api_key: The API key to validate
        key_name: Name of the key for error messages
        
    Raises:
        ValueError: If the API key is invalid
    """
    if not api_key:
        raise ValueError(f"{key_name} is missing. Please set it in the .env file.")
    
    # Basic validation - can be extended for specific API key formats
    if len(api_key) < 8:
        raise ValueError(f"{key_name} appears to be invalid (too short).")