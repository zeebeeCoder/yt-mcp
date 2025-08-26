"""Custom exceptions for the YouTube analysis pipeline"""
from typing import Callable, Optional, Any


class PipelineError(Exception):
    """Base exception for pipeline errors"""
    pass


class ConfigurationError(PipelineError):
    """Raised when configuration is invalid or missing"""
    pass


class ExtractionError(PipelineError):
    """Raised when data extraction fails"""
    pass


class ProcessingError(PipelineError):
    """Raised when AI processing fails"""
    pass


class APIError(PipelineError):
    """Raised when external API calls fail"""

    def __init__(self, message: str, api_name: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.api_name = api_name
        self.status_code = status_code


class ValidationError(PipelineError):
    """Raised when data validation fails"""
    pass


def handle_api_error(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle common API errors"""
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Convert common API errors to our custom exceptions
            error_msg = str(e).lower()

            if "quota" in error_msg or "rate limit" in error_msg:
                raise APIError(f"API rate limit exceeded: {e}", "unknown") from e
            elif "authentication" in error_msg or "api key" in error_msg:
                raise APIError(f"Authentication failed: {e}", "unknown") from e
            elif "not found" in error_msg:
                raise ExtractionError(f"Resource not found: {e}") from e
            else:
                # Re-raise as generic processing error
                raise ProcessingError(f"Unexpected error in {func.__name__}: {e}") from e

    return wrapper
