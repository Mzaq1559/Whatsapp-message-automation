import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)


class WhatsAppAutomationError(Exception):
    """Base exception for WhatsApp automation errors."""

class ContactNotFoundError(WhatsAppAutomationError):
    """Raised when a contact or group cannot be found on WhatsApp Web."""

class SendFailedError(WhatsAppAutomationError):
    """Raised when a message send attempt fails."""

def calculate_delay(min_delay: float = 5.0, max_jitter: float = 3.0) -> float:
    """Returns min_delay + random float between 0 and max_jitter."""
    return min_delay + random.uniform(0.0, max_jitter)

def human_delay(min_delay: float = 5.0, max_jitter: float = 3.0) -> None:
    delay = calculate_delay(min_delay, max_jitter)
    time.sleep(delay)

F = TypeVar("F", bound=Callable[..., Any])

def retry_on_selenium_error(
    max_attempts: int = 3,
    backoff_factor: float = 1.5,
    min_delay: float = 2.0,
) -> Callable[[F], F]:
    """
    Decorator for retrying functions on transient Selenium exceptions.
    Does NOT retry ContactNotFoundError as it is a permanent outcome for a contact search.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            current_delay = min_delay
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except (
                    StaleElementReferenceException,
                    TimeoutException,
                    ElementNotInteractableException,
                    NoSuchElementException,
                ) as exc:
                    if attempt == max_attempts:
                        raise SendFailedError(
                            f"Failed after {max_attempts} attempts due to Selenium error: {exc!s}"
                        ) from exc
                    time.sleep(current_delay + random.uniform(0, 1.0))
                    current_delay *= backoff_factor
                    attempt += 1
                except ContactNotFoundError:
                    # Do not retry search failure
                    raise
            raise SendFailedError("Max retry attempts reached.")
        return wrapper  # type: ignore
    return decorator
