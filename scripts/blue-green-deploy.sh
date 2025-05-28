#!/bin/bash
# Blue-Green Deployment Script for MetaFunction
# Provides zero-downtime deployments with instant rollback capability

set -euo pipefail

# Configuration
NAMESPACE="production"
APP_NAME="metafunction"
NEW_IMAGE="$1"
HEALTH_CHECK_TIMEOUT=300
VALIDATION_TIMEOUT=180

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check if required tools are available
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v helm &> /dev/null; then
        error "helm is not installed or not in PATH"
        exit 1
    fi
    
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        error "Namespace $NAMESPACE does not exist"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Get current active environment (blue or green)
get_active_environment() {
    local active_selector=$(kubectl get service "${APP_NAME}" -n "$NAMESPACE" -o jsonpath='{.spec.selector.environment}' 2>/dev/null || echo "")
    
    if [ "$active_selector" = "blue" ]; then
        echo "blue"
    elif [ "$active_selector" = "green" ]; then
        echo "green"
    else
        # Default to blue if no active environment
        echo "blue"
    fi
}

# Get inactive environment
get_inactive_environment() {
    local active=$(get_active_environment)
    if [ "$active" = "blue" ]; then
        echo "green"
    else
        echo "blue"
    fi
}

# Create database backup before deployment
create_backup() {
    log "Creating database backup..."
    
    local backup_job_name="${APP_NAME}-backup-$(date +%Y%m%d-%H%M%S)"
    
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: $backup_job_name
  namespace: $NAMESPACE
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: backup
        image: postgres:15-alpine
        command:
        - /bin/sh
        - -c
        - |
          pg_dump -h \$POSTGRES_HOST -U \$POSTGRES_USER -d \$POSTGRES_DB > /backup/\${BACKUP_NAME}.sql
        env:
        - name: POSTGRES_HOST
          value: "postgresql.${NAMESPACE}.svc.cluster.local"
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgresql-credentials
              key: username
        - name: POSTGRES_DB
          value: "metafunction"
        - name: BACKUP_NAME
          value: "${backup_job_name}"
        - name: PGPASSWORD
          valueFrom:
            secretKeyRef:
              name: postgresql-credentials
              key: password
        volumeMounts:
        - name: backup-storage
          mountPath: /backup
      volumes:
      - name: backup-storage
        persistentVolumeClaim:
          claimName: backup-storage
EOF

    kubectl wait --for=condition=complete job/"$backup_job_name" -n "$NAMESPACE" --timeout=600s
    success "Database backup completed: $backup_job_name"
}

# Deploy to inactive environment
deploy_to_inactive() {
    local inactive_env=$(get_inactive_environment)
    local deployment_name="${APP_NAME}-${inactive_env}"
    
    log "Deploying to inactive environment: $inactive_env"
    
    # Update the inactive deployment
    helm upgrade --install "$deployment_name" deployment/helm/metafunction/ \
        --namespace "$NAMESPACE" \
        --set image.repository="$(echo $NEW_IMAGE | cut -d: -f1)" \
        --set image.tag="$(echo $NEW_IMAGE | cut -d: -f2)" \
        --set nameOverride="${APP_NAME}-${inactive_env}" \
        --set fullnameOverride="${APP_NAME}-${inactive_env}" \
        --set service.name="${APP_NAME}-${inactive_env}" \
        --set environment="$inactive_env" \
        --set deployment.strategy.type="RollingUpdate" \
        --set deployment.strategy.rollingUpdate.maxUnavailable=0 \
        --set deployment.strategy.rollingUpdate.maxSurge=1 \
        --wait --timeout=600s
    
    success "Deployment to $inactive_env environment completed"
}

# Health check for the inactive environment
health_check() {
    local inactive_env=$(get_inactive_environment)
    local service_name="${APP_NAME}-${inactive_env}"
    
    log "Performing health checks on $inactive_env environment..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name="$APP_NAME",environment="$inactive_env" -n "$NAMESPACE" --timeout="${HEALTH_CHECK_TIMEOUT}s"
    
    # Port forward for testing
    kubectl port-forward service/"$service_name" 8080:80 -n "$NAMESPACE" &
    local port_forward_pid=$!
    
    # Cleanup function
    cleanup_port_forward() {
        kill $port_forward_pid 2>/dev/null || true
    }
    trap cleanup_port_forward EXIT
    
    sleep 5  # Wait for port forward to establish
    
    # Perform health checks
    local health_check_url="http://localhost:8080/health"
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_check_url" > /dev/null; then
            success "Health check passed on attempt $attempt"
            cleanup_port_forward
            return 0
        fi
        
        log "Health check attempt $attempt/$max_attempts failed, retrying..."
        sleep 10
        ((attempt++))
    done
    
    error "Health checks failed after $max_attempts attempts"
    cleanup_port_forward
    return 1
}

