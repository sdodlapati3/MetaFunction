"""
Web interface routes for MetaFunction.

This module contains the Flask routes for the web interface, including
the main chat interface and utility endpoints.
"""

import uuid
import logging
import subprocess
import json
import os
from pathlib import Path
from flask import Blueprint, render_template, request, session, send_file
from werkzeug.exceptions import BadRequest

from app.services.ai_service import AIService
from app.services.paper_service import PaperService
from app.services.logging_service import LoggingService
from app.services.logging_service import LoggingService

# Create blueprint
web_bp = Blueprint('web', __name__)

# Initialize services (these will be dependency-injected in production)
ai_service = AIService()
paper_service = PaperService()
logging_service = LoggingService()

logger = logging.getLogger(__name__)

@web_bp.route('/')
def index():
    """Render the index page with model selection dropdown."""
    # Ensure session has an ID
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    
    # Get available models from AI service
    models = ai_service.get_available_models()
    default_model = "gpt-4o-mini"
    
    logger.info(f"Index page loaded for session {session['session_id']}")
    
    return render_template(
        "index.html", 
        models=models, 
        default_model=default_model
    )

@web_bp.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests with the selected model."""
    try:
        # Extract request parameters
        user_input = request.form.get("message") or request.form.get("user_input", "").strip()
        selected_model = request.form.get("model", "gpt-4o-mini")
        session_id = session.get("session_id", "unknown")
        ignore_cache = request.form.get("ignore_cache") == "true"
        
        if not user_input:
            raise BadRequest("No input provided")
        
        logger.info(f"Processing chat request for session {session_id}")
        logger.info(f"Selected model: {selected_model}, Input length: {len(user_input)}")
        
        # Process the paper query if it contains identifiers
        paper_result = paper_service.process_query(user_input)
        
        # Build enhanced prompt with paper context
        if paper_result.has_content:
            prompt = paper_service.build_enhanced_prompt(user_input, paper_result)
            logger.info("Using enhanced context with paper details")
        else:
            prompt = user_input
            logger.info("No paper details found, using original query")
        
        # Get AI response
        response = ai_service.get_response(
            model=selected_model,
            prompt=prompt,
            use_cache=not ignore_cache
        )
        
        # Log the interaction
        logging_service.log_chat(
            session_id=session_id,
            user_input=user_input,
            response=response,
            paper_info=paper_result.to_dict(),
            model=selected_model
        )
        
        # Render response
        return render_template(
            "index.html",
            models=ai_service.get_available_models(),
            default_model=selected_model,
            response=response,
            paper_info=paper_result.to_dict()
        )
        
    except BadRequest as e:
        logger.warning(f"Bad request in chat: {e}")
        error_message = str(e)
    except Exception as e:
        logger.error(f"Unhandled exception in chat: {str(e)}")
        error_message = f"An error occurred: {str(e)}"
    
    # Error response
    return render_template(
        "index.html",
        models=ai_service.get_available_models(),
        default_model="gpt-4o-mini",
        response=error_message
    )

@web_bp.route('/download_log')
def download_log():
    """Download the chat log file."""
    log_file = logging_service.get_chat_log_path()
    
    if log_file.exists():
        return send_file(log_file, as_attachment=True)
    else:
        return "No log file found.", 404

@web_bp.route('/download_metadata')
def download_metadata():
    """Download the metadata JSON file."""
    metadata_file = logging_service.get_metadata_log_path()
    
    if metadata_file.exists():
        return send_file(metadata_file, as_attachment=True)
    else:
        return "No metadata file found.", 404

@web_bp.route('/view_metadata')
def view_metadata():
    """View metadata in HTML format."""
    try:
        metadata_entries = logging_service.get_metadata_entries()
        
        if not metadata_entries:
            return "<h3>No metadata logged yet.</h3>"
        
        # Build HTML table
        html = "<h2>Metadata Log</h2><table border=1 cellpadding=6>"
        html += "<tr><th>Timestamp</th><th>Title</th><th>DOI</th><th>PMID</th><th>Datasets</th><th>Treatments</th></tr>"
        
        for entry in metadata_entries:
            html += f"<tr>"
            html += f"<td>{entry.get('timestamp', '')}</td>"
            html += f"<td>{entry.get('title', '')}</td>"
            html += f"<td>{entry.get('doi', '')}</td>"
            html += f"<td>{entry.get('pmid', '')}</td>"
            html += f"<td>{', '.join(entry.get('datasets', []))}</td>"
            html += f"<td>{', '.join(entry.get('treatments', []))}</td>"
            html += "</tr>"
        
        html += "</table>"
        return html
        
    except Exception as e:
        logger.error(f"Error viewing metadata: {e}")
        return f"<h3>Error reading metadata: {e}</h3>"

@web_bp.route('/test_sources', methods=['GET', 'POST'])
def test_sources():
    """Test and display full text access from different sources."""
    if request.method == 'GET':
        return render_template('test_sources.html')
    
    # POST request - run tests
    try:
        doi = request.form.get('doi')
        pmid = request.form.get('pmid')
        title = request.form.get('title')
        pmcid = request.form.get('pmcid')
        
        if not any([doi, pmid, title, pmcid]):
            return render_template(
                'test_sources.html',
                error="Please provide either DOI, PMID, title, or PMCID"
            )
        
        # Run source tests
        test_results = paper_service.test_all_sources(
            doi=doi, pmid=pmid, title=title, pmcid=pmcid
        )
        
        return render_template('test_sources.html', results=test_results)
        
    except Exception as e:
        logger.error(f"Error in test_sources: {e}")
        return render_template(
            'test_sources.html',
            error=f"An error occurred: {str(e)}"
        )

@web_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check AI service health
        ai_health = ai_service.health_check()
        
        # Check paper service health
        paper_health = paper_service.health_check()
        
        # Overall health status
        overall_healthy = (
            ai_health.get('overall_status') == 'healthy' and
            paper_health.get('overall_status') == 'healthy'
        )
        
        health_data = {
            'status': 'healthy' if overall_healthy else 'degraded',
            'ai_service': ai_health,
            'paper_service': paper_health,
            'timestamp': logging_service.get_current_timestamp()
        }
        
        status_code = 200 if overall_healthy else 503
        return health_data, status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': logging_service.get_current_timestamp()
        }, 503

@web_bp.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 errors."""
    return '', 204  # No content

