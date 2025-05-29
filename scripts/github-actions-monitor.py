#!/usr/bin/env python3
"""
GitHub Actions Status Monitor
Checks the status of GitHub Actions workflows and provides detailed reporting.
"""

import argparse
import requests
import json
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import time


class GitHubActionsMonitor:
    """Monitor GitHub Actions workflows and runs."""
    
    def __init__(self, repo_owner: str, repo_name: str, token: Optional[str] = None):
        """Initialize the monitor.
        
        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            token: GitHub personal access token (optional, for private repos)
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        
        self.session = requests.Session()
        if token:
            self.session.headers.update({
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            })
    
    def get_workflows(self) -> List[Dict]:
        """Get all workflows for the repository."""
        try:
            response = self.session.get(f"{self.base_url}/actions/workflows")
            response.raise_for_status()
            return response.json().get('workflows', [])
        except requests.RequestException as e:
            print(f"Error fetching workflows: {e}")
            return []
    
    def get_workflow_runs(self, workflow_id: str, branch: str = None, limit: int = 10) -> List[Dict]:
        """Get recent runs for a specific workflow.
        
        Args:
            workflow_id: Workflow ID or filename
            branch: Filter by branch (optional)
            limit: Maximum number of runs to fetch
            
        Returns:
            List of workflow runs
        """
        try:
            params = {'per_page': limit}
            if branch:
                params['branch'] = branch
            
            response = self.session.get(
                f"{self.base_url}/actions/workflows/{workflow_id}/runs",
                params=params
            )
            response.raise_for_status()
            return response.json().get('workflow_runs', [])
        except requests.RequestException as e:
            print(f"Error fetching workflow runs: {e}")
            return []
    
    def get_run_jobs(self, run_id: str) -> List[Dict]:
        """Get jobs for a specific workflow run."""
        try:
            response = self.session.get(f"{self.base_url}/actions/runs/{run_id}/jobs")
            response.raise_for_status()
            return response.json().get('jobs', [])
        except requests.RequestException as e:
            print(f"Error fetching run jobs: {e}")
            return []
    
    def format_duration(self, start_time: str, end_time: str = None) -> str:
        """Format duration between start and end times."""
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if end_time:
                end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                end = datetime.now(timezone.utc)
            
            duration = end - start
            total_seconds = int(duration.total_seconds())
            
            if total_seconds < 60:
                return f"{total_seconds}s"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                return f"{minutes}m {seconds}s"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}h {minutes}m"
        except Exception:
            return "Unknown"
    
    def get_status_emoji(self, status: str, conclusion: str = None) -> str:
        """Get emoji for workflow status."""
        if status == 'completed':
            if conclusion == 'success':
                return "✅"
            elif conclusion == 'failure':
                return "❌"
            elif conclusion == 'cancelled':
                return "🚫"
            elif conclusion == 'skipped':
                return "⏭️"
            else:
                return "❓"
        elif status == 'in_progress':
            return "🔄"
        elif status == 'queued':
            return "⏳"
        else:
            return "❓"
    
    def print_workflow_status(self, workflow: Dict, runs: List[Dict], detailed: bool = False):
        """Print status information for a workflow."""
        print(f"\n📋 {workflow['name']}")
        print(f"   File: {workflow['path']}")
        print(f"   State: {workflow['state']}")
        
        if not runs:
            print("   No recent runs found")
            return
        
        latest_run = runs[0]
        status_emoji = self.get_status_emoji(latest_run['status'], latest_run.get('conclusion'))
        
        print(f"   Latest: {status_emoji} {latest_run['status'].title()}")
        print(f"   Branch: {latest_run['head_branch']}")
        print(f"   Commit: {latest_run['head_sha'][:8]}")
        print(f"   Started: {latest_run['created_at']}")
        
        if latest_run['status'] == 'completed':
            duration = self.format_duration(latest_run['created_at'], latest_run['updated_at'])
            print(f"   Duration: {duration}")
        
        if detailed and len(runs) > 1:
            print(f"   Recent runs:")
            for run in runs[1:6]:  # Show up to 5 more runs
                emoji = self.get_status_emoji(run['status'], run.get('conclusion'))
                branch = run['head_branch']
                date = run['created_at'][:10]
                print(f"     {emoji} {branch} - {date}")
    
    def print_job_details(self, run_id: str, run_name: str):
        """Print detailed job information for a workflow run."""
        jobs = self.get_run_jobs(run_id)
        
        if not jobs:
            print(f"No jobs found for run {run_id}")
            return
        
        print(f"\n🔍 Job Details for: {run_name}")
        print("=" * 60)
        
        for job in jobs:
            status_emoji = self.get_status_emoji(job['status'], job.get('conclusion'))
            duration = self.format_duration(job['started_at'], job.get('completed_at'))
            
            print(f"{status_emoji} {job['name']}")
            print(f"   Status: {job['status']}")
            if job.get('conclusion'):
                print(f"   Conclusion: {job['conclusion']}")
            print(f"   Duration: {duration}")
            
            if job['status'] == 'completed' and job.get('conclusion') == 'failure':
                print(f"   ❌ Job failed - check logs for details")
                print(f"   🔗 Logs: {job['html_url']}")
            
            print()
    
    def check_failing_workflows(self) -> List[Dict]:
        """Get all workflows that are currently failing."""
        failing_workflows = []
        workflows = self.get_workflows()
        
        for workflow in workflows:
            runs = self.get_workflow_runs(workflow['id'], limit=1)
            if runs:
                latest_run = runs[0]
                if (latest_run['status'] == 'completed' and 
                    latest_run.get('conclusion') == 'failure'):
                    failing_workflows.append({
                        'workflow': workflow,
                        'run': latest_run
                    })
        
        return failing_workflows
    
    def generate_status_report(self, output_file: str = None):
        """Generate a comprehensive status report."""
        workflows = self.get_workflows()
        
        if not workflows:
            print("No workflows found or unable to access repository")
            return
        
        report_lines = []
        report_lines.append(f"# GitHub Actions Status Report")
        report_lines.append(f"Repository: {self.repo_owner}/{self.repo_name}")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        all_passing = True
        
        for workflow in workflows:
            runs = self.get_workflow_runs(workflow['id'], limit=5)
            
            if runs:
                latest_run = runs[0]
                status_emoji = self.get_status_emoji(latest_run['status'], latest_run.get('conclusion'))
                
                report_lines.append(f"## {status_emoji} {workflow['name']}")
                report_lines.append(f"- **File**: `{workflow['path']}`")
                report_lines.append(f"- **Status**: {latest_run['status'].title()}")
                
                if latest_run.get('conclusion'):
                    report_lines.append(f"- **Conclusion**: {latest_run['conclusion'].title()}")
                
                report_lines.append(f"- **Branch**: {latest_run['head_branch']}")
                report_lines.append(f"- **Last Run**: {latest_run['created_at']}")
                
                if latest_run['status'] == 'completed':
                    duration = self.format_duration(latest_run['created_at'], latest_run['updated_at'])
                    report_lines.append(f"- **Duration**: {duration}")
                
                if latest_run.get('conclusion') == 'failure':
                    all_passing = False
                    report_lines.append(f"- **Action Required**: ❌ Workflow is failing")
                    report_lines.append(f"- **Run URL**: {latest_run['html_url']}")
                
                report_lines.append("")
        
        # Add summary
        report_lines.insert(4, f"**Overall Status**: {'✅ All workflows passing' if all_passing else '❌ Some workflows failing'}")
        report_lines.insert(5, "")
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_content)
            print(f"Report saved to: {output_file}")
        else:
            print(report_content)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Monitor GitHub Actions workflows and status'
    )
    parser.add_argument(
        '--repo',
        required=True,
        help='Repository in format owner/name'
    )
    parser.add_argument(
        '--token',
        help='GitHub personal access token (can also use GITHUB_TOKEN env var)'
    )
    parser.add_argument(
        '--branch',
        help='Filter by specific branch'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed information including recent runs'
    )
    parser.add_argument(
        '--jobs',
        help='Show job details for specific run ID'
    )
    parser.add_argument(
        '--failing-only',
        action='store_true',
        help='Show only failing workflows'
    )
    parser.add_argument(
        '--report',
        help='Generate status report and save to file'
    )
    parser.add_argument(
        '--watch',
        type=int,
        help='Watch mode - refresh every N seconds'
    )
    
    args = parser.parse_args()
    
    # Parse repository
    try:
        repo_owner, repo_name = args.repo.split('/')
    except ValueError:
        print("Error: Repository must be in format 'owner/name'")
        sys.exit(1)
    
    # Get token
    token = args.token or os.getenv('GITHUB_TOKEN')
    
    # Initialize monitor
    monitor = GitHubActionsMonitor(repo_owner, repo_name, token)
    
    try:
        if args.report:
            monitor.generate_status_report(args.report)
            return
        
        if args.jobs:
            monitor.print_job_details(args.jobs, f"Run {args.jobs}")
            return
        
        def print_status():
            print(f"🔍 GitHub Actions Status for {args.repo}")
            print("=" * 60)
            
            if args.failing_only:
                failing = monitor.check_failing_workflows()
                if failing:
                    print(f"❌ Found {len(failing)} failing workflows:")
                    for item in failing:
                        monitor.print_workflow_status(
                            item['workflow'], 
                            [item['run']], 
                            args.detailed
                        )
                else:
                    print("✅ No failing workflows found!")
            else:
                workflows = monitor.get_workflows()
                for workflow in workflows:
                    runs = monitor.get_workflow_runs(
                        workflow['id'], 
                        args.branch, 
                        10 if args.detailed else 1
                    )
                    monitor.print_workflow_status(workflow, runs, args.detailed)
        
        if args.watch:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')
                print_status()
                print(f"\n🔄 Refreshing every {args.watch} seconds... (Ctrl+C to exit)")
                time.sleep(args.watch)
        else:
            print_status()
    
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
