#!/usr/bin/env python3
"""
Project Memory Reminder System - Daily reminders and health checks.

This script provides automated reminders and health checks to ensure
project memory is maintained and no work is forgotten.
"""

import datetime
import json
import os
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Any


class ProjectReminderSystem:
    """Manages daily reminders and project health monitoring."""
    
    def __init__(self, project_root: str = None):
        """Initialize the reminder system."""
        self.project_root = Path(project_root or os.getcwd())
        self.memory_dir = self.project_root / "docs" / "project-memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.reminders_file = self.memory_dir / "reminder_log.json"
        
    def check_project_health(self) -> Dict[str, Any]:
        """Perform comprehensive project health check."""
        health_status = {
            "timestamp": datetime.datetime.now().isoformat(),
            "overall_health": "healthy",
            "issues": [],
            "warnings": [],
            "recommendations": [],
            "metrics": {}
        }
        
        # Check for stale work sessions
        sessions_file = self.memory_dir / "work_sessions.json"
        if sessions_file.exists():
            try:
                with open(sessions_file, 'r') as f:
                    sessions = json.load(f)
                
                active_sessions = [s for s in sessions if s.get("status") == "active"]
                if active_sessions:
                    health_status["warnings"].append(
                        f"Found {len(active_sessions)} unclosed work sessions"
                    )
                
                # Check for sessions without deliverables
                empty_sessions = [
                    s for s in sessions[-10:] 
                    if s.get("status") == "completed" and not s.get("deliverables")
                ]
                if empty_sessions:
                    health_status["recommendations"].append(
                        "Consider documenting deliverables for completed sessions"
                    )
                
                health_status["metrics"]["total_sessions"] = len(sessions)
                health_status["metrics"]["active_sessions"] = len(active_sessions)
                
            except Exception as e:
                health_status["issues"].append(f"Error reading work sessions: {e}")
        
        # Check Git status
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                changed_files = [line for line in result.stdout.strip().split('\n') if line.strip()]
                health_status["metrics"]["uncommitted_changes"] = len(changed_files)
                
                if len(changed_files) > 10:
                    health_status["warnings"].append(
                        f"Many uncommitted changes: {len(changed_files)} files"
                    )
                elif len(changed_files) > 0:
                    health_status["recommendations"].append(
                        f"Consider committing {len(changed_files)} changed files"
                    )
            
            # Check for unpushed commits
            result = subprocess.run(
                ["git", "log", "@{u}..", "--oneline"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                unpushed = [line for line in result.stdout.strip().split('\n') if line.strip()]
                health_status["metrics"]["unpushed_commits"] = len(unpushed)
                
                if len(unpushed) > 5:
                    health_status["warnings"].append(
                        f"Many unpushed commits: {len(unpushed)}"
                    )
                elif len(unpushed) > 0:
                    health_status["recommendations"].append(
                        f"Consider pushing {len(unpushed)} commits"
                    )
        
        except Exception as e:
            health_status["issues"].append(f"Git status check failed: {e}")
        
        # Check documentation freshness
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            status_file = docs_dir / "PROJECT_STATUS.md"
            if status_file.exists():
                last_modified = datetime.datetime.fromtimestamp(status_file.stat().st_mtime)
                days_old = (datetime.datetime.now() - last_modified).days
                
                health_status["metrics"]["status_report_age_days"] = days_old
                
                if days_old > 7:
                    health_status["warnings"].append(
                        f"Project status report is {days_old} days old"
                    )
                elif days_old > 3:
                    health_status["recommendations"].append(
                        "Consider updating project status report"
                    )
        
        # Set overall health based on issues
        if health_status["issues"]:
            health_status["overall_health"] = "unhealthy"
        elif health_status["warnings"]:
            health_status["overall_health"] = "degraded"
        
        return health_status
    
    def generate_daily_summary(self) -> str:
        """Generate daily project summary."""
        today = datetime.datetime.now()
        health = self.check_project_health()
        
        summary = f"""# 🧬 MetaFunction Daily Summary - {today.strftime('%Y-%m-%d')}

## 🏥 Project Health: {health['overall_health'].upper()}

### 📊 Metrics
"""
        
        for metric, value in health["metrics"].items():
            summary += f"- **{metric.replace('_', ' ').title()}**: {value}\n"
        
        if health["issues"]:
            summary += "\n### ❌ Issues Requiring Attention\n"
            for issue in health["issues"]:
                summary += f"- {issue}\n"
        
        if health["warnings"]:
            summary += "\n### ⚠️ Warnings\n"
            for warning in health["warnings"]:
                summary += f"- {warning}\n"
        
        if health["recommendations"]:
            summary += "\n### 💡 Recommendations\n"
            for rec in health["recommendations"]:
                summary += f"- {rec}\n"
        
        # Add recent activity
        sessions_file = self.memory_dir / "work_sessions.json"
        if sessions_file.exists():
            try:
                with open(sessions_file, 'r') as f:
                    sessions = json.load(f)
                
                # Recent sessions (last 3 days)
                cutoff = today - datetime.timedelta(days=3)
                recent_sessions = []
                
                for session in sessions:
                    if session.get("start_time"):
                        session_date = datetime.datetime.fromisoformat(session["start_time"])
                        if session_date >= cutoff:
                            recent_sessions.append(session)
                
                if recent_sessions:
                    summary += f"\n### 📝 Recent Activity ({len(recent_sessions)} sessions)\n"
                    for session in recent_sessions[-5:]:  # Last 5 sessions
                        start_time = datetime.datetime.fromisoformat(session["start_time"])
                        focus = ", ".join(session.get("focus_areas", []))
                        deliverables = len(session.get("deliverables", []))
                        
                        summary += f"- **{start_time.strftime('%m-%d %H:%M')}**: {focus} ({deliverables} deliverables)\n"
            
            except Exception as e:
                summary += f"\n### ⚠️ Could not load recent activity: {e}\n"
        
        # Add next actions
        summary += f"""
### 🎯 Recommended Actions for Today

1. **Health Check**: Address any issues or warnings listed above
2. **Session Management**: Close any open work sessions
3. **Documentation**: Update project documentation if needed
4. **Git Hygiene**: Commit pending changes and push to remotes
5. **Memory Update**: Run project memory analysis if significant changes made

### 🤖 Automation Status

- **Project Memory**: {'✅ Active' if (self.memory_dir / 'current_state.json').exists() else '❌ Not initialized'}
- **Git Hooks**: {'✅ Installed' if (self.project_root / '.git' / 'hooks' / 'post-commit').exists() else '❌ Not installed'}
- **Health Monitoring**: ✅ Active (this report)

---
*Generated automatically by MetaFunction Project Memory System*
*Next reminder: {(today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')}*
"""
        
        return summary
    
    def log_reminder(self, reminder_type: str, content: str) -> None:
        """Log a reminder to the reminder log."""
        reminder_log = []
        
        if self.reminders_file.exists():
            try:
                with open(self.reminders_file, 'r') as f:
                    reminder_log = json.load(f)
            except:
                reminder_log = []
        
        reminder_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": reminder_type,
            "content": content,
            "acknowledged": False
        }
        
        reminder_log.append(reminder_entry)
        
        # Keep only last 100 reminders
        if len(reminder_log) > 100:
            reminder_log = reminder_log[-100:]
        
        with open(self.reminders_file, 'w') as f:
            json.dump(reminder_log, f, indent=2)
    
    def send_email_reminder(self, summary: str, recipient_email: str) -> bool:
        """Send email reminder (if configured)."""
        try:
            # This would require SMTP configuration
            # For now, just save to file
            email_file = self.memory_dir / f"daily_summary_{datetime.datetime.now().strftime('%Y%m%d')}.md"
            with open(email_file, 'w') as f:
                f.write(summary)
            
            print(f"📧 Daily summary saved to: {email_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email reminder: {e}")
            return False
    
    def run_daily_check(self, email: str = None) -> None:
        """Run the daily project health check and reminder."""
        print("🌅 Running daily project health check...")
        
        # Generate summary
        summary = self.generate_daily_summary()
        
        # Log the reminder
        self.log_reminder("daily_check", "Daily health check completed")
        
        # Save summary
        summary_file = self.memory_dir / f"daily_summary_{datetime.datetime.now().strftime('%Y%m%d')}.md"
        with open(summary_file, 'w') as f:
            f.write(summary)
        
        print(f"📄 Daily summary saved to: {summary_file}")
        
        # Send email if configured
        if email:
            self.send_email_reminder(summary, email)
        
        # Display summary
        print("\n" + "="*60)
        print(summary)
        print("="*60)
        
        # Check for critical issues
        health = self.check_project_health()
        if health["overall_health"] == "unhealthy":
            print("\n🚨 CRITICAL: Project health is UNHEALTHY!")
            print("   Immediate attention required for the following issues:")
            for issue in health["issues"]:
                print(f"   - {issue}")
        
        print("\n✅ Daily health check complete!")


def main():
    """Main entry point for the reminder system."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MetaFunction Project Reminder System")
    parser.add_argument("--project-root", help="Project root directory")
    parser.add_argument("--email", help="Email address for reminders")
    parser.add_argument("--action", choices=["daily", "health", "summary"], 
                       default="daily", help="Action to perform")
    
    args = parser.parse_args()
    
    reminder_system = ProjectReminderSystem(args.project_root)
    
    if args.action == "daily":
        reminder_system.run_daily_check(args.email)
    elif args.action == "health":
        health = reminder_system.check_project_health()
        print(json.dumps(health, indent=2))
    elif args.action == "summary":
        summary = reminder_system.generate_daily_summary()
        print(summary)


if __name__ == "__main__":
    main()
