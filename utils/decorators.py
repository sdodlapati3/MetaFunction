import time
import random
import logging
import functools
import requests


def retry_request(func):
    """Decorator to retry network requests with exponential backoff."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        base_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (requests.RequestException, ConnectionError) as e:
                if attempt == max_retries - 1:  # Last attempt
                    raise

                delay = base_delay * (2**attempt) + random.uniform(0, 0.5)
                logging.warning(f"Request failed: {e}. Retrying in {delay:.2f}s...")
                time.sleep(delay)

    return wrapper
