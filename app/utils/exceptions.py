"""
Custom exceptions for the MetaFunction application.
"""


class MetaFunctionError(Exception):
    """Base exception for MetaFunction application."""
    pass


class ModelNotFoundError(MetaFunctionError):
    """Raised when a requested AI model is not available."""
    pass


class APIError(MetaFunctionError):
    """Raised when an external API call fails."""
    pass


class ConfigurationError(MetaFunctionError):
    """Raised when configuration is invalid or missing."""
    pass


class PaperResolutionError(MetaFunctionError):
    """Raised when paper content cannot be resolved."""
    pass


class ValidationError(MetaFunctionError):
    """Raised when input validation fails."""
    pass
