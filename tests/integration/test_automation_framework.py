#!/usr/bin/env python3
"""
Enhanced Integration Testing Automation Framework for MetaFunction

This framework provides comprehensive automated testing for enterprise-grade
integration scenarios, production readiness validation, and continuous
deployment pipeline testing.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml
import requests
import psycopg2
import redis
import kubernetes
from kubernetes import client, config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Represents the result of a test execution."""
    test_name: str
    status: str  # PASSED, FAILED, ERROR, SKIPPED
    duration: float
    timestamp: datetime
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestSuite:
    """Represents a collection of related tests."""
    name: str
    description: str
    tests: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 900  # Default 15 minutes
    parallel: bool = False

class IntegrationTestFramework:
    """Advanced integration testing framework for MetaFunction enterprise features."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.test_results: Dict[str, TestResult] = {}
        self.test_suites: Dict[str, TestSuite] = {}
        self.start_time = datetime.now()
        self.session_id = str(uuid.uuid4())[:8]
        
        # Initialize Kubernetes client
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.k8s_client = client.ApiClient()
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.batch_v1 = client.BatchV1Api()
        
        # Test environment setup
        self.namespace = self.config.get('namespace', 'integration-test')
        self.environment = self.config.get('environment', 'integration')
        self.test_data_dir = Path(self.config.get('test_data_dir', '/tmp/integration-tests'))
        self.test_data_dir.mkdir(exist_ok=True)
        
        # Initialize test suites
        self._initialize_test_suites()
    
    def _load_config(self, config_file: Optional[str]) -> Dict:
        """Load configuration from file or use defaults."""
        default_config = {
            'namespace': 'integration-test',
            'environment': 'integration',
            'timeout': 1800,
            'parallel_execution': True,
            'retry_count': 3,
            'test_data_dir': '/tmp/integration-tests',
            'reporting': {
                'formats': ['json', 'html', 'junit'],
                'output_dir': './test-reports'
            },
            'notifications': {
                'slack_webhook': os.getenv('SLACK_WEBHOOK'),
                'email_recipients': []
            }
        }
        
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
        
        return default_config
    
    def _initialize_test_suites(self):
        """Initialize predefined test suites."""
        self.test_suites = {
            'infrastructure': TestSuite(
                name='Infrastructure Tests',
                description='Validate infrastructure components and connectivity',
                tests=[
                    'test_kubernetes_cluster_health',
                    'test_network_connectivity',
                    'test_storage_availability',
                    'test_dns_resolution'
                ],
                timeout=600,
                parallel=True
            ),
            'application': TestSuite(
                name='Application Tests',
                description='Validate application deployment and functionality',
                tests=[
                    'test_application_deployment',
                    'test_service_endpoints',
                    'test_health_checks',
                    'test_api_functionality'
                ],
                dependencies=['infrastructure'],
                timeout=900
            ),
            'data': TestSuite(
                name='Data Layer Tests',
                description='Validate database and data services',
                tests=[
                    'test_database_connectivity',
                    'test_data_migration',
                    'test_backup_restoration',
                    'test_data_consistency'
                ],
                dependencies=['infrastructure'],
                timeout=1200
            ),
            'security': TestSuite(
                name='Security Tests',
                description='Validate security controls and compliance',
                tests=[
                    'test_authentication',
                    'test_authorization',
                    'test_network_policies',
                    'test_vulnerability_scanning',
                    'test_compliance_checks'
                ],
                dependencies=['application'],
                timeout=900
            ),
            'performance': TestSuite(
                name='Performance Tests',
                description='Validate performance characteristics',
                tests=[
                    'test_load_performance',
                    'test_stress_testing',
                    'test_scalability',
                    'test_resource_utilization'
                ],
                dependencies=['application', 'data'],
                timeout=1800,
                parallel=True
            ),
            'integration': TestSuite(
                name='End-to-End Integration Tests',
                description='Validate complete user workflows',
                tests=[
                    'test_user_registration_workflow',
                    'test_function_execution_workflow',
                    'test_error_handling_workflow',
                    'test_monitoring_integration'
                ],
                dependencies=['application', 'data', 'security'],
                timeout=1200
            ),
            'disaster_recovery': TestSuite(
                name='Disaster Recovery Tests',
                description='Validate backup and recovery procedures',
                tests=[
                    'test_backup_creation',
                    'test_backup_verification',
                    'test_disaster_simulation',
                    'test_recovery_procedures'
                ],
                dependencies=['data'],
                timeout=2400
            )
        }
    
    async def run_test_suite(self, suite_name: str) -> Dict[str, TestResult]:
        """Run a specific test suite."""
        if suite_name not in self.test_suites:
            raise ValueError(f"Test suite '{suite_name}' not found")
        
        suite = self.test_suites[suite_name]
        logger.info(f"Starting test suite: {suite.name}")
        
        # Check dependencies
        for dep in suite.dependencies:
            if not self._check_dependency_satisfied(dep):
                logger.error(f"Dependency '{dep}' not satisfied for suite '{suite_name}'")
                return {}
        
        # Run tests in suite
        suite_results = {}
        
        if suite.parallel and len(suite.tests) > 1:
            suite_results = await self._run_tests_parallel(suite.tests, suite.timeout)
        else:
            suite_results = await self._run_tests_sequential(suite.tests, suite.timeout)
        
        # Update global results
        self.test_results.update(suite_results)
        
        return suite_results
    
    async def run_all_test_suites(self) -> Dict[str, Dict[str, TestResult]]:
        """Run all test suites in dependency order."""
        logger.info("Starting comprehensive integration test execution")
        
        # Determine execution order based on dependencies
        execution_order = self._resolve_dependencies()
        all_results = {}
        
        for suite_name in execution_order:
            try:
                logger.info(f"Executing test suite: {suite_name}")
                suite_results = await self.run_test_suite(suite_name)
                all_results[suite_name] = suite_results
                
                # Check for critical failures
                if self._has_critical_failures(suite_results):
                    logger.error(f"Critical failures in {suite_name}, stopping execution")
                    break
                    
            except Exception as e:
                logger.error(f"Failed to execute test suite {suite_name}: {e}")
                all_results[suite_name] = {}
        
        return all_results
    
    async def _run_tests_parallel(self, test_names: List[str], timeout: int) -> Dict[str, TestResult]:
        """Run tests in parallel."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=min(len(test_names), 10)) as executor:
            # Submit all tests
            future_to_test = {
                executor.submit(self._execute_test_sync, test_name): test_name 
                for test_name in test_names
            }
            
            # Collect results
            for future in as_completed(future_to_test, timeout=timeout):
                test_name = future_to_test[future]
                try:
                    result = future.result()
                    results[test_name] = result
                except Exception as e:
                    logger.error(f"Test {test_name} failed with exception: {e}")
                    results[test_name] = TestResult(
                        test_name=test_name,
                        status="ERROR",
                        duration=0.0,
                        timestamp=datetime.now(),
                        error_message=str(e)
                    )
        
        return results
    
    async def _run_tests_sequential(self, test_names: List[str], timeout: int) -> Dict[str, TestResult]:
        """Run tests sequentially."""
        results = {}
        
        for test_name in test_names:
            try:
                result = await self._execute_test(test_name)
                results[test_name] = result
                
                # Stop on critical failure if configured
                if result.status == "FAILED" and self._is_critical_test(test_name):
                    logger.error(f"Critical test {test_name} failed, stopping suite")
                    break
                    
            except Exception as e:
                logger.error(f"Test {test_name} failed with exception: {e}")
                results[test_name] = TestResult(
                    test_name=test_name,
                    status="ERROR",
                    duration=0.0,
                    timestamp=datetime.now(),
                    error_message=str(e)
                )
        
        return results
    
    def _execute_test_sync(self, test_name: str) -> TestResult:
        """Synchronous wrapper for test execution."""
        return asyncio.run(self._execute_test(test_name))
    
    async def _execute_test(self, test_name: str) -> TestResult:
        """Execute a single test."""
        start_time = time.time()
        
        try:
            # Get test method
            test_method = getattr(self, test_name, None)
            if not test_method:
                raise ValueError(f"Test method '{test_name}' not found")
            
            logger.info(f"Executing test: {test_name}")
            
            # Execute test with retry logic
            result = await self._execute_with_retry(test_method)
            
            duration = time.time() - start_time
            
            return TestResult(
                test_name=test_name,
                status="PASSED" if result else "FAILED",
                duration=duration,
                timestamp=datetime.now(),
                details=getattr(test_method, '_test_details', {})
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Test {test_name} failed: {e}")
            
            return TestResult(
                test_name=test_name,
                status="ERROR",
                duration=duration,
                timestamp=datetime.now(),
                error_message=str(e)
            )
    
    async def _execute_with_retry(self, test_method, max_retries: int = None) -> bool:
        """Execute test method with retry logic."""
        if max_retries is None:
            max_retries = self.config.get('retry_count', 3)
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(test_method):
                    return await test_method()
                else:
                    return test_method()
                    
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Test attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Test failed after {max_retries + 1} attempts")
                    raise last_exception
        
        raise last_exception
    
    # Infrastructure Tests
    async def test_kubernetes_cluster_health(self) -> bool:
        """Test Kubernetes cluster health."""
        try:
            # Check cluster info
            cluster_info = subprocess.run(['kubectl', 'cluster-info'], 
                                        capture_output=True, text=True, timeout=30)
            if cluster_info.returncode != 0:
                return False
            
            # Check node status
            nodes = self.v1.list_node()
            ready_nodes = 0
            for node in nodes.items:
                for condition in node.status.conditions:
                    if condition.type == "Ready" and condition.status == "True":
                        ready_nodes += 1
                        break
            
            if ready_nodes == 0:
                logger.error("No ready nodes found")
                return False
            
            logger.info(f"Cluster health check passed: {ready_nodes} ready nodes")
            return True
            
        except Exception as e:
            logger.error(f"Cluster health check failed: {e}")
            return False
    
    async def test_network_connectivity(self) -> bool:
        """Test network connectivity between components."""
        try:
            # Test DNS resolution
            test_job = await self._create_test_job(
                "network-connectivity-test",
                "alpine:latest",
                ["/bin/sh", "-c", """
                    # Test DNS resolution
                    nslookup kubernetes.default.svc.cluster.local || exit 1
                    
                    # Test external connectivity
                    wget -q --spider https://google.com || exit 1
                    
                    echo "Network connectivity test passed"
                """]
            )
            
            return await self._wait_for_job_completion(test_job, timeout=120)
            
        except Exception as e:
            logger.error(f"Network connectivity test failed: {e}")
            return False
    
    async def test_storage_availability(self) -> bool:
        """Test storage availability and functionality."""
        try:
            # Create test PVC
            pvc_manifest = {
                "apiVersion": "v1",
                "kind": "PersistentVolumeClaim",
                "metadata": {
                    "name": f"test-storage-{self.session_id}",
                    "namespace": self.namespace
                },
                "spec": {
                    "accessModes": ["ReadWriteOnce"],
                    "resources": {
                        "requests": {
                            "storage": "1Gi"
                        }
                    }
                }
            }
            
            # Create PVC
            self.v1.create_namespaced_persistent_volume_claim(
                namespace=self.namespace,
                body=pvc_manifest
            )
            
            # Wait for PVC to be bound
            for _ in range(30):  # 5 minutes
                pvc = self.v1.read_namespaced_persistent_volume_claim(
                    name=f"test-storage-{self.session_id}",
                    namespace=self.namespace
                )
                if pvc.status.phase == "Bound":
                    break
                await asyncio.sleep(10)
            else:
                logger.error("PVC did not bind within timeout")
                return False
            
            # Test storage with a pod
            storage_test_job = await self._create_test_job(
                "storage-test",
                "alpine:latest",
                ["/bin/sh", "-c", """
                    # Test write
                    echo "test data" > /mnt/testfile
                    
                    # Test read
                    if [ "$(cat /mnt/testfile)" = "test data" ]; then
                        echo "Storage test passed"
                        exit 0
                    else
                        echo "Storage test failed"
                        exit 1
                    fi
                """],
                volume_mounts=[{
                    "name": "test-storage",
                    "mountPath": "/mnt"
                }],
                volumes=[{
                    "name": "test-storage",
                    "persistentVolumeClaim": {
                        "claimName": f"test-storage-{self.session_id}"
                    }
                }]
            )
            
            result = await self._wait_for_job_completion(storage_test_job, timeout=300)
            
            # Cleanup
            try:
                self.v1.delete_namespaced_persistent_volume_claim(
                    name=f"test-storage-{self.session_id}",
                    namespace=self.namespace
                )
            except:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"Storage availability test failed: {e}")
            return False
    
    async def test_dns_resolution(self) -> bool:
        """Test DNS resolution within the cluster."""
        try:
            dns_test_job = await self._create_test_job(
                "dns-resolution-test",
                "alpine:latest",
                ["/bin/sh", "-c", """
                    # Test internal DNS
                    nslookup kubernetes.default.svc.cluster.local || exit 1
                    
                    # Test service discovery
                    nslookup kube-dns.kube-system.svc.cluster.local || exit 1
                    
                    # Test external DNS
                    nslookup google.com || exit 1
                    
                    echo "DNS resolution test passed"
                """]
            )
            
            return await self._wait_for_job_completion(dns_test_job, timeout=120)
            
        except Exception as e:
            logger.error(f"DNS resolution test failed: {e}")
            return False
    
    # Application Tests
    async def test_application_deployment(self) -> bool:
        """Test MetaFunction application deployment."""
        try:
            # Check if application deployment exists
            deployments = self.apps_v1.list_namespaced_deployment(
                namespace=self.namespace,
                label_selector="app.kubernetes.io/name=metafunction"
            )
            
            if not deployments.items:
                logger.error("MetaFunction deployment not found")
                return False
            
            # Check deployment status
            deployment = deployments.items[0]
            if not deployment.status.ready_replicas:
                logger.error("No ready replicas in deployment")
                return False
            
            if deployment.status.ready_replicas != deployment.spec.replicas:
                logger.error(f"Only {deployment.status.ready_replicas}/{deployment.spec.replicas} replicas ready")
                return False
            
            logger.info("Application deployment verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Application deployment test failed: {e}")
            return False
    
    async def test_service_endpoints(self) -> bool:
        """Test service endpoints and load balancing."""
        try:
            # Get service
            services = self.v1.list_namespaced_service(
                namespace=self.namespace,
                label_selector="app.kubernetes.io/name=metafunction"
            )
            
            if not services.items:
                logger.error("MetaFunction service not found")
                return False
            
            service = services.items[0]
            
            # Check endpoints
            endpoints = self.v1.read_namespaced_endpoints(
                name=service.metadata.name,
                namespace=self.namespace
            )
            
            if not endpoints.subsets or not endpoints.subsets[0].addresses:
                logger.error("No healthy endpoints found")
                return False
            
            endpoint_count = len(endpoints.subsets[0].addresses)
            logger.info(f"Service endpoints test passed: {endpoint_count} healthy endpoints")
            return True
            
        except Exception as e:
            logger.error(f"Service endpoints test failed: {e}")
            return False
    
    async def test_health_checks(self) -> bool:
        """Test application health check endpoints."""
        try:
            health_test_job = await self._create_test_job(
                "health-check-test",
                "alpine/curl:latest",
                ["/bin/sh", "-c", f"""
                    # Test health endpoint
                    curl -f http://metafunction.{self.namespace}.svc.cluster.local:8000/health || exit 1
                    
                    # Test readiness endpoint
                    curl -f http://metafunction.{self.namespace}.svc.cluster.local:8000/readiness || exit 1
                    
                    # Test metrics endpoint
                    curl -f http://metafunction.{self.namespace}.svc.cluster.local:8000/metrics || exit 1
                    
                    echo "Health checks passed"
                """]
            )
            
            return await self._wait_for_job_completion(health_test_job, timeout=120)
            
        except Exception as e:
            logger.error(f"Health checks test failed: {e}")
            return False
    
    async def test_api_functionality(self) -> bool:
        """Test core API functionality."""
        try:
            api_test_job = await self._create_test_job(
                "api-functionality-test",
                "python:3.11-slim",
                ["/bin/sh", "-c", f"""
                    pip install requests
                    python3 -c "
import requests
import json

base_url = 'http://metafunction.{self.namespace}.svc.cluster.local:8000'

# Test function execution
response = requests.post(f'{{base_url}}/execute', json={{
    'code': 'def test(): return \"Hello World\"',
    'function_name': 'test'
}})

if response.status_code != 200:
    exit(1)

result = response.json()
if result.get('result') != 'Hello World':
    exit(1)

print('API functionality test passed')
"
                """]
            )
            
            return await self._wait_for_job_completion(api_test_job, timeout=300)
            
        except Exception as e:
            logger.error(f"API functionality test failed: {e}")
            return False
    
    # Data Layer Tests
    async def test_database_connectivity(self) -> bool:
        """Test database connectivity and basic operations."""
        try:
            db_test_job = await self._create_test_job(
                "database-connectivity-test",
                "postgres:15-alpine",
                ["/bin/sh", "-c", f"""
                    # Test connection
                    PGPASSWORD=$POSTGRES_PASSWORD psql -h postgresql.{self.namespace}.svc.cluster.local -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;" || exit 1
                    
                    # Test table creation
                    PGPASSWORD=$POSTGRES_PASSWORD psql -h postgresql.{self.namespace}.svc.cluster.local -U $POSTGRES_USER -d $POSTGRES_DB -c "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, data TEXT);" || exit 1
                    
                    # Test insert
                    PGPASSWORD=$POSTGRES_PASSWORD psql -h postgresql.{self.namespace}.svc.cluster.local -U $POSTGRES_USER -d $POSTGRES_DB -c "INSERT INTO test_table (data) VALUES ('test data');" || exit 1
                    
                    # Test select
                    PGPASSWORD=$POSTGRES_PASSWORD psql -h postgresql.{self.namespace}.svc.cluster.local -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT COUNT(*) FROM test_table;" || exit 1
                    
                    # Cleanup
                    PGPASSWORD=$POSTGRES_PASSWORD psql -h postgresql.{self.namespace}.svc.cluster.local -U $POSTGRES_USER -d $POSTGRES_DB -c "DROP TABLE test_table;" || exit 1
                    
                    echo "Database connectivity test passed"
                """],
                env_vars=[
                    {"name": "POSTGRES_HOST", "value": f"postgresql.{self.namespace}.svc.cluster.local"},
                    {"name": "POSTGRES_DB", "value": "metafunction"},
                    {"name": "POSTGRES_USER", "value": "postgres"},
                    {"name": "POSTGRES_PASSWORD", "valueFrom": {"secretKeyRef": {"name": "postgresql-secret", "key": "password"}}}
                ]
            )
            
            return await self._wait_for_job_completion(db_test_job, timeout=300)
            
        except Exception as e:
            logger.error(f"Database connectivity test failed: {e}")
            return False
    
    # Utility methods
    async def _create_test_job(self, name: str, image: str, command: List[str], 
                              env_vars: List[Dict] = None, volume_mounts: List[Dict] = None,
                              volumes: List[Dict] = None) -> str:
        """Create a test job and return its name."""
        job_name = f"{name}-{self.session_id}-{int(time.time())}"
        
        container_spec = {
            "name": "test",
            "image": image,
            "command": command
        }
        
        if env_vars:
            container_spec["env"] = env_vars
        
        if volume_mounts:
            container_spec["volumeMounts"] = volume_mounts
        
        job_manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "namespace": self.namespace,
                "labels": {
                    "test-session": self.session_id,
                    "test-framework": "integration"
                }
            },
            "spec": {
                "template": {
                    "spec": {
                        "containers": [container_spec],
                        "restartPolicy": "Never"
                    }
                },
                "backoffLimit": 0
            }
        }
        
        if volumes:
            job_manifest["spec"]["template"]["spec"]["volumes"] = volumes
        
        # Create job
        self.batch_v1.create_namespaced_job(
            namespace=self.namespace,
            body=job_manifest
        )
        
        return job_name
    
    async def _wait_for_job_completion(self, job_name: str, timeout: int = 300) -> bool:
        """Wait for job completion and return success status."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                job = self.batch_v1.read_namespaced_job_status(
                    name=job_name,
                    namespace=self.namespace
                )
                
                if job.status.succeeded:
                    # Cleanup job
                    self.batch_v1.delete_namespaced_job(
                        name=job_name,
                        namespace=self.namespace
                    )
                    return True
                
                if job.status.failed:
                    # Get logs for debugging
                    try:
                        pods = self.v1.list_namespaced_pod(
                            namespace=self.namespace,
                            label_selector=f"job-name={job_name}"
                        )
                        if pods.items:
                            logs = self.v1.read_namespaced_pod_log(
                                name=pods.items[0].metadata.name,
                                namespace=self.namespace
                            )
                            logger.error(f"Job {job_name} failed. Logs:\n{logs}")
                    except:
                        pass
                    
                    # Cleanup job
                    self.batch_v1.delete_namespaced_job(
                        name=job_name,
                        namespace=self.namespace
                    )
                    return False
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error checking job status: {e}")
                await asyncio.sleep(5)
        
        logger.error(f"Job {job_name} timed out")
        # Cleanup job
        try:
            self.batch_v1.delete_namespaced_job(
                name=job_name,
                namespace=self.namespace
            )
        except:
            pass
        
        return False
    
    def _resolve_dependencies(self) -> List[str]:
        """Resolve test suite dependencies and return execution order."""
        resolved = []
        remaining = list(self.test_suites.keys())
        
        while remaining:
            # Find suites with no unresolved dependencies
            ready = []
            for suite_name in remaining:
                suite = self.test_suites[suite_name]
                if all(dep in resolved for dep in suite.dependencies):
                    ready.append(suite_name)
            
            if not ready:
                # Circular dependency or missing dependency
                logger.error(f"Cannot resolve dependencies for: {remaining}")
                break
            
            # Add ready suites to resolved list
            for suite_name in ready:
                resolved.append(suite_name)
                remaining.remove(suite_name)
        
        return resolved
    
    def _check_dependency_satisfied(self, dep_name: str) -> bool:
        """Check if a dependency is satisfied."""
        if dep_name not in self.test_results:
            return False
        
        # Check if all tests in dependency suite passed
        dep_suite = self.test_suites.get(dep_name)
        if not dep_suite:
            return False
        
        for test_name in dep_suite.tests:
            result = self.test_results.get(test_name)
            if not result or result.status not in ["PASSED"]:
                return False
        
        return True
    
    def _has_critical_failures(self, results: Dict[str, TestResult]) -> bool:
        """Check if there are critical failures that should stop execution."""
        critical_tests = ['test_kubernetes_cluster_health', 'test_application_deployment']
        
        for test_name, result in results.items():
            if test_name in critical_tests and result.status in ["FAILED", "ERROR"]:
                return True
        
        return False
    
    def _is_critical_test(self, test_name: str) -> bool:
        """Check if a test is critical."""
        critical_tests = ['test_kubernetes_cluster_health', 'test_application_deployment']
        return test_name in critical_tests
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report."""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r.status == "PASSED"])
        failed_tests = len([r for r in self.test_results.values() if r.status == "FAILED"])
        error_tests = len([r for r in self.test_results.values() if r.status == "ERROR"])
        
        report = {
            "test_session": {
                "session_id": self.session_id,
                "framework": "MetaFunction Integration Test Framework",
                "environment": self.environment,
                "namespace": self.namespace,
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_duration": f"{total_duration:.2f}s"
            },
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "success_rate": f"{(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "0%"
            },
            "test_suites": {
                name: {
                    "description": suite.description,
                    "test_count": len(suite.tests),
                    "dependencies": suite.dependencies
                }
                for name, suite in self.test_suites.items()
            },
            "test_results": {
                name: {
                    "status": result.status,
                    "duration": f"{result.duration:.2f}s",
                    "timestamp": result.timestamp.isoformat(),
                    "error_message": result.error_message,
                    "details": result.details
                }
                for name, result in self.test_results.items()
            },
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_tests = [name for name, result in self.test_results.items() if result.status in ["FAILED", "ERROR"]]
        
        if "test_kubernetes_cluster_health" in failed_tests:
            recommendations.append("Review Kubernetes cluster configuration and node health")
        
        if "test_application_deployment" in failed_tests:
            recommendations.append("Check application deployment manifests and resource requirements")
        
        if "test_database_connectivity" in failed_tests:
            recommendations.append("Verify database service configuration and network policies")
        
        if "test_network_connectivity" in failed_tests:
            recommendations.append("Review network configuration and DNS settings")
        
        if "test_storage_availability" in failed_tests:
            recommendations.append("Check storage class configuration and persistent volume provisioning")
        
        if len(failed_tests) == 0:
            recommendations.append("All integration tests passed - system is ready for production deployment")
        elif len(failed_tests) < len(self.test_results) * 0.1:  # Less than 10% failure rate
            recommendations.append("Minor issues detected - review failed tests and consider proceeding with caution")
        else:
            recommendations.append("Significant issues detected - resolve failures before production deployment")
        
        return recommendations
    
    async def cleanup(self):
        """Cleanup test resources."""
        try:
            # Delete test jobs
            jobs = self.batch_v1.list_namespaced_job(
                namespace=self.namespace,
                label_selector=f"test-session={self.session_id}"
            )
            
            for job in jobs.items:
                self.batch_v1.delete_namespaced_job(
                    name=job.metadata.name,
                    namespace=self.namespace
                )
            
            # Delete test PVCs
            pvcs = self.v1.list_namespaced_persistent_volume_claim(
                namespace=self.namespace,
                label_selector=f"test-session={self.session_id}"
            )
            
            for pvc in pvcs.items:
                self.v1.delete_namespaced_persistent_volume_claim(
                    name=pvc.metadata.name,
                    namespace=self.namespace
                )
            
            logger.info("Test cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

async def main():
    """Main test execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MetaFunction Integration Test Framework")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--namespace", default="integration-test", help="Kubernetes namespace")
    parser.add_argument("--environment", default="integration", help="Environment name")
    parser.add_argument("--suite", help="Specific test suite to run")
    parser.add_argument("--output", default="integration-test-report.json", help="Output file for test report")
    parser.add_argument("--cleanup", action="store_true", help="Run cleanup after tests")
    
    args = parser.parse_args()
    
    # Initialize framework
    framework = IntegrationTestFramework(config_file=args.config)
    framework.namespace = args.namespace
    framework.environment = args.environment
    
    try:
        # Run tests
        if args.suite:
            logger.info(f"Running specific test suite: {args.suite}")
            results = await framework.run_test_suite(args.suite)
        else:
            logger.info("Running all test suites")
            results = await framework.run_all_test_suites()
        
        # Generate report
        report = framework.generate_report()
        
        # Save report
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*80)
        print("METAFUNCTION INTEGRATION TEST SUMMARY")
        print("="*80)
        print(f"Session ID: {report['test_session']['session_id']}")
        print(f"Environment: {report['test_session']['environment']}")
        print(f"Namespace: {report['test_session']['namespace']}")
        print(f"Total Duration: {report['test_session']['total_duration']}")
        print(f"Success Rate: {report['summary']['success_rate']}")
        print(f"Tests: {report['summary']['passed']}/{report['summary']['total_tests']} passed")
        
        if report['summary']['failed'] > 0 or report['summary']['errors'] > 0:
            print(f"\nFailed Tests: {report['summary']['failed']}")
            print(f"Error Tests: {report['summary']['errors']}")
            
            for name, result in report['test_results'].items():
                if result['status'] in ['FAILED', 'ERROR']:
                    print(f"  ❌ {name}: {result['status']}")
                    if result['error_message']:
                        print(f"     Error: {result['error_message']}")
        
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        print(f"\nDetailed report saved to: {args.output}")
        
        # Cleanup if requested
        if args.cleanup:
            await framework.cleanup()
        
        # Exit with appropriate code
        if report['summary']['failed'] > 0 or report['summary']['errors'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Framework execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
