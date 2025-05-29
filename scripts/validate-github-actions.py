#!/usr/bin/env python3
"""
GitHub Actions Status Validator and Monitor for MetaFunction
Provides comprehensive monitoring, validation, and troubleshooting for CI/CD pipelines.
"""

import os
import sys
import json
import time
import requests
import argparse
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import re

class GitHubActionsValidator:
    """Validate and monitor GitHub Actions workflows."""
    
    def __init__(self, repo_path: str, github_token: Optional[str] = None):
        """Initialize the validator.
        
        Args:
            repo_path: Path to the Git repository
            github_token: GitHub personal access token for API access
        """
        self.repo_path = Path(repo_path)
        self.github_token = github_token or os.environ.get('GITHUB_TOKEN')
        self.api_base = "https://api.github.com"
        
        # Get repository info
        self.owner, self.repo = self._get_repo_info()
        
        # Setup session with authentication
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            })
    
    def _get_repo_info(self) -> Tuple[str, str]:
        """Extract owner and repo name from git remote."""
        try:
            # Try origin first, then fall back to any available remote
            remotes_to_try = ['origin', 'sanjeevarddodlapati', 'sdodlapa', 'sdodlapati3']
            remote_url = None
            
            for remote in remotes_to_try:
                try:
                    result = subprocess.run(
                        ['git', 'remote', 'get-url', remote],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    remote_url = result.stdout.strip()
                    break
                except subprocess.CalledProcessError:
                    continue
            
            if not remote_url:
                # Try to get any remote
                result = subprocess.run(
                    ['git', 'remote'],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                remotes = result.stdout.strip().split('\n')
                if remotes and remotes[0]:
                    result = subprocess.run(
                        ['git', 'remote', 'get-url', remotes[0]],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    remote_url = result.stdout.strip()
            
            if not remote_url:
                raise ValueError("No git remotes found")
            
            # Parse GitHub URL
            if 'github.com' in remote_url:
                if remote_url.startswith('https://'):
                    # https://github.com/owner/repo.git or https://token@github.com/owner/repo.git
                    if '@github.com' in remote_url:
                        parts = remote_url.split('@github.com/')[1].replace('.git', '').split('/')
                    else:
                        parts = remote_url.replace('https://github.com/', '').replace('.git', '').split('/')
                else:
                    # git@github.com:owner/repo.git
                    parts = remote_url.split(':')[1].replace('.git', '').split('/')
                
                if len(parts) >= 2:
                    return parts[0], parts[1]
            
            raise ValueError(f"Cannot parse GitHub repository from: {remote_url}")
            
        except subprocess.CalledProcessError:
            # Fallback - assume MetaFunction repository based on directory structure
            return "SanjeevaRDodlapati", "MetaFunction"
    
    def validate_workflow_syntax(self) -> List[Dict]:
        """Validate YAML syntax of all workflow files."""
        workflows_dir = self.repo_path / '.github' / 'workflows'
        results = []
        
        if not workflows_dir.exists():
            return [{'status': 'error', 'message': 'No .github/workflows directory found'}]
        
        for workflow_file in workflows_dir.glob('*.yml'):
            try:
                with open(workflow_file, 'r') as f:
                    yaml.safe_load(f)
                
                results.append({
                    'file': workflow_file.name,
                    'status': 'valid',
                    'message': 'Valid YAML syntax'
                })
                
            except yaml.YAMLError as e:
                results.append({
                    'file': workflow_file.name,
                    'status': 'invalid',
                    'message': f'YAML syntax error: {str(e)}'
                })
            except Exception as e:
                results.append({
                    'file': workflow_file.name,
                    'status': 'error',
                    'message': f'Error reading file: {str(e)}'
                })
        
        return results
    
    def check_required_secrets(self) -> List[Dict]:
        """Check if required secrets are configured."""
        workflows_dir = self.repo_path / '.github' / 'workflows'
        required_secrets = set()
        
        # Extract secrets from workflow files
        for workflow_file in workflows_dir.glob('*.yml'):
            try:
                with open(workflow_file, 'r') as f:
                    content = f.read()
                
                # Find secrets.SECRET_NAME patterns
                secrets = re.findall(r'\$\{\{\s*secrets\.([A-Z_]+)\s*\}\}', content)
                required_secrets.update(secrets)
                
            except Exception:
                continue
        
        results = []
        
        if not self.github_token:
            return [{
                'status': 'warning',
                'message': 'Cannot check secrets without GitHub token'
            }]
        
        # Check each secret via GitHub API
        for secret in required_secrets:
            try:
                response = self.session.get(
                    f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/secrets/{secret}"
                )
                
                if response.status_code == 200:
                    results.append({
                        'secret': secret,
                        'status': 'configured',
                        'message': 'Secret is configured'
                    })
                elif response.status_code == 404:
                    results.append({
                        'secret': secret,
                        'status': 'missing',
                        'message': 'Secret not configured'
                    })
                else:
                    results.append({
                        'secret': secret,
                        'status': 'error',
                        'message': f'API error: {response.status_code}'
                    })
                    
            except Exception as e:
                results.append({
                    'secret': secret,
                    'status': 'error',
                    'message': f'Error checking secret: {str(e)}'
                })
        
        return results
    
    def get_workflow_runs(self, limit: int = 10) -> List[Dict]:
        """Get recent workflow runs."""
        if not self.github_token:
            return [{'status': 'error', 'message': 'GitHub token required for API access'}]
        
        try:
            response = self.session.get(
                f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/runs",
                params={'per_page': limit}
            )
            
            if response.status_code != 200:
                return [{'status': 'error', 'message': f'API error: {response.status_code}'}]
            
            data = response.json()
            runs = []
            
            for run in data.get('workflow_runs', []):
                runs.append({
                    'id': run['id'],
                    'workflow_name': run['name'],
                    'status': run['status'],
                    'conclusion': run['conclusion'],
                    'created_at': run['created_at'],
                    'updated_at': run['updated_at'],
                    'branch': run['head_branch'],
                    'commit_sha': run['head_sha'][:7],
                    'html_url': run['html_url']
                })
            
            return runs
            
        except Exception as e:
            return [{'status': 'error', 'message': f'Error fetching runs: {str(e)}'}]
    
    def check_dependencies(self) -> List[Dict]:
        """Check for missing dependencies referenced in workflows."""
        requirements_files = [
            self.repo_path / 'requirements' / 'requirements.txt',
            self.repo_path / 'requirements' / 'requirements-dev.txt',
            self.repo_path / 'package.json'
        ]
        
        results = []
        
        # Check Python requirements
        for req_file in requirements_files:
            if req_file.exists() and req_file.name.endswith('.txt'):
                try:
                    with open(req_file, 'r') as f:
                        content = f.read()
                    
                    # Check for common testing dependencies
                    required_deps = ['pytest', 'flake8', 'mypy', 'bandit', 'safety']
                    missing_deps = []
                    
                    for dep in required_deps:
                        if dep not in content:
                            missing_deps.append(dep)
                    
                    if missing_deps:
                        results.append({
                            'file': req_file.name,
                            'status': 'incomplete',
                            'missing': missing_deps,
                            'message': f'Missing dependencies: {", ".join(missing_deps)}'
                        })
                    else:
                        results.append({
                            'file': req_file.name,
                            'status': 'complete',
                            'message': 'All required dependencies present'
                        })
                        
                except Exception as e:
                    results.append({
                        'file': req_file.name,
                        'status': 'error',
                        'message': f'Error reading file: {str(e)}'
                    })
        
        return results
    
    def check_test_files(self) -> List[Dict]:
        """Check if referenced test files exist."""
        test_files = [
            'tests/performance/locustfile.py',
            'tests/post_deployment/health_check.py',
            'tests/conftest.py'
        ]
        
        results = []
        
        for test_file in test_files:
            file_path = self.repo_path / test_file
            
            if file_path.exists():
                results.append({
                    'file': test_file,
                    'status': 'exists',
                    'message': 'Test file found'
                })
            else:
                results.append({
                    'file': test_file,
                    'status': 'missing',
                    'message': 'Test file not found'
                })
        
        return results
    
    def generate_status_report(self) -> Dict:
        """Generate comprehensive status report."""
        print("🔍 Validating GitHub Actions configuration...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'repository': f"{self.owner}/{self.repo}",
            'validation_results': {}
        }
        
        # Validate workflow syntax
        print("  ├── Checking workflow syntax...")
        report['validation_results']['syntax'] = self.validate_workflow_syntax()
        
        # Check secrets
        print("  ├── Checking required secrets...")
        report['validation_results']['secrets'] = self.check_required_secrets()
        
        # Check dependencies
        print("  ├── Checking dependencies...")
        report['validation_results']['dependencies'] = self.check_dependencies()
        
        # Check test files
        print("  ├── Checking test files...")
        report['validation_results']['test_files'] = self.check_test_files()
        
        # Get recent runs
        print("  └── Fetching recent workflow runs...")
        report['recent_runs'] = self.get_workflow_runs()
        
        return report
    
    def print_summary(self, report: Dict):
        """Print a formatted summary of the validation results."""
        print("\n" + "="*70)
        print("🚀 GITHUB ACTIONS STATUS REPORT")
        print("="*70)
        print(f"Repository: {report['repository']}")
        print(f"Generated: {report['timestamp']}")
        print()
        
        # Syntax validation
        syntax_results = report['validation_results']['syntax']
        valid_count = sum(1 for r in syntax_results if r.get('status') == 'valid')
        total_count = len(syntax_results)
        
        print(f"📝 Workflow Syntax: {valid_count}/{total_count} valid")
        for result in syntax_results:
            if result.get('status') != 'valid':
                status_emoji = "❌" if result.get('status') == 'invalid' else "⚠️"
                print(f"  {status_emoji} {result.get('file', 'Unknown')}: {result.get('message', '')}")
        
        # Secrets check
        secrets_results = report['validation_results']['secrets']
        if secrets_results:
            configured_count = sum(1 for r in secrets_results if r.get('status') == 'configured')
            total_secrets = len(secrets_results)
            
            print(f"\n🔐 Secrets: {configured_count}/{total_secrets} configured")
            for result in secrets_results:
                if result.get('status') != 'configured':
                    status_emoji = "❌" if result.get('status') == 'missing' else "⚠️"
                    print(f"  {status_emoji} {result.get('secret', 'Unknown')}: {result.get('message', '')}")
        
        # Dependencies
        deps_results = report['validation_results']['dependencies']
        if deps_results:
            print(f"\n📦 Dependencies:")
            for result in deps_results:
                status_emoji = "✅" if result.get('status') == 'complete' else "⚠️"
                print(f"  {status_emoji} {result.get('file', 'Unknown')}: {result.get('message', '')}")
        
        # Test files
        test_results = report['validation_results']['test_files']
        if test_results:
            exists_count = sum(1 for r in test_results if r.get('status') == 'exists')
            total_tests = len(test_results)
            
            print(f"\n🧪 Test Files: {exists_count}/{total_tests} found")
            for result in test_results:
                if result.get('status') != 'exists':
                    print(f"  ❌ {result.get('file', 'Unknown')}: {result.get('message', '')}")
        
        # Recent runs
        recent_runs = report.get('recent_runs', [])
        if recent_runs and isinstance(recent_runs, list) and 'status' not in recent_runs[0]:
            print(f"\n📊 Recent Workflow Runs:")
            for run in recent_runs[:5]:
                status_emoji = "✅" if run.get('conclusion') == 'success' else "❌" if run.get('conclusion') == 'failure' else "🔄"
                print(f"  {status_emoji} {run.get('workflow_name', 'Unknown')} ({run.get('commit_sha', 'Unknown')}) - {run.get('conclusion', 'Unknown')}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Validate and monitor GitHub Actions workflows'
    )
    parser.add_argument(
        '--repo-path',
        default='.',
        help='Path to the Git repository (default: current directory)'
    )
    parser.add_argument(
        '--token',
        help='GitHub personal access token (can also use GITHUB_TOKEN env var)'
    )
    parser.add_argument(
        '--output',
        help='Output file for detailed JSON report'
    )
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Run in monitoring mode (continuous)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Monitoring interval in seconds (default: 300)'
    )
    
    args = parser.parse_args()
    
    try:
        validator = GitHubActionsValidator(args.repo_path, args.token)
        
        if args.monitor:
            print("🔄 Starting GitHub Actions monitoring...")
            while True:
                report = validator.generate_status_report()
                validator.print_summary(report)
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(report, f, indent=2)
                
                print(f"\n⏰ Next check in {args.interval} seconds...")
                time.sleep(args.interval)
        else:
            report = validator.generate_status_report()
            validator.print_summary(report)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"\n📄 Detailed report saved to: {args.output}")
    
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()