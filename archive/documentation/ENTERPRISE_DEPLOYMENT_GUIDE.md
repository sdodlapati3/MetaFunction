# MetaFunction Enterprise Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying and managing MetaFunction in production environments with enterprise-grade features including disaster recovery, security compliance, advanced monitoring, multi-region deployment, and sophisticated CI/CD pipelines.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Security and Compliance](#security-and-compliance)
4. [Database Management](#database-management)
5. [Deployment Strategies](#deployment-strategies)
6. [Monitoring and Observability](#monitoring-and-observability)
7. [Disaster Recovery](#disaster-recovery)
8. [Multi-Region Deployment](#multi-region-deployment)
9. [Performance Optimization](#performance-optimization)
10. [CI/CD Pipeline](#cicd-pipeline)
11. [Troubleshooting](#troubleshooting)
12. [Maintenance Procedures](#maintenance-procedures)

## Prerequisites

### Software Requirements

- **Kubernetes**: v1.24+ with RBAC enabled
- **Helm**: v3.8+
- **Istio**: v1.15+ (for service mesh)
- **ArgoCD**: v2.4+ (for GitOps)
- **Prometheus**: v2.37+ (for monitoring)
- **Grafana**: v9.0+ (for dashboards)
- **Velero**: v1.9+ (for backups)

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| Memory | 8 GB | 16+ GB |
| Storage | 100 GB | 500+ GB SSD |
| Network | 1 Gbps | 10+ Gbps |

### Cloud Resources

- **Multi-AZ Kubernetes cluster**
- **PostgreSQL RDS** (Multi-AZ with read replicas)
- **Redis ElastiCache** (with clustering)
- **S3 buckets** (for backups and artifacts)
- **CloudWatch/CloudFlare** (for monitoring and CDN)
- **Route53** (for DNS and health checks)

## Infrastructure Setup

### 1. Kubernetes Cluster Setup

```bash
# Create production-ready cluster
export CLUSTER_NAME="metafunction-prod"
export REGION="us-east-1"

# EKS example
eksctl create cluster \
  --name $CLUSTER_NAME \
  --region $REGION \
  --nodegroup-name workers \
  --node-type m5.xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --with-oidc \
  --ssh-access \
  --managed
```

### 2. Core Components Installation

```bash
# Install Helm
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/

# Install Istio
curl -L https://istio.io/downloadIstio | sh -
export PATH=$PWD/istio-1.18.0/bin:$PATH
istioctl install --set values.defaultRevision=default

# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# Install Velero
kubectl apply -f deployment/k8s/disaster-recovery.yaml
```

### 3. Apply Enterprise Configurations

```bash
# Apply all enterprise configurations
kubectl apply -f deployment/k8s/security-compliance.yaml
kubectl apply -f deployment/k8s/advanced-monitoring.yaml
kubectl apply -f deployment/k8s/multi-region.yaml
kubectl apply -f deployment/k8s/performance-optimization.yaml
kubectl apply -f deployment/k8s/database-migration.yaml
```

## Security and Compliance

### SOC2 Compliance

The MetaFunction deployment includes SOC2 Type II compliance controls:

#### Access Controls (CC6.1)
- RBAC with least privilege principle
- Multi-factor authentication for admin access
- Regular access reviews and audit trails

#### System Operations (CC7.1)
- Automated security monitoring with Falco
- Vulnerability scanning with Trivy
- Network segmentation with Istio policies

#### Change Management (CC8.1)
- GitOps deployment with approval workflows
- Immutable infrastructure patterns
- Automated rollback capabilities

### GDPR Compliance

#### Data Protection
```yaml
# Data classification labels
apiVersion: v1
kind: ConfigMap
metadata:
  name: data-classification
data:
  personal_data: "encrypted_at_rest,encrypted_in_transit,audit_logged"
  sensitive_data: "restricted_access,retention_policy_applied"
```

#### Privacy Controls
- Automatic PII detection and masking
- Right to erasure implementation
- Data portability features
- Consent management integration

### Security Monitoring

```bash
# View Falco security alerts
kubectl logs -f deployment/falco -n falco-system

# Check vulnerability scan results
kubectl get vulnerabilityreports -A

# Review security policies
kubectl get networkpolicies -A
kubectl get podsecuritypolicies
```

## Database Management

### Migration Strategies

#### Zero-Downtime Migrations

```bash
# Run zero-downtime migration
kubectl exec -it deployment/migration-controller -n database-ops -- \
  /scripts/zero-downtime-migration.sh add_user_preferences

# Monitor migration progress
kubectl logs -f job/migration-add-user-preferences -n database-ops
```

#### Migration Rollback

```bash
# List available backups
kubectl exec -it deployment/migration-controller -n database-ops -- \
  ls -la /migrations/backup_*

# Rollback to specific backup
kubectl exec -it deployment/migration-controller -n database-ops -- \
  /scripts/rollback-migration.sh backup_add_user_preferences_20240101_120000.sql
```

### Database Health Checks

```bash
# Check database metrics
kubectl port-forward service/postgresql 5432:5432
psql -h localhost -U postgres -d metafunction -c "
  SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    n_tup_ins, n_tup_upd, n_tup_del
  FROM pg_stat_user_tables 
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

## Deployment Strategies

### Blue-Green Deployment

```bash
# Execute blue-green deployment
./scripts/blue-green-deploy.sh ghcr.io/org/metafunction:v1.2.3

# Monitor deployment progress
kubectl get pods -l app=metafunction -A -w

# Verify deployment
curl -f https://metafunction.com/health
```

### Canary Deployment

```bash
# Execute canary deployment
./scripts/canary-deploy.sh ghcr.io/org/metafunction:v1.2.3

# Monitor canary metrics
kubectl port-forward service/prometheus 9090:9090
# Visit http://localhost:9090 for metrics
```

### Rolling Updates (Default)

```bash
# Standard rolling update
helm upgrade metafunction deployment/helm/metafunction/ \
  --set image.tag=v1.2.3 \
  --wait --timeout=600s

# Monitor rollout
kubectl rollout status deployment/metafunction
```

## Monitoring and Observability

### Grafana Dashboards

Access Grafana at: `https://grafana.metafunction.com`

Key dashboards:
- **Application Performance**: Response times, throughput, error rates
- **Infrastructure Health**: CPU, memory, disk, network metrics  
- **Business Metrics**: User engagement, function executions, revenue
- **Security Dashboard**: Failed logins, suspicious activities, compliance status

### Distributed Tracing

```bash
# Access Jaeger UI
kubectl port-forward service/jaeger-query 16686:16686
# Visit http://localhost:16686

# Query traces programmatically
curl "http://jaeger-query:16686/api/traces?service=metafunction&limit=100"
```

### Log Aggregation

```bash
# Search application logs
kubectl logs -f deployment/metafunction --tail=100

# Query Elasticsearch logs
curl -X GET "elasticsearch:9200/metafunction-logs-*/_search" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match": {"level": "ERROR"}}}'
```

### Alerting Rules

Critical alerts configured:
- **High Error Rate**: >5% HTTP 5xx responses
- **High Latency**: >2s p95 response time
- **Pod Crashes**: Any pod restart
- **Database Issues**: Connection failures or slow queries
- **Security Events**: Unauthorized access attempts

## Disaster Recovery

### Backup Verification

```bash
# Check backup status
kubectl get backups.velero.io -A

# Verify backup integrity
kubectl exec -it deployment/backup-verification -n disaster-recovery -- \
  python /scripts/verify_backup.py --backup-name daily-backup-20240101
```

### Recovery Procedures

#### Full Cluster Recovery

```bash
# Restore from Velero backup
velero restore create --from-backup cluster-backup-20240101

# Monitor restoration
velero restore describe cluster-restore-20240101

# Verify application functionality
./tests/smoke/production_smoke_tests.py --url https://metafunction.com
```

#### Database Point-in-Time Recovery

```bash
# Restore database to specific timestamp
kubectl exec -it deployment/database-recovery -n disaster-recovery -- \
  /scripts/restore_database.sh "2024-01-01 12:00:00"

# Verify data integrity
kubectl exec -it deployment/postgresql -- \
  psql -U postgres -d metafunction -c "SELECT COUNT(*) FROM users;"
```

### Recovery Testing

```bash
# Schedule disaster recovery drill
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: dr-drill
  namespace: disaster-recovery
spec:
  schedule: "0 2 1 * *"  # Monthly at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: dr-test
            image: metafunction/dr-tools:latest
            command: ["/scripts/dr_drill.sh"]
          restartPolicy: OnFailure
EOF
```

## Multi-Region Deployment

### Global Load Balancer Configuration

```bash
# Configure global load balancer
kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: global-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: metafunction-tls
    hosts:
    - metafunction.com
    - "*.metafunction.com"
EOF
```

### Cross-Region Database Replication

```bash
# Check replication status
kubectl exec -it postgresql-primary -- \
  psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# Verify replica lag
kubectl exec -it postgresql-replica-us-west -- \
  psql -U postgres -c "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()));"
```

### Regional Failover

```bash
# Manual failover to us-west region
kubectl patch service metafunction-global \
  -p '{"spec":{"selector":{"region":"us-west"}}}'

# Verify failover
curl -H "Host: metafunction.com" https://us-west.metafunction.com/health
```

## Performance Optimization

### Cache Management

```bash
# Monitor Redis cache performance
kubectl exec -it redis-cluster-0 -- redis-cli INFO memory

# Clear cache if needed
kubectl exec -it redis-cluster-0 -- redis-cli FLUSHALL

# Warm cache with critical data
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: cache-warming
spec:
  template:
    spec:
      containers:
      - name: cache-warmer
        image: metafunction:latest
        command: ["/scripts/warm_cache.py"]
      restartPolicy: Never
EOF
```

### Database Connection Pooling

```bash
# Monitor PgBouncer connections
kubectl exec -it pgbouncer-0 -- \
  psql -p 6432 pgbouncer -c "SHOW POOLS;"

# Adjust pool size if needed
kubectl patch configmap pgbouncer-config \
  -p '{"data":{"pgbouncer.ini":"[databases]\nmetafunction = host=postgresql port=5432 dbname=metafunction\n[pgbouncer]\npool_mode = transaction\nmax_client_conn = 200\ndefault_pool_size = 30"}}'
```

### Auto-scaling Configuration

```bash
# Check HPA status
kubectl get hpa metafunction

# Adjust scaling parameters
kubectl patch hpa metafunction \
  -p '{"spec":{"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":70}}}]}}'
```

## CI/CD Pipeline

### GitHub Actions Setup

1. **Configure Secrets**:
   ```bash
   # Required secrets in GitHub repository
   KUBECONFIG_STAGING
   KUBECONFIG_PRODUCTION  
   AWS_ACCESS_KEY_ID
   AWS_SECRET_ACCESS_KEY
   GITHUB_TOKEN
   SLACK_WEBHOOK
   ```

2. **Trigger Deployment**:
   ```bash
   # Manual deployment trigger
   gh workflow run enhanced-ci-cd.yaml \
     -f deploy_environment=production \
     -f deployment_strategy=blue-green
   ```

### Pipeline Monitoring

```bash
# Check workflow status
gh run list --workflow=enhanced-ci-cd.yaml

# View specific run logs
gh run view <run-id>

# Download artifacts
gh run download <run-id>
```

## Troubleshooting

### Common Issues

#### Pod Startup Issues
```bash
# Check pod events
kubectl describe pod <pod-name>

# View pod logs
kubectl logs <pod-name> --previous

# Debug container
kubectl exec -it <pod-name> -- /bin/sh
```

#### Database Connection Issues
```bash
# Test database connectivity
kubectl exec -it deployment/metafunction -- \
  python -c "
import psycopg2
conn = psycopg2.connect(
    host='postgresql.default.svc.cluster.local',
    database='metafunction', 
    user='metafunction',
    password='password'
)
print('Connection successful')
"
```

#### Network Policy Issues
```bash
# Check network policies
kubectl get networkpolicies -A

# Test connectivity between pods
kubectl exec -it pod1 -- nc -zv pod2-service 80
```

### Performance Debugging

```bash
# Application performance profiling
kubectl exec -it deployment/metafunction -- \
  python -m cProfile -o profile.stats app.py

# Database query analysis
kubectl exec -it postgresql-0 -- \
  psql -U postgres -d metafunction -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

### Security Investigation

```bash
# Check Falco alerts
kubectl logs -f daemonset/falco -n falco-system | grep CRITICAL

# Review audit logs
kubectl logs -f deployment/audit-logger -n kube-system

# Investigate suspicious network traffic
kubectl exec -it network-monitoring-pod -- \
  tcpdump -i any -w /tmp/capture.pcap host suspicious-ip
```

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily
- Monitor application health dashboards
- Review error logs and alerts
- Check backup completion status
- Verify certificate expiration dates

#### Weekly  
- Review security scan results
- Update dependency vulnerabilities
- Analyze performance metrics trends
- Test disaster recovery procedures

#### Monthly
- Rotate access credentials
- Review and update security policies
- Conduct penetration testing
- Update documentation

### Planned Maintenance Windows

```bash
# Schedule maintenance mode
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: maintenance-mode
data:
  enabled: "true"
  message: "System maintenance in progress. Please try again later."
  estimated_duration: "2 hours"
EOF

# Scale down application
kubectl scale deployment metafunction --replicas=0

# Perform maintenance tasks
./scripts/maintenance/update_database_schema.sh
./scripts/maintenance/cleanup_old_logs.sh
./scripts/maintenance/update_certificates.sh

# Scale back up
kubectl scale deployment metafunction --replicas=3

# Disable maintenance mode
kubectl patch configmap maintenance-mode \
  -p '{"data":{"enabled":"false"}}'
```

### Backup and Archive Procedures

```bash
# Create on-demand backup
velero backup create manual-backup-$(date +%Y%m%d) \
  --include-namespaces default,monitoring,istio-system

# Archive old logs
kubectl exec -it deployment/log-archiver -- \
  /scripts/archive_logs.sh --older-than 90d --destination s3://metafunction-archives/

# Clean up old container images
kubectl exec -it deployment/image-cleaner -- \
  /scripts/cleanup_images.sh --keep-latest 5
```

## Support and Escalation

### Contact Information

- **L1 Support**: support@metafunction.com
- **L2 Engineering**: engineering@metafunction.com  
- **Security Incidents**: security@metafunction.com
- **Emergency Hotline**: +1-555-METAFUNC

### Escalation Matrix

| Severity | Response Time | Escalation Path |
|----------|---------------|-----------------|
| P0 (Critical) | 15 minutes | DevOps → Engineering → CTO |
| P1 (High) | 1 hour | Support → DevOps → Engineering |
| P2 (Medium) | 4 hours | Support → DevOps |
| P3 (Low) | 24 hours | Support |

### Emergency Procedures

```bash
# Immediate incident response
./scripts/incident/emergency_scale_down.sh
./scripts/incident/enable_maintenance_mode.sh
./scripts/incident/notify_stakeholders.sh

# Post-incident analysis
./scripts/incident/collect_logs.sh incident-$(date +%Y%m%d)
./scripts/incident/generate_timeline.sh
./scripts/incident/create_postmortem.sh
```

---

For additional support or questions, please refer to the [MetaFunction Documentation](https://docs.metafunction.com) or contact our support team.
