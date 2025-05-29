#!/usr/bin/env python3
"""
GitHub Actions workflow validation script.
Checks for common issues in GitHub Actions workflows and provides fixes.
"""

import os
import yaml
import sys
from pathlib import Path


def check_workflow_file(file_path):
    """Check a workflow file for common issues."""
    issues = []
    
    try:
        with open(file_path, 'r') as f:
            workflow = yaml.safe_load(f)
        
        # Check for outdated action versions
        outdated_actions = {
            'actions/checkout@v3': 'actions/checkout@v4',
            'actions/setup-python@v4': 'actions/setup-python@v5',
            'github/codeql-action/upload-sarif@v2': 'github/codeql-action/upload-sarif@v3',
            'actions/upload-artifact@v3': 'actions/upload-artifact@v4',
            'actions/github-script@v6': 'actions/github-script@v7'
        }
        
        content = Path(file_path).read_text()
        for old_action, new_action in outdated_actions.items():
            if old_action in content:
                issues.append(f"Outdated action: {old_action} should be {new_action}")
        
        # Check for missing continue-on-error for optional steps
        if 'FOSSA_API_KEY' in content and 'continue-on-error: true' not in content:
            issues.append("FOSSA license check should have 'continue-on-error: true'")
        
        return issues
        
    except yaml.YAMLError as e:
        return [f"YAML syntax error: {e}"]
    except Exception as e:
        return [f"Error reading file: {e}"]


def check_required_files():
    """Check if all required files for CI/CD exist."""
    required_files = {
        'tests/performance/locustfile.py': 'Performance testing configuration',
        'tests/post_deployment/health_check.py': 'Post-deployment health check',
        'requirements-dev.txt': 'Development dependencies',
        '.github/workflows/ci-cd.yml': 'CI/CD workflow',
        '.github/workflows/security.yml': 'Security workflow'
    }
    
    missing_files = []
    for file_path, description in required_files.items():
        if not Path(file_path).exists():
            missing_files.append(f"{file_path} - {description}")
    
    return missing_files


def main():
    """Main validation function."""
    print("🔍 GitHub Actions Workflow Validation")
    print("=" * 50)
    
    # Check workflow files
    workflow_dir = Path('.github/workflows')
    if not workflow_dir.exists():
        print("❌ No .github/workflows directory found")
        return 1
    
    total_issues = 0
    
    for workflow_file in workflow_dir.glob('*.yml'):
        print(f"\n📄 Checking {workflow_file.name}...")
        issues = check_workflow_file(workflow_file)
        
        if issues:
            print(f"❌ Found {len(issues)} issues:")
            for issue in issues:
                print(f"   • {issue}")
            total_issues += len(issues)
        else:
            print("✅ No issues found")
    
    # Check required files
    print(f"\n📁 Checking required files...")
    missing_files = check_required_files()
    
    if missing_files:
        print(f"❌ Missing {len(missing_files)} required files:")
        for file in missing_files:
            print(f"   • {file}")
        total_issues += len(missing_files)
    else:
        print("✅ All required files present")
    
    # Summary
    print(f"\n📊 Summary:")
    if total_issues == 0:
        print("✅ All checks passed! Your GitHub Actions setup looks good.")
        return 0
    else:
        print(f"❌ Found {total_issues} total issues that need attention.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
