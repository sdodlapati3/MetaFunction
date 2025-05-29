#!/usr/bin/env python3
"""
Project Memory Tracker - Automated system to track and preserve project state.

This script implements the Project Memory System documented in docs/PROJECT_MEMORY_SYSTEM.md
to ensure no work is forgotten and provides comprehensive project state awareness.
"""

import os
import json
import yaml
import subprocess
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class ProjectComponent:
    """Represents a component of the project."""
    name: str
    status: str  # 'implemented', 'documented', 'pending', 'deprecated'
    location: str
    description: str
    last_modified: str
    dependencies: List[str] = None
    implementation_notes: str = ""


@dataclass
class WorkSession:
    """Represents a work session with deliverables."""
    session_id: str
    start_time: str
    end_time: str
    duration_hours: float
    focus_areas: List[str]
    deliverables: List[Dict[str, str]]
    decisions_made: List[Dict[str, str]]
    next_steps: List[str]
    context_preserved: Dict[str, Any]


class ProjectMemoryTracker:
    """Automated project memory and state tracking system."""
    
    def __init__(self, project_root: str = None):
        """Initialize the memory tracker."""
        self.project_root = Path(project_root or os.getcwd())
        self.memory_dir = self.project_root / "docs" / "project-memory"
        self.memory_dir.mkdir(exist_ok=True)
        
        # Memory files
        self.state_file = self.memory_dir / "current_state.json"
        self.history_file = self.memory_dir / "work_history.json"
        self.components_file = self.memory_dir / "components_inventory.json"
        self.status_file = self.project_root / "docs" / "PROJECT_STATUS.md"
        
    def scan_project_structure(self) -> Dict[str, Any]:
        """Scan and analyze current project structure."""
        structure = {
            "directories": [],
            "key_files": [],
            "documentation_files": [],
            "code_files": [],
            "config_files": [],
            "test_files": []
        }
        
        # Key patterns to identify different file types
        doc_patterns = [".md", ".rst", ".txt"]
        code_patterns = [".py", ".js", ".ts", ".java", ".cpp", ".c"]
        config_patterns = [".yml", ".yaml", ".json", ".toml", ".ini", ".env"]
        test_patterns = ["test_", "_test.py", "spec_", ".spec."]
        
        for root, dirs, files in os.walk(self.project_root):
            rel_root = os.path.relpath(root, self.project_root)
            
            # Skip hidden directories and virtual environments
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.venv', 'venv']]
            
            if rel_root != '.':
                structure["directories"].append(rel_root)
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(rel_root, file)
                file_info = {
                    "path": file_path,
                    "size": os.path.getsize(os.path.join(root, file)),
                    "modified": datetime.datetime.fromtimestamp(
                        os.path.getmtime(os.path.join(root, file))
                    ).isoformat()
                }
                
                # Categorize files
                if any(file.endswith(ext) for ext in doc_patterns):
                    structure["documentation_files"].append(file_info)
                elif any(pattern in file for pattern in test_patterns):
                    structure["test_files"].append(file_info)
                elif any(file.endswith(ext) for ext in code_patterns):
                    structure["code_files"].append(file_info)
                elif any(file.endswith(ext) for ext in config_patterns):
                    structure["config_files"].append(file_info)
                elif file in ["README.md", "CHANGELOG.md", "requirements.txt", "Dockerfile", "Makefile"]:
                    structure["key_files"].append(file_info)
        
        return structure
    
    def analyze_documentation(self) -> List[ProjectComponent]:
        """Analyze documentation to identify completed features and enhancements."""
        components = []
        docs_dir = self.project_root / "docs"
        
        if not docs_dir.exists():
            return components
        
        for doc_file in docs_dir.glob("*.md"):
            try:
                content = doc_file.read_text(encoding='utf-8')
                
                # Determine component status based on content
                status = "documented"
                if "implemented" in content.lower() or "✅" in content:
                    status = "implemented"
                elif "pending" in content.lower() or "🔄" in content:
                    status = "pending"
                elif "deprecated" in content.lower() or "❌" in content:
                    status = "deprecated"
                
                # Extract description from first few lines
                lines = content.split('\n')
                description = ""
                for line in lines[1:10]:  # Skip title, look in first 10 lines
                    if line.strip() and not line.startswith('#'):
                        description = line.strip()
                        break
                
                component = ProjectComponent(
                    name=doc_file.stem.replace('_', ' ').title(),
                    status=status,
                    location=str(doc_file.relative_to(self.project_root)),
                    description=description,
                    last_modified=datetime.datetime.fromtimestamp(
                        doc_file.stat().st_mtime
                    ).isoformat()
                )
                components.append(component)
                
            except Exception as e:
                print(f"Error analyzing {doc_file}: {e}")
        
        return components
    
    def analyze_code_features(self) -> List[ProjectComponent]:
        """Analyze codebase to identify implemented features."""
        components = []
        
        # Key directories to analyze
        key_dirs = ["app", "services", "clients", "routes", "utils", "resolvers"]
        
        for dir_name in key_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                continue
                
            for py_file in dir_path.rglob("*.py"):
                if py_file.name.startswith('__') or 'test' in py_file.name:
                    continue
                    
                try:
                    content = py_file.read_text(encoding='utf-8')
                    
                    # Extract classes and major functions
                    classes = []
                    functions = []
                    
                    for line in content.split('\n'):
                        if line.strip().startswith('class '):
                            classes.append(line.strip().split()[1].split('(')[0])
                        elif line.strip().startswith('def ') and not line.strip().startswith('def _'):
                            functions.append(line.strip().split()[1].split('(')[0])
                    
                    if classes or functions:
                        component = ProjectComponent(
                            name=f"Module: {py_file.stem}",
                            status="implemented",
                            location=str(py_file.relative_to(self.project_root)),
                            description=f"Classes: {', '.join(classes[:3])}. Functions: {', '.join(functions[:3])}",
                            last_modified=datetime.datetime.fromtimestamp(
                                py_file.stat().st_mtime
                            ).isoformat(),
                            implementation_notes=f"{len(classes)} classes, {len(functions)} functions"
                        )
                        components.append(component)
                        
                except Exception as e:
                    print(f"Error analyzing {py_file}: {e}")
        
        return components
    
    def get_git_context(self) -> Dict[str, Any]:
        """Get Git repository context and recent changes."""
        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            
            # Get recent commits
            log_result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            recent_commits = log_result.stdout.strip().split('\n') if log_result.returncode == 0 else []
            
            # Get status
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            changed_files = status_result.stdout.strip().split('\n') if status_result.returncode == 0 else []
            
            # Get remotes
            remote_result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            remotes = remote_result.stdout.strip().split('\n') if remote_result.returncode == 0 else []
            
            return {
                "current_branch": current_branch,
                "recent_commits": recent_commits,
                "changed_files": [f for f in changed_files if f.strip()],
                "remotes": remotes,
                "last_updated": datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Git analysis failed: {e}"}
    
    def generate_current_state(self) -> Dict[str, Any]:
        """Generate comprehensive current project state."""
        print("🔍 Analyzing project structure...")
        structure = self.scan_project_structure()
        
        print("📚 Analyzing documentation...")
        doc_components = self.analyze_documentation()
        
        print("💻 Analyzing code features...")
        code_components = self.analyze_code_features()
        
        print("🔄 Analyzing Git context...")
        git_context = self.get_git_context()
        
        state = {
            "generated_at": datetime.datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "structure": structure,
            "components": {
                "documentation": [asdict(comp) for comp in doc_components],
                "code_modules": [asdict(comp) for comp in code_components]
            },
            "git_context": git_context,
            "statistics": {
                "total_documentation_files": len(structure["documentation_files"]),
                "total_code_files": len(structure["code_files"]),
                "total_test_files": len(structure["test_files"]),
                "total_components": len(doc_components) + len(code_components)
            },
            "health_check": self.perform_health_check()
        }
        
        return state
    
    def perform_health_check(self) -> Dict[str, Any]:
        """Perform project health assessment."""
        health = {
            "overall_status": "healthy",
            "issues": [],
            "recommendations": []
        }
        
        # Check for key files
        key_files = ["README.md", "requirements.txt", "app.py"]
        for file in key_files:
            if not (self.project_root / file).exists():
                health["issues"].append(f"Missing key file: {file}")
        
        # Check documentation coverage
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            doc_count = len(list(docs_dir.glob("*.md")))
            if doc_count < 5:
                health["recommendations"].append("Consider adding more documentation")
        else:
            health["issues"].append("No docs directory found")
        
        # Set overall status
        if health["issues"]:
            health["overall_status"] = "degraded" if len(health["issues"]) < 3 else "unhealthy"
        
        return health
    
    def save_state(self, state: Dict[str, Any]) -> None:
        """Save current state to memory files."""
        # Save full state
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        # Save components inventory
        components_data = {
            "last_updated": state["generated_at"],
            "documentation_components": state["components"]["documentation"],
            "code_components": state["components"]["code_modules"]
        }
        
        with open(self.components_file, 'w') as f:
            json.dump(components_data, f, indent=2)
        
        print(f"💾 Project state saved to {self.state_file}")
        print(f"📋 Components inventory saved to {self.components_file}")
    
    def generate_status_report(self, state: Dict[str, Any]) -> str:
        """Generate comprehensive project status report."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# 🧬 MetaFunction Project Status Report

**Generated:** {timestamp}  
**Project Root:** {state['project_root']}  
**Overall Health:** {state['health_check']['overall_status'].upper()}

## 📊 Project Statistics

| Metric | Count |
|--------|-------|
| Documentation Files | {state['statistics']['total_documentation_files']} |
| Code Files | {state['statistics']['total_code_files']} |
| Test Files | {state['statistics']['total_test_files']} |
| Total Components | {state['statistics']['total_components']} |
| Directories | {len(state['structure']['directories'])} |

## 📚 Documentation Components

| Component | Status | Location | Last Modified |
|-----------|--------|----------|---------------|
"""
        
        for comp in state['components']['documentation']:
            report += f"| {comp['name']} | {comp['status']} | {comp['location']} | {comp['last_modified'][:10]} |\n"
        
        report += f"""
## 💻 Code Modules

| Module | Status | Location | Features |
|--------|--------|----------|----------|
"""
        
        for comp in state['components']['code_modules'][:10]:  # Limit to first 10
            report += f"| {comp['name']} | {comp['status']} | {comp['location']} | {comp['implementation_notes']} |\n"
        
        report += f"""
## 🔄 Git Context

**Current Branch:** {state['git_context'].get('current_branch', 'unknown')}  
**Recent Changes:** {len(state['git_context'].get('changed_files', []))} files modified  
**Remotes:** {len(state['git_context'].get('remotes', []))} repositories configured

### Recent Commits
"""
        
        for commit in state['git_context'].get('recent_commits', [])[:5]:
            report += f"- {commit}\n"
        
        if state['health_check']['issues']:
            report += "\n## ⚠️ Issues\n"
            for issue in state['health_check']['issues']:
                report += f"- {issue}\n"
        
        if state['health_check']['recommendations']:
            report += "\n## 💡 Recommendations\n"
            for rec in state['health_check']['recommendations']:
                report += f"- {rec}\n"
        
        report += f"""
## 🎯 Next Steps

Based on the current project state, recommended next actions:

1. **Implementation Priority**: Review pending documentation components for implementation
2. **Testing**: Ensure all code modules have corresponding tests
3. **Documentation**: Keep documentation synchronized with code changes
4. **Monitoring**: Regular health checks to maintain project quality

---
*This report was generated automatically by the Project Memory System*
*Last Updated: {timestamp}*
"""
        
        return report
    
    def save_status_report(self, report: str) -> None:
        """Save status report to PROJECT_STATUS.md."""
        with open(self.status_file, 'w') as f:
            f.write(report)
        print(f"📄 Status report saved to {self.status_file}")
    
    def record_work_session(self, session: WorkSession) -> None:
        """Record a work session to history."""
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            except:
                history = []
        
        history.append(asdict(session))
        
        # Keep only last 50 sessions
        if len(history) > 50:
            history = history[-50:]
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        print(f"📝 Work session recorded: {session.session_id}")
    
    def run_full_analysis(self) -> None:
        """Run complete project memory analysis."""
        print("🧠 Starting Project Memory Analysis...")
        print("=" * 60)
        
        # Generate current state
        state = self.generate_current_state()
        
        # Save state to memory files
        self.save_state(state)
        
        # Generate and save status report
        report = self.generate_status_report(state)
        self.save_status_report(report)
        
        print("=" * 60)
        print("✅ Project Memory Analysis Complete!")
        print(f"📁 Memory files saved to: {self.memory_dir}")
        print(f"📄 Status report: {self.status_file}")
        print(f"🔍 Found {state['statistics']['total_components']} total components")
        print(f"🏥 Project health: {state['health_check']['overall_status'].upper()}")


def main():
    """Main entry point for the project memory tracker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MetaFunction Project Memory Tracker")
    parser.add_argument("--project-root", help="Project root directory")
    parser.add_argument("--action", choices=["analyze", "report", "session"], 
                       default="analyze", help="Action to perform")
    parser.add_argument("--session-id", help="Session ID for recording work")
    parser.add_argument("--duration", type=float, help="Session duration in hours")
    
    args = parser.parse_args()
    
    tracker = ProjectMemoryTracker(args.project_root)
    
    if args.action == "analyze":
        tracker.run_full_analysis()
    elif args.action == "report":
        state = tracker.generate_current_state()
        report = tracker.generate_status_report(state)
        print(report)
    elif args.action == "session" and args.session_id:
        # Record a work session (this would be called by other tools)
        session = WorkSession(
            session_id=args.session_id,
            start_time=datetime.datetime.now().isoformat(),
            end_time=datetime.datetime.now().isoformat(),
            duration_hours=args.duration or 1.0,
            focus_areas=["memory_system_implementation"],
            deliverables=[{"type": "tool", "item": "project_memory_tracker.py"}],
            decisions_made=[],
            next_steps=["Test memory system", "Integrate with CI/CD"],
            context_preserved={}
        )
        tracker.record_work_session(session)


if __name__ == "__main__":
    main()
