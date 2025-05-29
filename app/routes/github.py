"""
GitHub Actions status API endpoint for MetaFunction web interface.
Provides real-time workflow status information.
"""

import os
import requests
from flask import Blueprint, jsonify, render_template, request
from datetime import datetime
import logging

# Create blueprint for GitHub Actions integration
github_bp = Blueprint('github', __name__, url_prefix='/github')

logger = logging.getLogger(__name__)


class GitHubActionsService:
    """Service for interacting with GitHub Actions API."""
    
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        self.repo_owner = os.getenv('GITHUB_REPO_OWNER', 'your-username')
        self.repo_name = os.getenv('GITHUB_REPO_NAME', 'MetaFunction')
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            })
    
    def get_workflow_status(self) -> dict:
        """Get current status of all workflows."""
        try:
            # Get workflows
            workflows_response = self.session.get(f"{self.base_url}/actions/workflows")
            if workflows_response.status_code != 200:
                return {"error": "Failed to fetch workflows", "status_code": workflows_response.status_code}
            
            workflows = workflows_response.json().get('workflows', [])
            workflow_statuses = []
            
            for workflow in workflows:
                # Get latest run for each workflow
                runs_response = self.session.get(
                    f"{self.base_url}/actions/workflows/{workflow['id']}/runs",
                    params={'per_page': 1}
                )
                
                if runs_response.status_code == 200:
                    runs = runs_response.json().get('workflow_runs', [])
                    if runs:
                        latest_run = runs[0]
                        workflow_statuses.append({
                            'name': workflow['name'],
                            'file': workflow['path'],
                            'state': workflow['state'],
                            'status': latest_run['status'],
                            'conclusion': latest_run.get('conclusion'),
                            'branch': latest_run['head_branch'],
                            'commit': latest_run['head_sha'][:8],
                            'created_at': latest_run['created_at'],
                            'updated_at': latest_run['updated_at'],
                            'html_url': latest_run['html_url']
                        })
                    else:
                        workflow_statuses.append({
                            'name': workflow['name'],
                            'file': workflow['path'],
                            'state': workflow['state'],
                            'status': 'no_runs',
                            'conclusion': None
                        })
            
            return {
                'repository': f"{self.repo_owner}/{self.repo_name}",
                'workflows': workflow_statuses,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except requests.RequestException as e:
            logger.error(f"GitHub API error: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": "Internal server error"}


# Initialize service
github_service = GitHubActionsService()


@github_bp.route('/status')
def workflow_status():
    """Get workflow status as JSON."""
    status_data = github_service.get_workflow_status()
    return jsonify(status_data)


@github_bp.route('/dashboard')
def workflow_dashboard():
    """Render workflow status dashboard."""
    return render_template('github/dashboard.html')


@github_bp.route('/health')
def github_health():
    """Health check for GitHub integration."""
    try:
        # Simple check if we can reach GitHub API
        response = github_service.session.get(
            f"{github_service.base_url}",
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify({
                'status': 'healthy',
                'github_api': 'accessible',
                'token_configured': bool(github_service.token),
                'repository': f"{github_service.repo_owner}/{github_service.repo_name}"
            })
        else:
            return jsonify({
                'status': 'degraded',
                'github_api': 'accessible_with_errors',
                'status_code': response.status_code
            }), 503
            
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'github_api': 'inaccessible'
        }), 503