# Run validation tests
run_validation_tests() {
    local inactive_env=$(get_inactive_environment)
    local service_name="${APP_NAME}-${inactive_env}"
    
    log "Running validation tests on $inactive_env environment..."
    
    # Create a test job
    local test_job_name="${APP_NAME}-validation-$(date +%Y%m%d-%H%M%S)"
    
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: $test_job_name
  namespace: $NAMESPACE
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: validation-tests
        image: python:3.11-slim
        command:
        - /bin/sh
        - -c
        - |
          pip install requests pytest
          python -c "
          import requests
          import sys
          import time
          
          # Test basic functionality
          response = requests.get('http://${service_name}.${NAMESPACE}.svc.cluster.local/health')
          assert response.status_code == 200, f'Health check failed: {response.status_code}'
          
          # Test API endpoints
          response = requests.get('http://${service_name}.${NAMESPACE}.svc.cluster.local/api/v1/functions')
          assert response.status_code == 200, f'API test failed: {response.status_code}'
          
          print('All validation tests passed')
          "
EOF

    kubectl wait --for=condition=complete job/"$test_job_name" -n "$NAMESPACE" --timeout="${VALIDATION_TIMEOUT}s"
    
    # Check if job completed successfully
    local job_status=$(kubectl get job "$test_job_name" -n "$NAMESPACE" -o jsonpath='{.status.conditions[0].type}')
    if [ "$job_status" = "Complete" ]; then
        success "Validation tests passed"
        kubectl delete job "$test_job_name" -n "$NAMESPACE"
        return 0
    else
        error "Validation tests failed"
        kubectl logs job/"$test_job_name" -n "$NAMESPACE"
        kubectl delete job "$test_job_name" -n "$NAMESPACE"
        return 1
    fi
}

# Switch traffic to new environment
switch_traffic() {
    local inactive_env=$(get_inactive_environment)
    local active_env=$(get_active_environment)
    
    log "Switching traffic from $active_env to $inactive_env..."
    
    # Update the main service to point to the new environment
    kubectl patch service "$APP_NAME" -n "$NAMESPACE" -p "{\"spec\":{\"selector\":{\"environment\":\"$inactive_env\"}}}"
    
    # Wait for service to update
    sleep 10
    
    # Verify the switch
    local current_selector=$(kubectl get service "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.environment}')
    if [ "$current_selector" = "$inactive_env" ]; then
        success "Traffic successfully switched to $inactive_env environment"
        return 0
    else
        error "Failed to switch traffic to $inactive_env environment"
        return 1
    fi
}

# Monitor new environment after traffic switch
monitor_deployment() {
    log "Monitoring new deployment for 5 minutes..."
    
    local start_time=$(date +%s)
    local monitor_duration=300  # 5 minutes
    local check_interval=30
    
    while [ $(($(date +%s) - start_time)) -lt $monitor_duration ]; do
        # Check pod status
        local ready_pods=$(kubectl get pods -l app.kubernetes.io/name="$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | tr ' ' '\n' | grep -c "True" || echo "0")
        local total_pods=$(kubectl get pods -l app.kubernetes.io/name="$APP_NAME" -n "$NAMESPACE" --no-headers | wc -l)
        
        # Check service health
        if curl -f -s "http://localhost:8080/health" > /dev/null 2>&1; then
            log "✓ Health check passed - Ready pods: $ready_pods/$total_pods"
        else
            warning "✗ Health check failed - Ready pods: $ready_pods/$total_pods"
        fi
        
        sleep $check_interval
    done
    
    success "Monitoring completed successfully"
}

# Cleanup old environment
cleanup_old_environment() {
    local old_env=$(get_inactive_environment)  # This is now the old environment after switch
    local deployment_name="${APP_NAME}-${old_env}"
    
    log "Cleaning up old environment: $old_env"
    
    # Scale down old deployment
    kubectl scale deployment "$deployment_name" -n "$NAMESPACE" --replicas=0
    
    # Optionally delete old deployment (commented out for safety)
    # helm uninstall "$deployment_name" -n "$NAMESPACE"
    
    success "Old environment $old_env scaled down"
}

# Rollback function
rollback() {
    local current_active=$(get_active_environment)
    local rollback_to=$(get_inactive_environment)
    
    warning "Initiating rollback from $current_active to $rollback_to..."
    
    # Switch traffic back
    kubectl patch service "$APP_NAME" -n "$NAMESPACE" -p "{\"spec\":{\"selector\":{\"environment\":\"$rollback_to\"}}}"
    
    success "Rollback completed - traffic switched back to $rollback_to"
}

# Main deployment function
main() {
    if [ $# -eq 0 ]; then
        error "Usage: $0 <new-image>"
        error "Example: $0 myregistry.com/metafunction:v1.2.3"
        exit 1
    fi
    
    log "Starting Blue-Green deployment for MetaFunction"
    log "New image: $NEW_IMAGE"
    
    # Check prerequisites
    check_prerequisites
    
    # Show current state
    local active_env=$(get_active_environment)
    local inactive_env=$(get_inactive_environment)
    log "Current active environment: $active_env"
    log "Deploying to inactive environment: $inactive_env"
    
    # Set trap for cleanup on error
    trap 'error "Deployment failed! Check logs above."; exit 1' ERR
    
    # Step 1: Create backup
    create_backup
    
    # Step 2: Deploy to inactive environment
    deploy_to_inactive
    
    # Step 3: Health checks
    if ! health_check; then
        error "Health checks failed, aborting deployment"
        exit 1
    fi
    
    # Step 4: Validation tests
    if ! run_validation_tests; then
        error "Validation tests failed, aborting deployment"
        exit 1
    fi
    
    # Step 5: Switch traffic
    if ! switch_traffic; then
        error "Failed to switch traffic, rolling back"
        rollback
        exit 1
    fi
    
    # Step 6: Monitor deployment
    monitor_deployment
    
    # Step 7: Cleanup old environment (optional)
    read -p "Do you want to scale down the old environment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup_old_environment
    fi
    
    success "Blue-Green deployment completed successfully!"
    success "Active environment is now: $(get_active_environment)"
    
    # Remove error trap
    trap - ERR
}

# Handle script interruption
trap 'error "Deployment interrupted!"; exit 130' INT TERM

# Run main function
main "$@"
