#!/usr/bin/env python3
"""
Work Session Recorder - Records detailed work sessions for project memory.

This script allows recording detailed work sessions with context preservation,
implementing the session tracking described in docs/PROJECT_MEMORY_SYSTEM.md
"""

import json
import datetime
import argparse
import sys
import uuid
import os
from pathlib import Path
from typing import Dict, List, Any


class WorkSessionRecorder:
    """Records and manages work sessions for project memory."""
    
    def __init__(self, project_root: str = None):
        """Initialize the session recorder."""
        self.project_root = Path(project_root or os.getcwd())
        self.memory_dir = self.project_root / "docs" / "project-memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.memory_dir / "work_sessions.json"
        
    def load_sessions(self) -> List[Dict[str, Any]]:
        """Load existing work sessions."""
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_sessions(self, sessions: List[Dict[str, Any]]) -> None:
        """Save work sessions to file."""
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)
    
    def create_session(self, focus_areas: List[str], description: str = "") -> str:
        """Create a new work session."""
        session_id = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        session = {
            "session_id": session_id,
            "start_time": datetime.datetime.now().isoformat(),
            "end_time": None,
            "duration_hours": None,
            "focus_areas": focus_areas,
            "description": description,
            "deliverables": [],
            "decisions_made": [],
            "challenges_encountered": [],
            "solutions_implemented": [],
            "next_steps": [],
            "context_preserved": {
                "git_branch": self._get_git_branch(),
                "git_hash": self._get_git_hash(),
                "environment": "development"
            },
            "status": "active"
        }
        
        sessions = self.load_sessions()
        sessions.append(session)
        self.save_sessions(sessions)
        
        print(f"✅ Started work session: {session_id}")
        print(f"📝 Focus areas: {', '.join(focus_areas)}")
        
        return session_id
    
    def end_session(self, session_id: str, deliverables: List[str] = None,
                   decisions: List[str] = None, next_steps: List[str] = None) -> None:
        """End a work session with summary."""
        sessions = self.load_sessions()
        
        for session in sessions:
            if session["session_id"] == session_id:
                end_time = datetime.datetime.now()
                start_time = datetime.datetime.fromisoformat(session["start_time"])
                duration = (end_time - start_time).total_seconds() / 3600
                
                session["end_time"] = end_time.isoformat()
                session["duration_hours"] = round(duration, 2)
                session["status"] = "completed"
                
                if deliverables:
                    session["deliverables"].extend([
                        {"type": "deliverable", "item": item, "timestamp": end_time.isoformat()}
                        for item in deliverables
                    ])
                
                if decisions:
                    session["decisions_made"].extend([
                        {"decision": decision, "timestamp": end_time.isoformat()}
                        for decision in decisions
                    ])
                
                if next_steps:
                    session["next_steps"] = next_steps
                
                self.save_sessions(sessions)
                
                print(f"✅ Completed work session: {session_id}")
                print(f"⏱️  Duration: {duration:.2f} hours")
                print(f"📦 Deliverables: {len(session['deliverables'])}")
                
                return
        
        print(f"❌ Session not found: {session_id}")
    
    def add_deliverable(self, session_id: str, deliverable_type: str, 
                       item: str, description: str = "") -> None:
        """Add a deliverable to an active session."""
        sessions = self.load_sessions()
        
        for session in sessions:
            if session["session_id"] == session_id and session["status"] == "active":
                deliverable = {
                    "type": deliverable_type,
                    "item": item,
                    "description": description,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                session["deliverables"].append(deliverable)
                self.save_sessions(sessions)
                
                print(f"📦 Added deliverable to {session_id}: {item}")
                return
        
        print(f"❌ Active session not found: {session_id}")
    
    def add_decision(self, session_id: str, decision: str, 
                    rationale: str = "", impact: str = "") -> None:
        """Add a decision to an active session."""
        sessions = self.load_sessions()
        
        for session in sessions:
            if session["session_id"] == session_id and session["status"] == "active":
                decision_record = {
                    "decision": decision,
                    "rationale": rationale,
                    "impact": impact,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                session["decisions_made"].append(decision_record)
                self.save_sessions(sessions)
                
                print(f"⚖️  Added decision to {session_id}: {decision}")
                return
        
        print(f"❌ Active session not found: {session_id}")
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active work sessions."""
        sessions = self.load_sessions()
        active = [s for s in sessions if s["status"] == "active"]
        
        if active:
            print("🔄 Active Work Sessions:")
            for session in active:
                start_time = datetime.datetime.fromisoformat(session["start_time"])
                elapsed = (datetime.datetime.now() - start_time).total_seconds() / 3600
                
                print(f"  📝 {session['session_id']}")
                print(f"     Started: {start_time.strftime('%Y-%m-%d %H:%M')}")
                print(f"     Elapsed: {elapsed:.1f} hours")
                print(f"     Focus: {', '.join(session['focus_areas'])}")
                print(f"     Deliverables: {len(session['deliverables'])}")
                print()
        else:
            print("📝 No active work sessions")
        
        return active
    
    def generate_session_summary(self, session_id: str) -> str:
        """Generate a comprehensive session summary."""
        sessions = self.load_sessions()
        
        for session in sessions:
            if session["session_id"] == session_id:
                start_time = datetime.datetime.fromisoformat(session["start_time"])
                
                summary = f"""# Work Session Summary: {session_id}

**Start Time:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}
"""
                
                if session["end_time"]:
                    end_time = datetime.datetime.fromisoformat(session["end_time"])
                    summary += f"**End Time:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    summary += f"**Duration:** {session['duration_hours']} hours\n"
                
                summary += f"**Status:** {session['status']}\n"
                summary += f"**Focus Areas:** {', '.join(session['focus_areas'])}\n\n"
                
                if session["description"]:
                    summary += f"**Description:** {session['description']}\n\n"
                
                if session["deliverables"]:
                    summary += "## 📦 Deliverables\n\n"
                    for deliverable in session["deliverables"]:
                        summary += f"- **{deliverable['type']}**: {deliverable['item']}\n"
                        if deliverable.get('description'):
                            summary += f"  - {deliverable['description']}\n"
                    summary += "\n"
                
                if session["decisions_made"]:
                    summary += "## ⚖️ Decisions Made\n\n"
                    for decision in session["decisions_made"]:
                        summary += f"- **Decision**: {decision['decision']}\n"
                        if decision.get('rationale'):
                            summary += f"  - **Rationale**: {decision['rationale']}\n"
                        if decision.get('impact'):
                            summary += f"  - **Impact**: {decision['impact']}\n"
                    summary += "\n"
                
                if session["next_steps"]:
                    summary += "## 🎯 Next Steps\n\n"
                    for step in session["next_steps"]:
                        summary += f"- {step}\n"
                    summary += "\n"
                
                return summary
        
        return f"Session not found: {session_id}"
    
    def record_from_file(self, file_path: str) -> None:
        """Record a session from a JSON file (used by git hooks)."""
        try:
            with open(file_path, 'r') as f:
                session_data = json.load(f)
            
            # Convert git commit data to session format
            if session_data.get("type") == "git_commit":
                session = {
                    "session_id": session_data["session_id"],
                    "start_time": session_data["session_start"],
                    "end_time": session_data["session_start"],  # Commits are instantaneous
                    "duration_hours": 0.0,
                    "focus_areas": ["git_commit"],
                    "description": f"Git commit: {session_data['commit_message']}",
                    "deliverables": [
                        {
                            "type": "git_commit",
                            "item": f"Commit {session_data['commit_hash'][:8]}",
                            "description": session_data['commit_message'],
                            "timestamp": session_data['session_start']
                        }
                    ],
                    "decisions_made": [],
                    "challenges_encountered": [],
                    "solutions_implemented": [],
                    "next_steps": [],
                    "context_preserved": session_data["context_preserved"],
                    "status": "completed",
                    "git_context": {
                        "commit_hash": session_data["commit_hash"],
                        "commit_author": session_data["commit_author"],
                        "files_modified": session_data["files_modified"]
                    }
                }
                
                sessions = self.load_sessions()
                sessions.append(session)
                self.save_sessions(sessions)
                
                print(f"📝 Recorded git commit session: {session['session_id']}")
            
        except Exception as e:
            print(f"❌ Error recording session from file: {e}")
    
    def _get_git_branch(self) -> str:
        """Get current git branch."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def _get_git_hash(self) -> str:
        """Get current git commit hash."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"


def main():
    """Main entry point for the session recorder."""
    parser = argparse.ArgumentParser(description="MetaFunction Work Session Recorder")
    parser.add_argument("--project-root", help="Project root directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start session
    start_parser = subparsers.add_parser("start", help="Start a new work session")
    start_parser.add_argument("--focus", nargs="+", required=True, help="Focus areas for the session")
    start_parser.add_argument("--description", help="Session description")
    
    # End session
    end_parser = subparsers.add_parser("end", help="End a work session")
    end_parser.add_argument("--session-id", required=True, help="Session ID to end")
    end_parser.add_argument("--deliverables", nargs="*", help="Deliverables completed")
    end_parser.add_argument("--decisions", nargs="*", help="Decisions made")
    end_parser.add_argument("--next-steps", nargs="*", help="Next steps identified")
    
    # Add deliverable
    add_parser = subparsers.add_parser("add", help="Add deliverable to active session")
    add_parser.add_argument("--session-id", required=True, help="Session ID")
    add_parser.add_argument("--type", required=True, help="Deliverable type")
    add_parser.add_argument("--item", required=True, help="Deliverable item")
    add_parser.add_argument("--description", help="Deliverable description")
    
    # Add decision
    decide_parser = subparsers.add_parser("decide", help="Add decision to active session")
    decide_parser.add_argument("--session-id", required=True, help="Session ID")
    decide_parser.add_argument("--decision", required=True, help="Decision made")
    decide_parser.add_argument("--rationale", help="Decision rationale")
    decide_parser.add_argument("--impact", help="Decision impact")
    
    # List sessions
    list_parser = subparsers.add_parser("list", help="List active sessions")
    
    # Session summary
    summary_parser = subparsers.add_parser("summary", help="Generate session summary")
    summary_parser.add_argument("--session-id", required=True, help="Session ID")
    
    # Record from file (for git hooks)
    file_parser = subparsers.add_parser("from-file", help="Record session from file")
    file_parser.add_argument("--file", required=True, help="JSON file path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    recorder = WorkSessionRecorder(args.project_root)
    
    if args.command == "start":
        session_id = recorder.create_session(args.focus, args.description or "")
        print(f"\n💡 To end this session, run:")
        print(f"   python scripts/record_session.py end --session-id {session_id}")
        
    elif args.command == "end":
        recorder.end_session(
            args.session_id,
            args.deliverables,
            args.decisions,
            args.next_steps
        )
        
    elif args.command == "add":
        recorder.add_deliverable(
            args.session_id,
            args.type,
            args.item,
            args.description or ""
        )
        
    elif args.command == "decide":
        recorder.add_decision(
            args.session_id,
            args.decision,
            args.rationale or "",
            args.impact or ""
        )
        
    elif args.command == "list":
        recorder.list_active_sessions()
        
    elif args.command == "summary":
        summary = recorder.generate_session_summary(args.session_id)
        print(summary)
        
    elif args.command == "from-file":
        recorder.record_from_file(args.file)


if __name__ == "__main__":
    main()
