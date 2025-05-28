"""
Flask application factory and main entry point.

This module implements the application factory pattern for better testability
and configuration management.
"""

import os
import logging
from flask import Flask

def create_app(config_class=None):
    """
    Application factory function.
    
    Args:
        config_class: Configuration class to use. If None, will be determined
                     from environment variables.
    
    Returns:
        Flask application instance
    """
    # Create Flask app
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Load configuration
    if config_class is None:
        from app.config import get_config
        config_class = get_config()
    
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # Initialize logging
    from app.services.logging_service import setup_logging
    setup_logging()
    
    # Register blueprints
    from app.routes.web import web_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register error handlers
    from app.utils.exceptions import register_error_handlers
    register_error_handlers(app)
    
    return app

def main():
    """Main entry point for development server."""
    app = create_app()
    
    # Get port from environment or default to 8000
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logging.info(f"Starting MetaFunction on port {port}")
    logging.info(f"Debug mode: {debug}")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )

if __name__ == '__main__':
    main()
