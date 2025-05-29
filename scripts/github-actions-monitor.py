#!/usr/bin/env python3
"""
Enhanced GitHub Actions Monitor
Real-time monitoring with notifications and advanced analytics
"""

import os
import json
import time
import logging
import argparse
import requests
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class WorkflowRun:
    """Dataclass for workflow run information."""
    id: int
    name: str
    status: str
    conclusion: Optional[str]
    created_at: str
    updated_at: str
    commit_sha: str
    commit_message: str
    actor: str
    duration_minutes: Optional[float] = None
    

@dataclass
class MonitorAlert:
    """Dataclass for monitoring alerts."""
    level: str  # info, warning, error, critical
    title: str
    message: str
    timestamp: str
    workflow_run: Optional[WorkflowRun] = None


class GitHubActionsMonitor:
    """Enhanced GitHub Actions monitoring with real-time alerts."""
    
    def __init__(self, repo_path: str, github_token: Optional[str] = None):
        """Initialize the monitor.
        
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
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Store for tracking state changes
        self.last_known_runs = {}
        self.alerts = []
        
    def _get_repo_info(self) -> Tuple[str, str]:
        """Extract owner and repo name from git remote."""
        try:
            # Try multiple remotes in order of preference
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
    
    def get_workflow_runs(self, limit: int = 50) -> List[WorkflowRun]:
        """Get recent workflow runs with enhanced data."""
        if not self.github_token:
            self.logger.warning("GitHub token required for API access")
            return []
        
        try:
            response = self.session.get(
                f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/runs",
                params={'per_page': limit}
            )
            
            if response.status_code != 200:
                self.logger.error(f"API error: {response.status_code}")
                return []
            
            data = response.json()
            runs = []
            
            for run in data.get('workflow_runs', []):
                # Calculate duration if run is completed
                duration = None
                if run.get('conclusion') and run.get('created_at') and run.get('updated_at'):
                    try:
                        created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
                        updated = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
                        duration = (updated - created).total_seconds() / 60
                    except:
                        pass
                
                workflow_run = WorkflowRun(
                    id=run['id'],
                    name=run['name'],
                    status=run['status'],
                    conclusion=run['conclusion'],
                    created_at=run['created_at'],
                    updated_at=run['updated_at'],
                    commit_sha=run['head_sha'][:8],
                    commit_message=run.get('head_commit', {}).get('message', 'Unknown'),
                    actor=run.get('actor', {}).get('login', 'Unknown'),
                    duration_minutes=duration
                )
                runs.append(workflow_run)
            
            return runs
            
        except Exception as e:
            self.logger.error(f"Error fetching workflow runs: {e}")
            return []
    
    def get_workflow_status_summary(self) -> Dict:
        """Get summary of workflow statuses."""
        runs = self.get_workflow_runs(20)
        
        if not runs:
            return {
                'total_runs': 0,
                'success_rate': 0,
                'failure_rate': 0,
                'avg_duration': 0,
                'last_run': None
            }
        
        # Calculate metrics
        total_runs = len(runs)
        successful_runs = sum(1 for run in runs if run.conclusion == 'success')
        failed_runs = sum(1 for run in runs if run.conclusion == 'failure')
        
        success_rate = (successful_runs / total_runs) * 100 if total_runs > 0 else 0
        failure_rate = (failed_runs / total_runs) * 100 if total_runs > 0 else 0
        
        # Calculate average duration for completed runs
        completed_runs_with_duration = [
            run for run in runs 
            if run.duration_minutes is not None and run.conclusion
        ]
        avg_duration = (
            sum(run.duration_minutes for run in completed_runs_with_duration) / 
            len(completed_runs_with_duration)
        ) if completed_runs_with_duration else 0
        
        return {
            'total_runs': total_runs,
            'successful_runs': successful_runs,
            'failed_runs': failed_runs,
            'success_rate': round(success_rate, 1),
            'failure_rate': round(failure_rate, 1),
            'avg_duration': round(avg_duration, 1),
            'last_run': runs[0] if runs else None
        }
    
    def check_for_new_failures(self, current_runs: List[WorkflowRun]) -> List[MonitorAlert]:
        """Check for new workflow failures and generate alerts."""
        alerts = []
        
        for run in current_runs:
            run_key = f"{run.name}_{run.id}"
            
            # Check if this is a new run we haven't seen before
            if run_key not in self.last_known_runs:
                self.last_known_runs[run_key] = run
                
                # Generate alert for new failures
                if run.conclusion == 'failure':
                    alert = MonitorAlert(
                        level='error',
                        title='Workflow Failed',
                        message=f"Workflow '{run.name}' failed on commit {run.commit_sha}",
                        timestamp=datetime.now().isoformat(),
                        workflow_run=run
                    )
                    alerts.append(alert)
                    
                # Generate alert for long-running workflows
                elif (run.status == 'in_progress' and 
                      run.duration_minutes and 
                      run.duration_minutes > 30):
                    alert = MonitorAlert(
                        level='warning',
                        title='Long Running Workflow',
                        message=f"Workflow '{run.name}' has been running for {run.duration_minutes:.1f} minutes",
                        timestamp=datetime.now().isoformat(),
                        workflow_run=run
                    )
                    alerts.append(alert)
        
        return alerts
    
    def get_repository_health_score(self) -> Dict:
        """Calculate an overall repository health score based on CI/CD metrics."""
        summary = self.get_workflow_status_summary()
        runs = self.get_workflow_runs(50)
        
        # Health score factors
        factors = {
            'success_rate': 0,
            'frequency': 0,
            'duration': 0,
            'consistency': 0
        }
        
        # Success rate factor (0-40 points)
        factors['success_rate'] = min(40, summary['success_rate'] * 0.4)
        
        # Deployment frequency factor (0-25 points)
        if runs:
            recent_runs = [
                run for run in runs 
                if datetime.fromisoformat(run.created_at.replace('Z', '+00:00')) > 
                   datetime.now().replace(tzinfo=None) - timedelta(days=7)
            ]
            frequency_score = min(25, len(recent_runs) * 5)
            factors['frequency'] = frequency_score
        
        # Duration factor (0-20 points)
        if summary['avg_duration'] > 0:
            # Ideal duration is 5-15 minutes, score decreases as it gets longer
            if summary['avg_duration'] <= 15:
                factors['duration'] = 20
            elif summary['avg_duration'] <= 30:
                factors['duration'] = 15
            elif summary['avg_duration'] <= 60:
                factors['duration'] = 10
            else:
                factors['duration'] = 5
        
        # Consistency factor (0-15 points)
        if len(runs) >= 10:
            # Check for consistent success over time
            recent_10 = runs[:10]
            consistent_successes = sum(1 for run in recent_10 if run.conclusion == 'success')
            factors['consistency'] = (consistent_successes / 10) * 15
        
        total_score = sum(factors.values())
        
        # Determine health level
        if total_score >= 85:
            health_level = 'excellent'
        elif total_score >= 70:
            health_level = 'good'
        elif total_score >= 50:
            health_level = 'fair'
        else:
            health_level = 'poor'
        
        return {
            'score': round(total_score, 1),
            'level': health_level,
            'factors': factors,
            'recommendations': self._get_health_recommendations(factors, summary)
        }
    
    def _get_health_recommendations(self, factors: Dict, summary: Dict) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        if factors['success_rate'] < 30:
            recommendations.append("🔧 Fix failing workflows - success rate is below 75%")
            
        if factors['frequency'] < 15:
            recommendations.append("📈 Increase deployment frequency for better CI/CD")
            
        if factors['duration'] < 15:
            recommendations.append("⚡ Optimize workflow duration - currently over 30 minutes")
            
        if factors['consistency'] < 10:
            recommendations.append("🎯 Improve workflow consistency - too many recent failures")
            
        if summary['failure_rate'] > 20:
            recommendations.append("🚨 Address high failure rate - consider workflow improvements")
        
        if not recommendations:
            recommendations.append("✅ Repository health is good - maintain current practices")
            
        return recommendations
    
    def generate_monitoring_report(self) -> Dict:
        """Generate comprehensive monitoring report."""
        runs = self.get_workflow_runs(20)
        summary = self.get_workflow_status_summary()
        health = self.get_repository_health_score()
        
        # Check for new alerts
        new_alerts = self.check_for_new_failures(runs)
        self.alerts.extend(new_alerts)
        
        # Keep only recent alerts (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.alerts = [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert.timestamp) > cutoff_time
        ]
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'repository': f"{self.owner}/{self.repo}",
            'summary': summary,
            'health': health,
            'recent_runs': [asdict(run) for run in runs[:10]],
            'alerts': [asdict(alert) for alert in self.alerts[-10:]],  # Last 10 alerts
            'monitoring_status': 'active' if self.github_token else 'limited'
        }
        
        return report
    
    def print_monitoring_dashboard(self, report: Dict):
        """Print a comprehensive monitoring dashboard."""
        print("\n" + "="*80)
        print("🚀 GITHUB ACTIONS MONITORING DASHBOARD")
        print("="*80)
        print(f"Repository: {report['repository']}")
        print(f"Last Updated: {report['timestamp']}")
        print(f"Monitoring Status: {report['monitoring_status'].upper()}")
        print()
        
        # Health Score
        health = report.get('health', {})
        health_emoji = {
            'excellent': '🟢',
            'good': '🟡', 
            'fair': '🟠',
            'poor': '🔴'
        }
        health_level = health.get('level', 'unknown')
        health_score = health.get('score', 0)
        print(f"📊 Repository Health: {health_emoji.get(health_level, '⚪')} {health_level.upper()} ({health_score}/100)")
        
        # Summary Stats
        summary = report.get('summary', {})
        if summary:
            print(f"\n📈 Workflow Statistics (Last 20 runs):")
            try:
                success_rate = summary.get('success_rate', 0)
                successful_runs = summary.get('successful_runs', 0)
                total_runs = summary.get('total_runs', 0)
                failure_rate = summary.get('failure_rate', 0)
                failed_runs = summary.get('failed_runs', 0)
                avg_duration = summary.get('avg_duration', 0)
                
                print(f"  ├── Success Rate: {success_rate}% ({successful_runs}/{total_runs})")
                print(f"  ├── Failure Rate: {failure_rate}% ({failed_runs}/{total_runs})")
                print(f"  └── Avg Duration: {avg_duration} minutes")
            except Exception as e:
                print(f"  ❌ Error displaying summary: {e}")
                print(f"  Summary data: {summary}")
        else:
            print(f"\n📈 Workflow Statistics: No data available (GitHub token required)")
        
        # Recent Runs
        recent_runs = report.get('recent_runs', [])
        if recent_runs:
            print(f"\n🔄 Recent Workflow Runs:")
            for run in recent_runs[:5]:
                try:
                    status_emoji = {
                        'success': '✅',
                        'failure': '❌',
                        'in_progress': '🔄',
                        'queued': '⏳'
                    }.get(run.get('conclusion') or run.get('status'), '⚪')
                    
                    duration_str = f" ({run['duration_minutes']:.1f}m)" if run.get('duration_minutes') else ""
                    name = run.get('name', 'Unknown')
                    commit_sha = run.get('commit_sha', 'Unknown')
                    actor = run.get('actor', 'Unknown')
                    print(f"  {status_emoji} {name} - {commit_sha} by {actor}{duration_str}")
                except Exception as e:
                    print(f"  ❌ Error displaying run: {e}")
        
        # Active Alerts
        alerts = report.get('alerts', [])
        if alerts:
            print(f"\n🚨 Recent Alerts:")
            for alert in alerts[-5:]:
                try:
                    alert_emoji = {
                        'info': 'ℹ️',
                        'warning': '⚠️',
                        'error': '❌',
                        'critical': '🚨'
                    }.get(alert.get('level'), '⚪')
                    title = alert.get('title', 'Unknown')
                    message = alert.get('message', 'No message')
                    print(f"  {alert_emoji} {title}: {message}")
                except Exception as e:
                    print(f"  ❌ Error displaying alert: {e}")
        
        # Recommendations
        recommendations = health.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations:")
            for rec in recommendations:
                print(f"  • {rec}")
        
        print("\n" + "="*80)
    
    def monitor_continuous(self, interval: int = 300):
        """Run continuous monitoring with specified interval."""
        self.logger.info(f"Starting continuous monitoring (interval: {interval}s)")
        
        try:
            while True:
                report = self.generate_monitoring_report()
                self.print_monitoring_dashboard(report)
                
                # Save report to file
                report_file = self.repo_path / 'monitoring_report.json'
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2)
                
                # Check for critical alerts
                critical_alerts = [
                    alert for alert in self.alerts 
                    if alert.level == 'critical'
                ]
                
                if critical_alerts:
                    self.logger.critical(f"Found {len(critical_alerts)} critical alerts!")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Enhanced GitHub Actions monitoring with real-time alerts'
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
        help='Output file for monitoring report'
    )
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Run in continuous monitoring mode'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Monitoring interval in seconds (default: 300)'
    )
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Show monitoring dashboard once and exit'
    )
    
    args = parser.parse_args()
    
    try:
        monitor = GitHubActionsMonitor(args.repo_path, args.token)
        
        if args.monitor:
            monitor.monitor_continuous(args.interval)
        elif args.dashboard:
            report = monitor.generate_monitoring_report()
            monitor.print_monitoring_dashboard(report)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"\n📁 Report saved to: {args.output}")
        else:
            # Single run mode
            report = monitor.generate_monitoring_report()
            monitor.print_monitoring_dashboard(report)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"\n📁 Report saved to: {args.output}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())