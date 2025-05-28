"""
REST API routes for MetaFunction.

This module provides JSON API endpoints for programmatic access to
MetaFunction's paper analysis capabilities.
"""

import logging
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest

from app.services.ai_service import AIService
from app.services.paper_service import PaperService
from app.utils.validators import validate_request_data
from app.utils.exceptions import APIError, ValidationError

# Create blueprint
api_bp = Blueprint('api', __name__)

# Initialize services
ai_service = AIService()
paper_service = PaperService()

logger = logging.getLogger(__name__)

@api_bp.route('/models', methods=['GET'])
def get_models():
    """Get list of available AI models."""
    try:
        models = ai_service.get_available_models()
        model_info = {}
        
        for model in models:
            info = ai_service.get_model_info(model)
            model_info[model] = info
        
        return jsonify({
            'status': 'success',
            'models': models,
            'model_info': model_info,
            'default_model': 'gpt-4o-mini'
        })
        
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve models',
            'error': str(e)
        }), 500

@api_bp.route('/analyze', methods=['POST'])
def analyze_paper():
    """
    Analyze a scientific paper with AI.
    
    Expected JSON payload:
    {
        "query": "Your question or paper identifier",
        "model": "gpt-4o-mini",  # optional
        "use_cache": true,       # optional
        "include_metadata": true # optional
    }
    """
    try:
        # Validate request
        data = request.get_json()
        if not data:
            raise BadRequest("No JSON data provided")
        
        # Validate required fields
        required_fields = {'query'}
        validate_request_data(data, required_fields)
        
        query = data['query']
        model = data.get('model', 'gpt-4o-mini')
        use_cache = data.get('use_cache', True)
        include_metadata = data.get('include_metadata', True)
        
        logger.info(f"API analyze request - Model: {model}, Query length: {len(query)}")
        
        # Validate model
        if not ai_service.validate_model(model):
            available_models = ai_service.get_available_models()
            raise ValidationError(f"Invalid model '{model}'. Available: {available_models}")
        
        # Process paper query
        paper_result = paper_service.process_query(query)
        
        # Build prompt
        if paper_result.has_content:
            prompt = paper_service.build_enhanced_prompt(query, paper_result)
        else:
            prompt = query
        
        # Get AI response
        response = ai_service.get_response(
            model=model,
            prompt=prompt,
            use_cache=use_cache
        )
        
        # Build response
        result = {
            'status': 'success',
            'response': response,
            'model_used': model,
            'has_paper_context': paper_result.has_content
        }
        
        if include_metadata and paper_result.has_content:
            result['paper_metadata'] = paper_result.to_dict()
        
        return jsonify(result)
        
    except ValidationError as e:
        logger.warning(f"Validation error in analyze: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'error': str(e)
        }), 400
        
    except APIError as e:
        logger.error(f"API error in analyze: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Service error',
            'error': str(e)
        }), 503
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500

@api_bp.route('/paper/resolve', methods=['POST'])
def resolve_paper():
    """
    Resolve paper metadata and content.
    
    Expected JSON payload:
    {
        "doi": "10.1000/example",     # optional
        "pmid": "12345678",           # optional
        "title": "Paper title",      # optional
        "pmcid": "PMC123456"         # optional
    }
    """
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("No JSON data provided")
        
        doi = data.get('doi')
        pmid = data.get('pmid')
        title = data.get('title')
        pmcid = data.get('pmcid')
        
        if not any([doi, pmid, title, pmcid]):
            raise ValidationError("At least one identifier (doi, pmid, title, pmcid) is required")
        
        logger.info(f"API resolve request - DOI: {doi}, PMID: {pmid}, Title: {bool(title)}")
        
        # Resolve paper
        paper_result = paper_service.resolve_paper(
            doi=doi, pmid=pmid, title=title, pmcid=pmcid
        )
        
        return jsonify({
            'status': 'success',
            'paper': paper_result.to_dict()
        })
        
    except ValidationError as e:
        logger.warning(f"Validation error in resolve: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'error': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Error resolving paper: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to resolve paper',
            'error': str(e)
        }), 500

@api_bp.route('/paper/test_sources', methods=['POST'])
def test_paper_sources():
    """
    Test paper availability across different sources.
    
    Expected JSON payload:
    {
        "doi": "10.1000/example",     # optional
        "pmid": "12345678",           # optional
        "title": "Paper title",      # optional
        "pmcid": "PMC123456"         # optional
    }
    """
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("No JSON data provided")
        
        doi = data.get('doi')
        pmid = data.get('pmid')
        title = data.get('title')
        pmcid = data.get('pmcid')
        
        if not any([doi, pmid, title, pmcid]):
            raise ValidationError("At least one identifier is required")
        
        logger.info(f"API test sources request")
        
        # Test all sources
        test_results = paper_service.test_all_sources(
            doi=doi, pmid=pmid, title=title, pmcid=pmcid
        )
        
        return jsonify({
            'status': 'success',
            'test_results': test_results
        })
        
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'error': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Error testing sources: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to test sources',
            'error': str(e)
        }), 500

@api_bp.route('/health', methods=['GET'])
def api_health():
    """API health check endpoint."""
    try:
        ai_health = ai_service.health_check()
        paper_health = paper_service.health_check()
        
        overall_healthy = (
            ai_health.get('overall_status') == 'healthy' and
            paper_health.get('overall_status') == 'healthy'
        )
        
        result = {
            'status': 'healthy' if overall_healthy else 'degraded',
            'services': {
                'ai_service': ai_health,
                'paper_service': paper_health
            },
            'api_version': '2.0',
            'endpoints': [
                '/api/models',
                '/api/analyze',
                '/api/paper/resolve',
                '/api/paper/test_sources',
                '/api/health'
            ]
        }
        
        status_code = 200 if overall_healthy else 503
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"API health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

# Error handlers for the API blueprint
@api_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return jsonify({
        'status': 'error',
        'message': 'Bad request',
        'error': str(error)
    }), 400

@api_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found',
        'error': str(error)
    }), 404

@api_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'status': 'error',
        'message': 'Internal server error',
        'error': 'An unexpected error occurred'
    }), 500
