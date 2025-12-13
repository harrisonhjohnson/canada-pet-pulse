"""
Base scraper utilities and shared functionality.
Provides error handling, retry logic, and common scraper patterns.
"""

import logging
import time
from typing import Optional, Any, Callable
from functools import wraps

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 3, delay: float = 5.0):
    """
    Decorator to retry failed operations with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay in seconds (doubles with each retry)

    Example:
        @retry_on_failure(max_retries=3, delay=5.0)
        def fetch_data():
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries} failed: {e}"
                    )

                    # Don't sleep after the last failed attempt
                    if attempt < max_retries - 1:
                        sleep_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.info(f"Retrying in {sleep_time} seconds...")
                        time.sleep(sleep_time)

            # All retries exhausted
            logger.error(f"{func.__name__} failed after {max_retries} attempts")
            raise last_exception

        return wrapper
    return decorator


class BaseScraper:
    """
    Base class with common scraper utilities.
    """

    @staticmethod
    def safe_get(data: dict, *keys, default: Any = None) -> Any:
        """
        Safely navigate nested dictionary without KeyError.

        Args:
            data: Dictionary to navigate
            *keys: Sequence of keys to traverse
            default: Default value if key not found

        Returns:
            Value at the nested key path, or default if not found

        Example:
            >>> data = {'user': {'profile': {'name': 'John'}}}
            >>> BaseScraper.safe_get(data, 'user', 'profile', 'name')
            'John'
            >>> BaseScraper.safe_get(data, 'user', 'settings', 'theme', default='dark')
            'dark'
        """
        current = data

        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default

        return current if current is not None else default

    @staticmethod
    def validate_response(response: list, min_items: int = 0,
                         name: str = "response") -> bool:
        """
        Validate scraper response meets minimum quality thresholds.

        Args:
            response: List of scraped items
            min_items: Minimum number of items required
            name: Name of the response for logging

        Returns:
            True if response is valid, False otherwise
        """
        if not response:
            logger.warning(f"Empty {name} received")
            return False

        if len(response) < min_items:
            logger.warning(
                f"Insufficient items in {name}: {len(response)} < {min_items}"
            )
            return False

        logger.info(f"Valid {name}: {len(response)} items")
        return True

    @staticmethod
    def truncate_text(text: str, max_length: int = 500,
                     suffix: str = "...") -> str:
        """
        Truncate text to maximum length with suffix.

        Args:
            text: Text to truncate
            max_length: Maximum length including suffix
            suffix: String to append if truncated

        Returns:
            Truncated text
        """
        if not text:
            return ""

        if len(text) <= max_length:
            return text

        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def clean_whitespace(text: str) -> str:
        """
        Clean and normalize whitespace in text.

        Args:
            text: Text to clean

        Returns:
            Text with normalized whitespace
        """
        if not text:
            return ""

        # Replace multiple whitespace with single space
        import re
        text = re.sub(r'\s+', ' ', text)

        # Strip leading/trailing whitespace
        return text.strip()
