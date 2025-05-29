#!/usr/bin/env python3
"""
Comprehensive GitHub Actions System Test
Tests the entire monitoring and validation ecosystem
"""

import os
import json
import time
import logging
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GitHubActionsSystemTest:
    """Comprehensive system test for GitHub Actions monitoring."""
    
    def __init__(self, repo_path: str, server_url: str = "http://127.0.0.1:8000"):
        """Initialize the system test.
        
        Args:
            repo_path: Path to the repository
            server_url: URL of the running MetaFunction server
        """
        self.repo_path = Path(repo_path)
        self.server_url = server_url
        self.test_results = {}
        
    def test_scripts_existence(self) -> bool:
        """Test that all required scripts exist."""
        logger.info("🔍 Testing script existence...")
        
        required_scripts = [
            'scripts/validate-github-actions.py',
            'scripts/github-actions-monitor.py',
            'scripts/test-github-actions.py'
        ]
        
        missing_scripts = []
        for script in required_scripts:
            script_path = self.repo_path / script
            if not script_path.exists():
                missing_scripts.append(script)
        
        success = len(missing_scripts) == 0
        self.test_results['script_existence'] = {
            'success': success,
            'missing_scripts': missing_scripts,
            'message': f"Found {len(required_scripts) - len(missing_scripts)}/{len(required_scripts)} scripts"
        }
        
        if success:
            logger.info("✅ All required scripts found")
        else:
            logger.error(f"❌ Missing scripts: {missing_scripts}")
            
        return success
    
    def test_validation_script(self) -> bool:
        """Test the validation script functionality."""
        logger.info("🔍 Testing validation script...")
        
        try:
            cmd = [
                'python3', 
                str(self.repo_path / 'scripts/validate-github-actions.py'),
                '--repo-path', str(self.repo_path),
                '--output', '/tmp/system_test_validation.json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Check if report was generated
            report_exists = os.path.exists('/tmp/system_test_validation.json')
            report_data = {}
            
            if report_exists:
                with open('/tmp/system_test_validation.json', 'r') as f:
                    report_data = json.load(f)
            
            success = result.returncode == 0 and report_exists
            
            self.test_results['validation_script'] = {
                'success': success,
                'return_code': result.returncode,
                'report_exists': report_exists,
                'report_keys': list(report_data.keys()) if report_data else [],
                'stdout': result.stdout[:500] if result.stdout else '',
                'stderr': result.stderr[:500] if result.stderr else ''
            }
            
            if success:
                logger.info("✅ Validation script executed successfully")
            else:
                logger.error(f"❌ Validation script failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Validation script test failed: {e}")
            self.test_results['validation_script'] = {
                'success': False,
                'error': str(e)
            }
            success = False
            
        return success
    
    def test_monitoring_script(self) -> bool:
        """Test the monitoring script functionality."""
        logger.info("🔍 Testing monitoring script...")
        
        try:
            cmd = [
                'python3', 
                str(self.repo_path / 'scripts/github-actions-monitor.py'),
                '--repo-path', str(self.repo_path),
                '--dashboard',
                '--output', '/tmp/system_test_monitoring.json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Check if report was generated
            report_exists = os.path.exists('/tmp/system_test_monitoring.json')
            report_data = {}
            
            if report_exists:
                with open('/tmp/system_test_monitoring.json', 'r') as f:
                    report_data = json.load(f)
            
            success = result.returncode == 0 and report_exists
            
            self.test_results['monitoring_script'] = {
                'success': success,
                'return_code': result.returncode,
                'report_exists': report_exists,
                'report_keys': list(report_data.keys()) if report_data else [],
                'stdout': result.stdout[:500] if result.stdout else '',
                'stderr': result.stderr[:500] if result.stderr else ''
            }
            
            if success:
                logger.info("✅ Monitoring script executed successfully")
            else:
                logger.error(f"❌ Monitoring script failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Monitoring script test failed: {e}")
            self.test_results['monitoring_script'] = {
                'success': False,
                'error': str(e)
            }
            success = False
            
        return success
    
    def test_web_dashboard(self) -> bool:
        """Test the web dashboard functionality."""
        logger.info("🔍 Testing web dashboard...")
        
        try:
            # Test dashboard endpoint
            response = requests.get(f"{self.server_url}/github-actions", timeout=30)
            
            success = response.status_code == 200
            content_length = len(response.content)
            is_html = 'text/html' in response.headers.get('content-type', '')
            
            self.test_results['web_dashboard'] = {
                'success': success,
                'status_code': response.status_code,
                'content_length': content_length,
                'is_html': is_html,
                'response_time': response.elapsed.total_seconds()
            }
            
            if success:
                logger.info(f"✅ Web dashboard accessible ({content_length} bytes)")
            else:
                logger.error(f"❌ Web dashboard failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Web dashboard test failed: {e}")
            self.test_results['web_dashboard'] = {
                'success': False,
                'error': str(e)
            }
            success = False
            
        return success
    
    def test_main_page_navigation(self) -> bool:
        """Test that the main page includes navigation to GitHub Actions dashboard."""
        logger.info("🔍 Testing main page navigation...")
        
        try:
            response = requests.get(self.server_url, timeout=10)
            
            success = response.status_code == 200
            has_github_link = '/github-actions' in response.text
            has_developer_tools = 'Developer Tools' in response.text
            
            self.test_results['main_page_navigation'] = {
                'success': success and has_github_link,
                'status_code': response.status_code,
                'has_github_link': has_github_link,
                'has_developer_tools': has_developer_tools,
                'content_length': len(response.content)
            }
            
            if success and has_github_link:
                logger.info("✅ Main page includes GitHub Actions navigation")
            else:
                logger.error("❌ Main page missing GitHub Actions navigation")
                
        except Exception as e:
            logger.error(f"❌ Main page navigation test failed: {e}")
            self.test_results['main_page_navigation'] = {
                'success': False,
                'error': str(e)
            }
            success = False
            
        return success
    
    def test_template_files(self) -> bool:
        """Test that required template files exist."""
        logger.info("🔍 Testing template files...")
        
        required_templates = [
            'templates/github_actions_enhanced_dashboard.html',
            'templates/index.html'
        ]
        
        missing_templates = []
        for template in required_templates:
            template_path = self.repo_path / template
            if not template_path.exists():
                missing_templates.append(template)
        
        success = len(missing_templates) == 0
        
        self.test_results['template_files'] = {
            'success': success,
            'missing_templates': missing_templates,
            'message': f"Found {len(required_templates) - len(missing_templates)}/{len(required_templates)} templates"
        }
        
        if success:
            logger.info("✅ All required template files found")
        else:
            logger.error(f"❌ Missing templates: {missing_templates}")
            
        return success
    
    def test_dependency_validation(self) -> bool:
        """Test that dependencies are properly configured."""
        logger.info("🔍 Testing dependency validation...")
        
        try:
            # Check requirements-dev.txt for security tools
            req_dev_path = self.repo_path / 'requirements' / 'requirements-dev.txt'
            has_bandit = False
            has_safety = False
            
            if req_dev_path.exists():
                with open(req_dev_path, 'r') as f:
                    content = f.read()
                    has_bandit = 'bandit' in content
                    has_safety = 'safety' in content
            
            success = has_bandit and has_safety
            
            self.test_results['dependency_validation'] = {
                'success': success,
                'has_bandit': has_bandit,
                'has_safety': has_safety,
                'requirements_dev_exists': req_dev_path.exists()
            }
            
            if success:
                logger.info("✅ Security dependencies properly configured")
            else:
                logger.error("❌ Missing security dependencies in requirements/requirements-dev.txt")
                
        except Exception as e:
            logger.error(f"❌ Dependency validation test failed: {e}")
            self.test_results['dependency_validation'] = {
                'success': False,
                'error': str(e)
            }
            success = False
            
        return success
    
    def generate_report(self) -> Dict:
        """Generate a comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get('success', False))
        
        report = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'repository': str(self.repo_path),
            'server_url': self.server_url,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0
            },
            'test_results': self.test_results,
            'overall_status': 'PASS' if passed_tests == total_tests else 'FAIL'
        }
        
        return report
    
    def run_all_tests(self) -> Dict:
        """Run all system tests."""
        logger.info("🚀 Starting GitHub Actions System Test Suite")
        logger.info("=" * 70)
        
        # Run all tests
        tests = [
            self.test_scripts_existence,
            self.test_validation_script,
            self.test_monitoring_script,
            self.test_template_files,
            self.test_dependency_validation,
            self.test_main_page_navigation,
            self.test_web_dashboard
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                logger.error(f"Test {test.__name__} failed with exception: {e}")
            
        # Generate report
        report = self.generate_report()
        
        # Print summary
        logger.info("=" * 70)
        logger.info(f"🏁 Test Suite Complete: {report['overall_status']}")
        logger.info(f"📊 Results: {report['summary']['passed_tests']}/{report['summary']['total_tests']} tests passed ({report['summary']['success_rate']}%)")
        
        return report


def main():
    """Main function to run the system test."""
    import argparse
    
    parser = argparse.ArgumentParser(description='GitHub Actions System Test')
    parser.add_argument('--repo-path', required=True, help='Path to the repository')
    parser.add_argument('--server-url', default='http://127.0.0.1:8000', help='Server URL')
    parser.add_argument('--output', help='Output file for test report')
    
    args = parser.parse_args()
    
    # Run tests
    tester = GitHubActionsSystemTest(args.repo_path, args.server_url)
    report = tester.run_all_tests()
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"📄 Report saved to: {args.output}")
    
    # Exit with appropriate code
    exit_code = 0 if report['overall_status'] == 'PASS' else 1
    exit(exit_code)


if __name__ == '__main__':
    main()
