#!/usr/bin/env python3
"""
MetaFunction CI/CD Success Rate Monitoring and Analysis
Real-time monitoring of GitHub Actions workflows with enhanced reporting
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class EnhancedCIMonitor:
    """Enhanced CI/CD monitoring with detailed analytics"""
    
    def __init__(self, repo_path: Path = Path.cwd()):
        self.repo_path = repo_path
        self.github_token = self._get_github_token()
        self.repo_full_name = self._get_repo_name()
        
    def _get_github_token(self) -> Optional[str]:
        """Extract GitHub token from git remotes"""
        try:
            # Get remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            remote_url = result.stdout.strip()
            
            # Extract token from https://token@github.com/... format
            if "https://" in remote_url and "@github.com" in remote_url:
                # Extract token from URL
                token_part = remote_url.split("https://")[1].split("@github.com")[0]
                if token_part and len(token_part) > 10:  # Basic validation
                    return token_part
                    
        except Exception as e:
            print(f"Warning: Could not extract GitHub token: {e}")
            
        return None
        
    def _get_repo_name(self) -> Optional[str]:
        """Get repository name from git remotes"""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            remote_url = result.stdout.strip()
            
            # Extract repo name from various URL formats
            if "github.com/" in remote_url:
                repo_part = remote_url.split("github.com/")[1]
                # Remove .git suffix if present
                if repo_part.endswith('.git'):
                    repo_part = repo_part[:-4]
                return repo_part
                
        except Exception:
            pass
            
        return None
        
    def get_workflow_runs(self, limit: int = 50) -> List[Dict]:
        """Get recent workflow runs from GitHub API"""
        if not self.github_token or not self.repo_full_name:
            print("❌ GitHub token or repository name not available")
            return []
            
        try:
            import requests
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            url = f'https://api.github.com/repos/{self.repo_full_name}/actions/runs'
            params = {'per_page': limit}
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                return response.json()['workflow_runs']
            else:
                print(f"❌ GitHub API error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching workflow runs: {e}")
            return []
            
    def analyze_success_rate(self, runs: List[Dict]) -> Dict:
        """Analyze workflow success rates with detailed breakdown"""
        if not runs:
            return {
                'total_runs': 0,
                'success_rate': 0.0,
                'failure_rate': 0.0,
                'success_count': 0,
                'failure_count': 0,
                'avg_duration': 0.0,
                'status_breakdown': {},
                'recent_trend': 'unknown'
            }
            
        total_runs = len(runs)
        success_count = sum(1 for run in runs if run['conclusion'] == 'success')
        failure_count = sum(1 for run in runs if run['conclusion'] in ['failure', 'cancelled', 'timed_out'])
        
        # Calculate durations (in minutes)
        durations = []
        for run in runs:
            if run.get('created_at') and run.get('updated_at'):
                try:
                    created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
                    updated = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
                    duration = (updated - created).total_seconds() / 60
                    if duration > 0:
                        durations.append(duration)
                except:
                    pass
                    
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        # Status breakdown
        status_breakdown = {}
        for run in runs:
            status = run.get('conclusion', 'unknown')
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
            
        # Recent trend analysis (last 10 vs previous 10)
        recent_trend = 'stable'
        if total_runs >= 20:
            recent_success_rate = sum(1 for run in runs[:10] if run['conclusion'] == 'success') / 10
            previous_success_rate = sum(1 for run in runs[10:20] if run['conclusion'] == 'success') / 10
            
            if recent_success_rate > previous_success_rate + 0.1:
                recent_trend = 'improving'
            elif recent_success_rate < previous_success_rate - 0.1:
                recent_trend = 'declining'
                
        return {
            'total_runs': total_runs,
            'success_rate': (success_count / total_runs) * 100,
            'failure_rate': (failure_count / total_runs) * 100,
            'success_count': success_count,
            'failure_count': failure_count,
            'avg_duration': avg_duration,
            'status_breakdown': status_breakdown,
            'recent_trend': recent_trend
        }
        
    def calculate_health_score(self, analysis: Dict) -> Tuple[float, str]:
        """Calculate overall health score (0-100) with rating"""
        if analysis['total_runs'] == 0:
            return 0.0, "NO DATA"
            
        # Base score from success rate
        base_score = analysis['success_rate']
        
        # Adjustments
        adjustments = 0
        
        # Trend adjustment
        if analysis['recent_trend'] == 'improving':
            adjustments += 5
        elif analysis['recent_trend'] == 'declining':
            adjustments -= 10
            
        # Duration penalty (if avg > 5 minutes)
        if analysis['avg_duration'] > 5:
            adjustments -= min(10, (analysis['avg_duration'] - 5) * 2)
            
        # Volume bonus (more data = more reliable)
        if analysis['total_runs'] >= 50:
            adjustments += 5
        elif analysis['total_runs'] >= 20:
            adjustments += 2
            
        # Final score
        health_score = max(0, min(100, base_score + adjustments))
        
        # Rating
        if health_score >= 95:
            rating = "EXCELLENT"
        elif health_score >= 85:
            rating = "GOOD"
        elif health_score >= 70:
            rating = "FAIR"
        elif health_score >= 50:
            rating = "POOR"
        else:
            rating = "CRITICAL"
            
        return health_score, rating
        
    def generate_report(self) -> str:
        """Generate comprehensive monitoring report"""
        print("🔍 Fetching workflow data...")
        runs = self.get_workflow_runs(50)
        
        print("📊 Analyzing success patterns...")
        analysis = self.analyze_success_rate(runs)
        
        print("🏥 Calculating health metrics...")
        health_score, rating = self.calculate_health_score(analysis)
        
        # Build report
        report_lines = [
            "=" * 80,
            "🚀 METAFUNCTION CI/CD ENHANCED MONITORING DASHBOARD",
            "=" * 80,
            f"Repository: {self.repo_full_name or 'Unknown'}",
            f"Last Updated: {datetime.now(timezone.utc).isoformat()}",
            f"Monitoring Status: {'ACTIVE' if self.github_token else 'LIMITED'}",
            "",
            f"📊 Repository Health: {self._get_health_emoji(rating)} {rating} ({health_score:.1f}/100)",
            "",
        ]
        
        if analysis['total_runs'] > 0:
            report_lines.extend([
                f"📈 Workflow Statistics (Last {analysis['total_runs']} runs):",
                f"  ├── Success Rate: {analysis['success_rate']:.1f}% ({analysis['success_count']}/{analysis['total_runs']})",
                f"  ├── Failure Rate: {analysis['failure_rate']:.1f}% ({analysis['failure_count']}/{analysis['total_runs']})",
                f"  ├── Avg Duration: {analysis['avg_duration']:.1f} minutes",
                f"  └── Recent Trend: {self._get_trend_emoji(analysis['recent_trend'])} {analysis['recent_trend'].upper()}",
                "",
            ])
            
            # Status breakdown
            if analysis['status_breakdown']:
                report_lines.append("📋 Status Breakdown:")
                for status, count in analysis['status_breakdown'].items():
                    emoji = self._get_status_emoji(status)
                    percentage = (count / analysis['total_runs']) * 100
                    report_lines.append(f"  ├── {emoji} {status.title()}: {count} ({percentage:.1f}%)")
                report_lines.append("")
                
            # Recent runs
            if runs[:5]:
                report_lines.append("🔄 Recent Workflow Runs:")
                for run in runs[:5]:
                    emoji = self._get_status_emoji(run.get('conclusion', 'unknown'))
                    duration = self._calculate_run_duration(run)
                    actor = run.get('actor', {}).get('login', 'unknown')
                    head_sha = run.get('head_sha', '')[:8]
                    report_lines.append(
                        f"  {emoji} {run.get('display_title', 'Unknown')} - "
                        f"#{run.get('run_number', 'N/A')} - {head_sha} by {actor} ({duration})"
                    )
                report_lines.append("")
                
        # Recommendations
        recommendations = self._generate_recommendations(analysis, health_score)
        if recommendations:
            report_lines.append("💡 Recommendations:")
            for rec in recommendations:
                report_lines.append(f"  {rec}")
            report_lines.append("")
            
        report_lines.append("=" * 80)
        
        return "\\n".join(report_lines)
        
    def _get_health_emoji(self, rating: str) -> str:
        """Get emoji for health rating"""
        emojis = {
            "EXCELLENT": "🟢",
            "GOOD": "🟡",
            "FAIR": "🟠",
            "POOR": "🔴",
            "CRITICAL": "⚫",
            "NO DATA": "⚪"
        }
        return emojis.get(rating, "❓")
        
    def _get_trend_emoji(self, trend: str) -> str:
        """Get emoji for trend"""
        emojis = {
            "improving": "📈",
            "declining": "📉",
            "stable": "➡️",
            "unknown": "❓"
        }
        return emojis.get(trend, "❓")
        
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for workflow status"""
        emojis = {
            "success": "✅",
            "failure": "❌",
            "cancelled": "⏹️",
            "timed_out": "⏰",
            "in_progress": "🔄",
            "queued": "⏳",
            "unknown": "❓"
        }
        return emojis.get(status, "❓")
        
    def _calculate_run_duration(self, run: Dict) -> str:
        """Calculate and format run duration"""
        try:
            if run.get('created_at') and run.get('updated_at'):
                created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
                updated = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
                duration = (updated - created).total_seconds() / 60
                return f"{duration:.1f}m"
        except:
            pass
        return "N/A"
        
    def _generate_recommendations(self, analysis: Dict, health_score: float) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if health_score >= 95:
            recommendations.append("• ✅ Repository health is excellent - maintain current practices")
        elif health_score >= 85:
            recommendations.append("• ✅ Repository health is good - minor optimizations possible")
        elif health_score < 70:
            recommendations.append("• ⚠️ Repository health needs attention")
            
        if analysis['failure_rate'] > 20:
            recommendations.append("• 🔧 High failure rate detected - review recent changes")
            
        if analysis['avg_duration'] > 10:
            recommendations.append("• ⚡ Consider optimizing workflow performance")
            
        if analysis['recent_trend'] == 'declining':
            recommendations.append("• 📉 Recent declining trend - investigate latest commits")
            
        if analysis['total_runs'] < 20:
            recommendations.append("• 📊 Limited data available - continue monitoring")
            
        return recommendations

def main():
    """Main execution function"""
    try:
        monitor = EnhancedCIMonitor()
        report = monitor.generate_report()
        print(report)
        
        # Save report to file
        report_file = Path("ci_monitoring_report.txt")
        with open(report_file, 'w') as f:
            f.write(report.replace('\\n', '\\n'))
        print(f"\\n📄 Report saved to: {report_file}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
