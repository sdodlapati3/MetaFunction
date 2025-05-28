# MetaFunction Operational Runbooks

## Table of Contents

1. [Incident Response](#incident-response)
2. [Database Operations](#database-operations)
3. [Deployment Operations](#deployment-operations)
4. [Security Operations](#security-operations)
5. [Performance Troubleshooting](#performance-troubleshooting)
6. [Backup and Recovery](#backup-and-recovery)
7. [Monitoring and Alerting](#monitoring-and-alerting)

---

## Incident Response

### P0 - Critical Service Outage

**Detection**: Service completely unavailable, error rate >90%

**Immediate Response** (0-15 minutes):
1. **Acknowledge the incident**
   ```bash
   # Create incident channel
   slack-cli create-channel "incident-$(date +%Y%m%d-%H%M)"
   
   # Page on-call engineer
   pagerduty-cli trigger-incident \
     --service "metafunction-production" \
     --summary "Critical service outage detected"
   ```

2. **Assess the scope**
   ```bash
   # Check service health
   kubectl get pods -l app=metafunction -A
   kubectl get services -l app=metafunction -A
   
   # Check external dependencies
   curl -f https://api.openai.com/health
   kubectl exec -it postgresql-0 -- pg_isready
   ```

3. **Implement immediate mitigation**
   ```bash
   # Scale up replicas
   kubectl scale deployment metafunction --replicas=6
   
   # Enable maintenance mode if needed
   kubectl patch configmap maintenance-mode \
     -p '{"data":{"enabled":"true","message":"Service temporarily unavailable"}}'
   
   # Failover to backup region
   ./scripts/failover-to-backup-region.sh us-west-2
   ```

**Investigation** (15-60 minutes):
1. **Gather logs and metrics**
   ```bash
   # Application logs
   kubectl logs deployment/metafunction --tail=1000 > incident-app-logs.txt
   
   # System metrics
   curl "http://prometheus:9090/api/v1/query_range?query=up&start=$(date -d '1 hour ago' +%s)&end=$(date +%s)&step=60"
   
   # Database status
   kubectl exec -it postgresql-0 -- psql -U postgres -c "SELECT * FROM pg_stat_activity;"
   ```

2. **Identify root cause**
   - Check recent deployments
   - Review configuration changes
   - Analyze error patterns
   - Examine resource utilization

**Resolution**:
1. **Apply fix based on root cause**
2. **Verify service restoration**
3. **Scale back to normal operations**
4. **Disable maintenance mode**

### P1 - Degraded Performance

**Detection**: High latency (>2s p95), elevated error rate (5-15%)

**Response Process**:
1. **Immediate triage**
   ```bash
   # Check current performance metrics
   kubectl port-forward service/grafana 3000:3000
   # Access dashboard at http://localhost:3000
   
   # Identify bottlenecks
   kubectl top pods -l app=metafunction
   kubectl exec -it postgresql-0 -- \
     psql -U postgres -c "SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
   ```

2. **Resource optimization**
   ```bash
   # Scale horizontally
   kubectl patch hpa metafunction -p '{"spec":{"maxReplicas":10}}'
   
   # Restart problematic pods
   kubectl rollout restart deployment/metafunction
   
   # Clear cache if corrupted
   kubectl exec -it redis-0 -- redis-cli FLUSHALL
   ```

---

## Database Operations

### Database Migration Execution

**Pre-migration Checklist**:
- [ ] Backup completed successfully
- [ ] Migration tested in staging
- [ ] Rollback plan prepared
- [ ] Maintenance window scheduled
- [ ] Stakeholders notified

**Execution**:
```bash
# 1. Create backup
kubectl exec -it deployment/migration-controller -n database-ops -- \
  /scripts/run-migration.sh create_backup pre_migration_$(date +%Y%m%d_%H%M%S)

# 2. Run migration
kubectl exec -it deployment/migration-controller -n database-ops -- \
  /scripts/run-migration.sh add_new_feature_table schema false

# 3. Verify migration
kubectl exec -it postgresql-0 -- \
  psql -U postgres -d metafunction -c "\dt+ new_feature_table"

# 4. Update application configuration
kubectl patch configmap metafunction-config \
  -p '{"data":{"NEW_FEATURE_ENABLED":"true"}}'

# 5. Restart application
kubectl rollout restart deployment/metafunction
```

**Rollback Procedure**:
```bash
# 1. Stop application writes to new table
kubectl patch configmap metafunction-config \
  -p '{"data":{"NEW_FEATURE_ENABLED":"false"}}'

# 2. Execute rollback script
kubectl exec -it deployment/migration-controller -n database-ops -- \
  /scripts/rollback-migration.sh backup_pre_migration_20240101_120000.sql

# 3. Verify rollback
kubectl exec -it postgresql-0 -- \
  psql -U postgres -d metafunction -c "SELECT COUNT(*) FROM users;"
```

### Database Performance Tuning

**Query Performance Analysis**:
```bash
# Enable query logging
kubectl exec -it postgresql-0 -- \
  psql -U postgres -c "ALTER SYSTEM SET log_statement = 'all';"
kubectl exec -it postgresql-0 -- \
  psql -U postgres -c "SELECT pg_reload_conf();"

# Analyze slow queries
kubectl exec -it postgresql-0 -- \
  psql -U postgres -c "
  SELECT query, calls, total_time, mean_time, rows
  FROM pg_stat_statements 
  WHERE mean_time > 100
  ORDER BY total_time DESC 
  LIMIT 20;"

# Check index usage
kubectl exec -it postgresql-0 -- \
  psql -U postgres -d metafunction -c "
  SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
  FROM pg_stat_user_indexes
  WHERE idx_scan = 0;"
```

**Index Management**:
```bash
# Create index concurrently (zero-downtime)
kubectl exec -it postgresql-0 -- \
  psql -U postgres -d metafunction -c "
  CREATE INDEX CONCURRENTLY idx_users_email ON users(email);"

# Monitor index creation progress
kubectl exec -it postgresql-0 -- \
  psql -U postgres -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query
  FROM pg_stat_activity
  WHERE query LIKE '%CREATE INDEX%';"
```

---

## Deployment Operations

### Blue-Green Deployment Runbook

**Pre-deployment**:
1. **Validate new version**
   ```bash
   # Run comprehensive tests
   ./tests/e2e/full_regression_tests.py --environment staging
   
   # Security scan
   trivy image ghcr.io/org/metafunction:v1.2.3
   
   # Performance baseline
   ./tests/performance/baseline_comparison.py --new-version v1.2.3
   ```

2. **Prepare environment**
   ```bash
   # Ensure sufficient resources
   kubectl describe nodes | grep -A 5 "Allocated resources"
   
   # Verify dependencies
   kubectl get pods -l app=postgresql,app=redis -A
   ```

**Deployment Execution**:
```bash
# Execute blue-green deployment
./scripts/blue-green-deploy.sh ghcr.io/org/metafunction:v1.2.3

# Monitor deployment progress
watch kubectl get pods -l app=metafunction

# Verify health after switch
for i in {1..10}; do
  curl -f https://metafunction.com/health && echo " - OK" || echo " - FAIL"
  sleep 5
done
```

**Post-deployment Verification**:
```bash
# Business metrics validation
python scripts/validate_business_metrics.py \
  --pre-deployment-baseline /tmp/metrics_baseline.json \
  --tolerance 5%

# Security posture check
python scripts/security_posture_check.py --environment production

# Performance validation
python scripts/performance_validation.py \
  --duration 300 \
  --error-threshold 1% \
  --latency-threshold 500ms
```

### Rollback Procedures

**Immediate Rollback** (Critical Issues):
```bash
# Quick rollback to previous stable version
kubectl rollout undo deployment/metafunction

# Verify rollback
kubectl rollout status deployment/metafunction --timeout=300s

# Update external load balancer if needed
aws elbv2 modify-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/metafunction-prod \
  --health-check-path /health
```

**Gradual Rollback** (Performance Issues):
```bash
# Scale down new version gradually
kubectl patch deployment metafunction \
  -p '{"spec":{"replicas":2}}'

# Monitor impact
watch kubectl top pods -l app=metafunction

# Complete rollback if issues persist
kubectl rollout undo deployment/metafunction
```

---

## Security Operations

### Security Incident Response

**Suspected Breach Detection**:
```bash
# Check Falco alerts
kubectl logs -f daemonset/falco -n falco-system | grep -E "(CRITICAL|WARNING)"

# Review authentication logs
kubectl logs deployment/oauth-proxy | grep -E "(failed|denied|unauthorized)"

# Check network anomalies
kubectl exec -it network-monitoring-pod -- \
  netstat -tuln | grep -E ":22|:3389|:1433|:3306"
```

**Immediate Containment**:
```bash
# Isolate affected pods
kubectl label pod suspicious-pod-name isolated=true

# Apply emergency network policy
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: emergency-isolation
spec:
  podSelector:
    matchLabels:
      isolated: "true"
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
EOF

# Force password reset for affected users
kubectl exec -it deployment/user-management -- \
  python scripts/force_password_reset.py --user-list /tmp/affected_users.txt
```

### Vulnerability Management

**Regular Vulnerability Scanning**:
```bash
# Scan container images
trivy image --format table --exit-code 1 ghcr.io/org/metafunction:latest

# Scan Kubernetes manifests
trivy k8s --report summary deployment/k8s/

# Scan dependencies
trivy fs --security-checks vuln,config .

# Generate SBOM
syft packages dir:. -o json > sbom.json
grype sbom.json
```

**Patch Management**:
```bash
# List outdated packages
kubectl exec -it deployment/metafunction -- \
  pip list --outdated

# Update base image
docker pull python:3.11-slim
docker build -t metafunction:patched .

# Deploy security patches
helm upgrade metafunction deployment/helm/metafunction/ \
  --set image.tag=patched \
  --set securityContext.runAsNonRoot=true \
  --set securityContext.readOnlyRootFilesystem=true
```

---

## Performance Troubleshooting

### High CPU Usage

**Investigation**:
```bash
# Identify CPU-intensive pods
kubectl top pods --sort-by cpu -A

# Get detailed CPU metrics
kubectl exec -it high-cpu-pod -- top -p 1

# Profile application
kubectl exec -it deployment/metafunction -- \
  python -m cProfile -o /tmp/profile.stats app.py &

# Analyze profile
kubectl cp metafunction-pod:/tmp/profile.stats ./profile.stats
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative')
p.print_stats(20)
"
```

**Mitigation**:
```bash
# Horizontal scaling
kubectl patch hpa metafunction \
  -p '{"spec":{"maxReplicas":15,"targetCPUUtilizationPercentage":60}}'

# Resource limit adjustment
kubectl patch deployment metafunction \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"metafunction","resources":{"limits":{"cpu":"2000m"}}}]}}}}'

# Code optimization deployment
git checkout feature/cpu-optimization
docker build -t metafunction:optimized .
kubectl set image deployment/metafunction metafunction=metafunction:optimized
```

### Memory Leaks

**Detection and Analysis**:
```bash
# Memory usage trends
kubectl top pods --sort-by memory -A

# Memory profiling
kubectl exec -it deployment/metafunction -- \
  python -c "
import tracemalloc
import gc
tracemalloc.start()
# Application code here
current, peak = tracemalloc.get_traced_memory()
print(f'Current: {current / 1024 / 1024:.1f} MB')
print(f'Peak: {peak / 1024 / 1024:.1f} MB')
"

# Garbage collection analysis
kubectl exec -it deployment/metafunction -- \
  python -c "
import gc
print('GC stats:', gc.get_stats())
print('Unreachable objects:', gc.collect())
"
```

**Remediation**:
```bash
# Implement memory limits
kubectl patch deployment metafunction \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"metafunction","resources":{"limits":{"memory":"1Gi"},"requests":{"memory":"512Mi"}}}]}}}}'

# Enable memory monitoring
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: memory-monitoring
spec:
  selector:
    matchLabels:
      app: metafunction
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
EOF
```

### Database Performance Issues

**Query Performance**:
```bash
# Long-running queries
kubectl exec -it postgresql-0 -- \
  psql -U postgres -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query
  FROM pg_stat_activity
  WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"

# Lock analysis
kubectl exec -it postgresql-0 -- \
  psql -U postgres -c "
  SELECT blocked_locks.pid AS blocked_pid,
         blocked_activity.usename AS blocked_user,
         blocking_locks.pid AS blocking_pid,
         blocking_activity.usename AS blocking_user,
         blocked_activity.query AS blocked_statement,
         blocking_activity.query AS current_statement_in_blocking_process
  FROM pg_catalog.pg_locks blocked_locks
  JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
  JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
  JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
  WHERE NOT blocked_locks.granted;"
```

**Connection Pool Issues**:
```bash
# PgBouncer statistics
kubectl exec -it pgbouncer-0 -- \
  psql -p 6432 pgbouncer -c "SHOW POOLS; SHOW CLIENTS; SHOW SERVERS;"

# Adjust pool settings
kubectl patch configmap pgbouncer-config \
  -p '{"data":{"pgbouncer.ini":"pool_mode = transaction\nmax_client_conn = 300\ndefault_pool_size = 50"}}'

kubectl rollout restart deployment/pgbouncer
```

---

## Backup and Recovery

### Backup Verification

**Daily Verification**:
```bash
# Check Velero backup status
velero backup get --output table

# Verify backup integrity
velero backup describe daily-backup-$(date +%Y%m%d) --details

# Test backup restoration (non-destructive)
velero restore create test-restore-$(date +%Y%m%d) \
  --from-backup daily-backup-$(date +%Y%m%d) \
  --namespace-mappings default:test-restore

# Cleanup test restore
kubectl delete namespace test-restore
```

**Database Backup Verification**:
```bash
# Check database backup
kubectl exec -it deployment/backup-verification -n disaster-recovery -- \
  python /scripts/verify_backup.py \
  --backup-file /backups/postgres-backup-$(date +%Y%m%d).sql \
  --verify-schema \
  --verify-data-integrity \
  --sample-size 1000

# Verify cross-region backup replication
aws s3 ls s3://metafunction-backups-us-west/ --recursive | tail -10
```

### Disaster Recovery Drill

**Monthly DR Test**:
```bash
# Simulate regional failure
kubectl cordon node-1 node-2 node-3
kubectl drain node-1 node-2 node-3 --ignore-daemonsets --delete-emptydir-data

# Verify automatic failover
curl -f https://metafunction.com/health

# Test backup restoration in alternate region
./scripts/dr-drill.sh --region us-west-2 --backup-date $(date +%Y%m%d)

# Validate service functionality
./tests/dr/disaster_recovery_tests.py --region us-west-2

# Document results
./scripts/generate_dr_report.sh --drill-date $(date +%Y%m%d)
```

---

## Monitoring and Alerting

### Alert Investigation

**High Error Rate Alert**:
```bash
# Investigate error patterns
kubectl logs deployment/metafunction | grep ERROR | tail -100

# Check error rate metrics
curl "http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~'5..'}[5m])"

# Identify error sources
kubectl exec -it deployment/metafunction -- \
  python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Application debugging code
"
```

**Latency Alert Investigation**:
```bash
# Check response time distribution
curl "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"

# Identify slow endpoints
kubectl logs deployment/metafunction | grep -E "took|duration" | tail -50

# Database query analysis
kubectl exec -it postgresql-0 -- \
  psql -U postgres -c "SELECT query, mean_time, calls FROM pg_stat_statements WHERE mean_time > 100 ORDER BY mean_time DESC LIMIT 10;"
```

### Custom Metrics and Alerts

**Business Metrics Monitoring**:
```bash
# User engagement metrics
kubectl exec -it deployment/metafunction -- \
  python -c "
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
registry = CollectorRegistry()
active_users = Gauge('metafunction_active_users_total', 'Active users', registry=registry)
active_users.set(get_active_user_count())  # Your implementation
push_to_gateway('pushgateway:9091', job='business_metrics', registry=registry)
"

# Revenue tracking
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: revenue-monitoring
data:
  script.py: |
    import requests
    import time
    from prometheus_client import CollectorRegistry, Counter, push_to_gateway
    
    revenue_counter = Counter('metafunction_revenue_total', 'Total revenue')
    
    while True:
        current_revenue = get_current_revenue()  # Your implementation
        revenue_counter._value._value = current_revenue
        push_to_gateway('pushgateway:9091', job='revenue_metrics', registry=registry)
        time.sleep(300)  # 5 minutes
EOF
```

---

## Emergency Contact Information

### Escalation Matrix

**24/7 On-Call Rotation**:
- **Primary**: DevOps Engineer (PagerDuty)
- **Secondary**: Senior SRE (PagerDuty + Phone)
- **Escalation**: Engineering Manager (30 min delay)
- **Executive**: CTO (Critical P0 incidents)

### Emergency Procedures

**Complete Service Outage**:
1. **Immediate**: Execute automated failover
2. **5 minutes**: Manual investigation begins
3. **15 minutes**: Escalate to senior engineer
4. **30 minutes**: Escalate to management
5. **60 minutes**: External communication

**Data Breach Suspected**:
1. **Immediate**: Isolate affected systems
2. **15 minutes**: Security team notification
3. **30 minutes**: Legal team notification
4. **2 hours**: Regulatory notification (if required)
5. **24 hours**: Customer notification (if required)

---

*This runbook is a living document. Please update it as systems and procedures evolve.*
