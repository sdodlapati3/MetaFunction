#!/usr/bin/env python3
"""
MetaFunction - AI-Powered Scientific Paper Analysis Platform

This is the main entry point for the MetaFunction application.
It uses the application factory pattern implemented in app/main.py
for better maintainability and testing.

Usage:
    python app.py                    # Start development server
    python app.py --port 8080        # Start on custom port
    python app.py --production       # Start in production mode
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='MetaFunction - AI-Powered Scientific Paper Analysis Platform'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=int(os.getenv('PORT', 8000)),
        help='Port to run the server on (default: 8000)'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--production',
        action='store_true',
        help='Run in production mode (disables debug)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run in debug mode (overrides production)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set the logging level (default: INFO)'
    )
    
    return parser.parse_args()


def setup_ssl_context():
    """Setup SSL context for secure connections."""
    import ssl
    import certifi
    
    # Create unverified SSL context for development/testing
    ssl._create_default_https_context = ssl._create_unverified_context
    
    # Use certifi certificates
    os.environ['SSL_CERT_FILE'] = certifi.where()


def validate_environment():
    """Validate that required environment variables are set."""
    required_vars = []
    optional_vars = [
        'OPENAI_API_KEY',
        'DEEPSEEK_API_KEY', 
        'PERPLEXITY_API_KEY',
        'DEEPSEEK_USERNAME',
        'DEEPSEEK_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Check if at least one AI service is configured
    ai_services = ['OPENAI_API_KEY', 'DEEPSEEK_API_KEY', 'PERPLEXITY_API_KEY']
    if not any(os.getenv(var) for var in ai_services):
        logging.warning("No AI service API keys found. Some features may not work.")
    
    logging.info("Environment validation completed")


def main():
    """Main entry point for the application."""
    args = parse_arguments()
    
    # Configure logging
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting MetaFunction application")
    
    # Setup SSL context
    setup_ssl_context()
    
    # Validate environment
    validate_environment()
    
    # Import and create the Flask app using the application factory
    try:
        from app.main import create_app
        app = create_app()
    except ImportError as e:
        logger.error(f"Failed to import application factory: {e}")
        logger.error("Make sure you're in the correct directory and dependencies are installed")
        sys.exit(1)
    
    # Determine if we're running in debug mode
    debug_mode = args.debug or (not args.production and os.getenv('FLASK_ENV') == 'development')
    
    logger.info(f"Starting server on {args.host}:{args.port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Environment: {'development' if debug_mode else 'production'}")
    
    # Print startup banner
    print("\n" + "="*60)
    print("🧬 MetaFunction - AI-Powered Scientific Paper Analysis")
    print("="*60)
    print(f"🌐 Server: http://{args.host}:{args.port}")
    print(f"🔧 Mode: {'Development' if debug_mode else 'Production'}")
    print(f"📊 Log Level: {args.log_level}")
    print("="*60 + "\n")
    
    try:
        # Start the Flask development server
        app.run(
            host=args.host,
            port=args.port,
            debug=debug_mode,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