@web_bp.route('/github-actions')
def github_actions_dashboard():
    """Enhanced GitHub Actions status dashboard with monitoring."""
    try:
        # Get paths for scripts
        validation_script = Path(__file__).parent.parent.parent / 'scripts' / 'validate-github-actions.py'
        monitoring_script = Path(__file__).parent.parent.parent / 'scripts' / 'github-actions-monitor.py'
        repo_path = Path(__file__).parent.parent.parent
        
        # Get GitHub token from environment
        github_token = os.environ.get('GITHUB_TOKEN')
        
        # Initialize combined report
        combined_report = {
            'repository': 'MetaFunction',
            'timestamp': logging_service.get_current_timestamp(),
            'validation_results': {
                'syntax': [{'status': 'unknown', 'message': 'Unable to validate'}],
                'secrets': [{'status': 'unknown', 'message': 'Token required'}],
                'dependencies': [{'status': 'unknown', 'message': 'Unable to check'}],
                'test_files': [{'status': 'unknown', 'message': 'Unable to check'}]
            },
            'monitoring_data': {
                'health': {'level': 'unknown', 'score': 0, 'recommendations': []},
                'summary': {'total_runs': 0, 'success_rate': 0, 'failure_rate': 0},
                'recent_runs': [],
                'alerts': []
            },
            'script_outputs': {}
        }
        
        # Run validation script
        if validation_script.exists():
            try:
                cmd = [
                    'python3', str(validation_script),
                    '--repo-path', str(repo_path),
                    '--output', '/tmp/github_validation_report.json'
                ]
                
                if github_token:
                    cmd.extend(['--token', github_token])
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                combined_report['script_outputs']['validation'] = {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode
                }
                
                # Load validation results
                if os.path.exists('/tmp/github_validation_report.json'):
                    with open('/tmp/github_validation_report.json', 'r') as f:
                        validation_data = json.load(f)
                        combined_report['validation_results'] = validation_data.get('validation_results', combined_report['validation_results'])
                        
            except Exception as e:
                logger.error(f"Validation script error: {e}")
                combined_report['script_outputs']['validation'] = {'error': str(e)}
        
        # Run monitoring script  
        if monitoring_script.exists():
            try:
                cmd = [
                    'python3', str(monitoring_script),
                    '--repo-path', str(repo_path),
                    '--dashboard',
                    '--output', '/tmp/github_monitoring_report.json'
                ]
                
                if github_token:
                    cmd.extend(['--token', github_token])
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                combined_report['script_outputs']['monitoring'] = {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode
                }
                
                # Load monitoring results
                if os.path.exists('/tmp/github_monitoring_report.json'):
                    with open('/tmp/github_monitoring_report.json', 'r') as f:
                        monitoring_data = json.load(f)
                        combined_report['monitoring_data'] = {
                            'health': monitoring_data.get('health', combined_report['monitoring_data']['health']),
                            'summary': monitoring_data.get('summary', combined_report['monitoring_data']['summary']),
                            'recent_runs': monitoring_data.get('recent_runs', [])[:10],
                            'alerts': monitoring_data.get('alerts', [])[:5]
                        }
                        
            except Exception as e:
                logger.error(f"Monitoring script error: {e}")
                combined_report['script_outputs']['monitoring'] = {'error': str(e)}
        
        return render_template('github_actions_enhanced_dashboard.html', report=combined_report)
        
    except Exception as e:
        logger.error(f"GitHub Actions dashboard error: {e}")
        error_report = {
            'repository': 'MetaFunction',
            'timestamp': logging_service.get_current_timestamp(),
            'error': str(e),
            'validation_results': {
                'syntax': [{'status': 'error', 'message': f'Dashboard error: {str(e)}'}],
                'secrets': [{'status': 'error', 'message': f'Dashboard error: {str(e)}'}],
                'dependencies': [{'status': 'error', 'message': f'Dashboard error: {str(e)}'}],
                'test_files': [{'status': 'error', 'message': f'Dashboard error: {str(e)}'}]
            },
            'monitoring_data': {
                'health': {'level': 'error', 'score': 0, 'recommendations': []},
                'summary': {'total_runs': 0, 'success_rate': 0, 'failure_rate': 0},
                'recent_runs': [],
                'alerts': []
            }
        }
        return render_template('github_actions_enhanced_dashboard.html', report=error_report)
