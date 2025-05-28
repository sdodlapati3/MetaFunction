"""
Custom exceptions for the MetaFunction application.
"""

import logging
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

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


def register_error_handlers(app: Flask) -> None:
    """
    Register error handlers for the Flask application.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle validation errors."""
        logger.warning(f"Validation error: {error}")
        return jsonify({
            'error': 'Validation Error',
            'message': str(error),
            'status': 400
        }), 400
    
    @app.errorhandler(ModelNotFoundError)
    def handle_model_not_found_error(error):
        """Handle model not found errors."""
        logger.error(f"Model not found: {error}")
        return jsonify({
            'error': 'Model Not Found',
            'message': str(error),
            'status': 404
        }), 404
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle external API errors."""
        logger.error(f"API error: {error}")
        return jsonify({
            'error': 'API Error',
            'message': str(error),
            'status': 502
        }), 502
    
    @app.errorhandler(ConfigurationError)
    def handle_configuration_error(error):
        """Handle configuration errors."""
        logger.error(f"Configuration error: {error}")
        return jsonify({
            'error': 'Configuration Error',
            'message': 'Server configuration error',
            'status': 500
        }), 500
    
    @app.errorhandler(PaperResolutionError)
    def handle_paper_resolution_error(error):
        """Handle paper resolution errors."""
        logger.warning(f"Paper resolution error: {error}")
        return jsonify({
            'error': 'Paper Resolution Error',
            'message': str(error),
            'status': 404
        }), 404
    
    @app.errorhandler(MetaFunctionError)
    def handle_metafunction_error(error):
        """Handle general MetaFunction errors."""
        logger.error(f"MetaFunction error: {error}")
        return jsonify({
            'error': 'Application Error',
            'message': str(error),
            'status': 500
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP error {error.code}: {error.description}")
        return jsonify({
            'error': error.name,
            'message': error.description,
            'status': error.code
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {error}", exc_info=True)
        
        # Don't expose internal error details in production
        if app.config.get('DEBUG'):
            message = str(error)
        else:
            message = 'An unexpected error occurred'
        
        return jsonify({
            'error': 'Internal Server Error',
            'message': message,
            'status': 500
        }), 500
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors."""
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested endpoint was not found',
                'status': 404
            }), 404
        else:
            # For web routes, you might want to render a template
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested page was not found',
                'status': 404
            }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle method not allowed errors."""
        return jsonify({
            'error': 'Method Not Allowed',
            'message': f'The {request.method} method is not allowed for this endpoint',
            'status': 405
        }), 405
