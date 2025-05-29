#!/usr/bin/env python3
"""
Post-deployment health check script for MetaFunction application.
Validates that the deployed application is working correctly.
"""
import argparse
import requests
import time
import sys
import json
from typing import Dict, List, Optional


class HealthChecker:
    """Health check utility for MetaFunction deployment."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize health checker.
        
        Args:
            base_url: Base URL of the deployed application
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MetaFunction-HealthCheck/1.0'
        })
    
    def check_endpoint(self, endpoint: str, expected_status: int = 200, 
                      method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """Check a specific endpoint.
        
        Args:
            endpoint: Endpoint path
            expected_status: Expected HTTP status code
            method: HTTP method
            data: Request data for POST requests
            
        Returns:
            Dict with check results
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, data=data, timeout=self.timeout)
            else:
                return {
                    'endpoint': endpoint,
                    'status': 'error',
                    'message': f'Unsupported method: {method}'
                }
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            success = response.status_code == expected_status
            
            return {
                'endpoint': endpoint,
                'status': 'pass' if success else 'fail',
                'status_code': response.status_code,
                'expected_status': expected_status,
                'response_time_ms': round(response_time, 2),
                'message': 'OK' if success else f'Expected {expected_status}, got {response.status_code}',
                'content_length': len(response.content)
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'endpoint': endpoint,
                'status': 'error',
                'message': str(e)
            }
    
    def run_health_checks(self) -> List[Dict]:
        """Run all health checks.
        
        Returns:
            List of check results
        """
        checks = [
            # Basic availability
            {'endpoint': '/', 'expected_status': 200},
            {'endpoint': '/health', 'expected_status': 200},
            
            # Static resources
            {'endpoint': '/static/favicon.ico', 'expected_status': 200},
            
            # API endpoints (if they exist)
            {'endpoint': '/api/health', 'expected_status': 200},
            {'endpoint': '/api/status', 'expected_status': 200},
            
            # Test a simple chat request
            {
                'endpoint': '/chat',
                'method': 'POST',
                'expected_status': 200,
                'data': {
                    'paper_text': 'Sample paper for health check',
                    'model': 'gpt-4o-mini',
                    'analysis_focus': 'summary'
                }
            }
        ]
        
        results = []
        for check in checks:
            print(f"Checking {check['endpoint']}...")
            result = self.check_endpoint(
                check['endpoint'],
                check.get('expected_status', 200),
                check.get('method', 'GET'),
                check.get('data')
            )
            results.append(result)
            
            # Print immediate feedback
            status_emoji = "✅" if result['status'] == 'pass' else "❌" if result['status'] == 'fail' else "⚠️"
            print(f"  {status_emoji} {result['status'].upper()}: {result.get('message', 'No message')}")
            
            # Small delay between checks
            time.sleep(0.5)
        
        return results
    
    def print_summary(self, results: List[Dict]) -> bool:
        """Print summary of health check results.
        
        Args:
            results: List of check results
            
        Returns:
            True if all checks passed, False otherwise
        """
        passed = sum(1 for r in results if r['status'] == 'pass')
        failed = sum(1 for r in results if r['status'] == 'fail')
        errors = sum(1 for r in results if r['status'] == 'error')
        total = len(results)
        
        print("\n" + "="*60)
        print("HEALTH CHECK SUMMARY")
        print("="*60)
        print(f"Total checks: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Errors: {errors} ⚠️")
        print(f"Success rate: {(passed/total)*100:.1f}%")
        
        if failed > 0 or errors > 0:
            print("\nFAILED/ERROR CHECKS:")
            for result in results:
                if result['status'] in ['fail', 'error']:
                    print(f"  - {result['endpoint']}: {result['message']}")
        
        # Calculate average response time for successful checks
        successful_times = [r['response_time_ms'] for r in results 
                          if r['status'] == 'pass' and 'response_time_ms' in r]
        if successful_times:
            avg_time = sum(successful_times) / len(successful_times)
            print(f"\nAverage response time: {avg_time:.2f}ms")
        
        return failed == 0 and errors == 0


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Post-deployment health check for MetaFunction'
    )
    parser.add_argument(
        '--url',
        required=True,
        help='Base URL of the deployed application'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    parser.add_argument(
        '--output',
        help='Output file for detailed results (JSON format)'
    )
    parser.add_argument(
        '--critical-only',
        action='store_true',
        help='Only check critical endpoints'
    )
    
    args = parser.parse_args()
    
    print(f"Running health checks for: {args.url}")
    print(f"Timeout: {args.timeout}s")
    print("-" * 60)
    
    # Initialize health checker
    checker = HealthChecker(args.url, args.timeout)
    
    # Run checks
    try:
        results = checker.run_health_checks()
        
        # Save detailed results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                    'base_url': args.url,
                    'results': results
                }, f, indent=2)
            print(f"\nDetailed results saved to: {args.output}")
        
        # Print summary and exit with appropriate code
        all_passed = checker.print_summary(results)
        sys.exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        print("\nHealth check interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error during health check: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
