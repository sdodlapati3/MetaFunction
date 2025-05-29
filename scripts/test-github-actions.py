#!/usr/bin/env python3
"""
Quick test script for GitHub Actions monitoring integration.
"""

import sys
import subprocess
from pathlib import Path

def test_github_actions_validation():
    """Test the GitHub Actions validation script."""
    print("🧪 Testing GitHub Actions validation script...")
    
    script_path = Path(__file__).parent / 'validate-github-actions.py'
    repo_path = Path(__file__).parent.parent
    
    if not script_path.exists():
        print("❌ Validation script not found")
        return False
    
    try:
        # Test basic validation without token
        result = subprocess.run([
            'python3', str(script_path),
            '--repo-path', str(repo_path)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Validation script executed successfully")
            print("📝 Sample output:")
            print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            return True
        else:
            print(f"⚠️ Validation script returned code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Validation script timed out")
        return False
    except Exception as e:
        print(f"❌ Error running validation script: {e}")
        return False

def test_required_files():
    """Test that required test files exist."""
    print("\n🧪 Testing required test files...")
    
    required_files = [
        'tests/performance/locustfile.py',
        'tests/post_deployment/health_check.py',
        'scripts/validate-github-actions.py'
    ]
    
    repo_path = Path(__file__).parent.parent
    all_exist = True
    
    for file_path in required_files:
        full_path = repo_path / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_exist = False
    
    return all_exist

def test_workflow_syntax():
    """Test workflow file syntax."""
    print("\n🧪 Testing workflow file syntax...")
    
    workflows_dir = Path(__file__).parent.parent / '.github' / 'workflows'
    
    if not workflows_dir.exists():
        print("❌ No .github/workflows directory found")
        return False
    
    import yaml
    
    workflow_files = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))
    
    if not workflow_files:
        print("❌ No workflow files found")
        return False
    
    all_valid = True
    
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, 'r') as f:
                yaml.safe_load(f)
            print(f"✅ {workflow_file.name}")
        except yaml.YAMLError as e:
            print(f"❌ {workflow_file.name} - Invalid YAML: {e}")
            all_valid = False
        except Exception as e:
            print(f"⚠️ {workflow_file.name} - Error: {e}")
            all_valid = False
    
    return all_valid

def main():
    """Run all tests."""
    print("🚀 GitHub Actions Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Required Files", test_required_files),
        ("Workflow Syntax", test_workflow_syntax),
        ("Validation Script", test_github_actions_validation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, passed_test in results:
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status} {test_name}")
        if passed_test:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! GitHub Actions integration is ready.")
        return 0
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
