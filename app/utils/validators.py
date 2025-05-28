"""
Input validation utilities for MetaFunction.

This module provides functions for validating request data and ensuring
data integrity across the application.
"""

from typing import Dict, Any, Set, Optional
from app.utils.exceptions import ValidationError


def validate_request_data(data: Dict[str, Any], required_fields: Set[str], 
                         optional_fields: Optional[Set[str]] = None) -> None:
    """
    Validate request data against required and optional fields.
    
    Args:
        data: Dictionary containing request data
        required_fields: Set of required field names
        optional_fields: Set of optional field names (if provided, extra fields are rejected)
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValidationError("Request data must be a dictionary")
    
    # Check for missing required fields
    missing_fields = required_fields - set(data.keys())
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(sorted(missing_fields))}")
    
    # Check for empty required fields
    empty_fields = []
    for field in required_fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            empty_fields.append(field)
    
    if empty_fields:
        raise ValidationError(f"Required fields cannot be empty: {', '.join(sorted(empty_fields))}")
    
    # If optional_fields is provided, check for unexpected fields
    if optional_fields is not None:
        allowed_fields = required_fields | optional_fields
        unexpected_fields = set(data.keys()) - allowed_fields
        if unexpected_fields:
            raise ValidationError(f"Unexpected fields: {', '.join(sorted(unexpected_fields))}")


def validate_model_name(model: str) -> None:
    """
    Validate AI model name.
    
    Args:
        model: Model name to validate
        
    Raises:
        ValidationError: If model name is invalid
    """
    if not isinstance(model, str) or not model.strip():
        raise ValidationError("Model name must be a non-empty string")
    
    # List of supported models - update as needed
    supported_models = {
        'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo',
        'deepseek-chat', 'deepseek-coder',
        'llama-3.1-sonar-small-128k-online', 'llama-3.1-sonar-large-128k-online',
        'llama-3.1-sonar-huge-128k-online'
    }
    
    if model not in supported_models:
        raise ValidationError(f"Unsupported model: {model}. Supported models: {', '.join(sorted(supported_models))}")


def validate_query(query: str, max_length: int = 10000) -> None:
    """
    Validate user query.
    
    Args:
        query: User query to validate
        max_length: Maximum allowed query length
        
    Raises:
        ValidationError: If query is invalid
    """
    if not isinstance(query, str):
        raise ValidationError("Query must be a string")
    
    if not query.strip():
        raise ValidationError("Query cannot be empty")
    
    if len(query) > max_length:
        raise ValidationError(f"Query too long. Maximum length: {max_length} characters")


def validate_paper_identifier(identifier: str, identifier_type: str) -> None:
    """
    Validate paper identifier (DOI, PMID, etc.).
    
    Args:
        identifier: Paper identifier to validate
        identifier_type: Type of identifier ('doi', 'pmid', 'arxiv', etc.)
        
    Raises:
        ValidationError: If identifier is invalid
    """
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValidationError(f"{identifier_type.upper()} must be a non-empty string")
    
    identifier = identifier.strip()
    
    if identifier_type.lower() == 'doi':
        # Basic DOI format validation
        if not identifier.startswith('10.'):
            raise ValidationError("DOI must start with '10.'")
        if '/' not in identifier:
            raise ValidationError("DOI must contain a '/' character")
    
    elif identifier_type.lower() == 'pmid':
        # PMID should be numeric
        if not identifier.isdigit():
            raise ValidationError("PMID must be numeric")
    
    elif identifier_type.lower() == 'arxiv':
        # Basic arXiv ID validation (simplified)
        if not any(char.isdigit() for char in identifier):
            raise ValidationError("arXiv ID must contain numbers")


def validate_session_id(session_id: str) -> None:
    """
    Validate session ID.
    
    Args:
        session_id: Session ID to validate
        
    Raises:
        ValidationError: If session ID is invalid
    """
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValidationError("Session ID must be a non-empty string")
    
    # Check length limits
    if len(session_id) < 8 or len(session_id) > 128:
        raise ValidationError("Session ID must be between 8 and 128 characters")
    
    # Check for valid characters (alphanumeric, hyphens, underscores)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        raise ValidationError("Session ID can only contain letters, numbers, hyphens, and underscores")


def validate_boolean_field(value: Any, field_name: str) -> bool:
    """
    Validate and convert boolean field.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        
    Returns:
        Boolean value
        
    Raises:
        ValidationError: If value cannot be converted to boolean
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        lower_value = value.lower()
        if lower_value in ('true', '1', 'yes', 'on'):
            return True
        elif lower_value in ('false', '0', 'no', 'off'):
            return False
    
    elif isinstance(value, int):
        return bool(value)
    
    raise ValidationError(f"{field_name} must be a boolean value")
