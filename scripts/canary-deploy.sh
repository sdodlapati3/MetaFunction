#!/bin/bash
# Canary Deployment Script for MetaFunction
# Gradually shifts traffic to new version with automated rollback on issues

set -euo pipefail

# Configuration
NAMESPACE="production"
APP_NAME="metafunction"
NEW_IMAGE="$1"
CANARY_STEPS=(10 25 50 75 100)  # Traffic percentages for canary steps
STEP_DURATION=300  # 5 minutes per step
HEALTH_CHECK_INTERVAL=30
ERROR_THRESHOLD=5  # Percentage of errors that triggers rollback
LATENCY_THRESHOLD=2000  # Milliseconds - latency threshold

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    for tool in kubectl helm curl jq; do
        if ! command -v $tool &> /dev/null; then
            error "$tool is not installed or not in PATH"
            exit 1
        fi
    done
    
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        error "Namespace $NAMESPACE does not exist"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Create canary deployment
create_canary_deployment() {
    log "Creating canary deployment..."
    
    # Deploy canary version
    helm upgrade --install "${APP_NAME}-canary" deployment/helm/metafunction/ \
        --namespace "$NAMESPACE" \
        --set image.repository="$(echo $NEW_IMAGE | cut -d: -f1)" \
        --set image.tag="$(echo $NEW_IMAGE | cut -d: -f2)" \
        --set nameOverride="${APP_NAME}-canary" \
        --set fullnameOverride="${APP_NAME}-canary" \
        --set service.name="${APP_NAME}-canary" \
        --set replicaCount=1 \
        --set resources.requests.memory="256Mi" \
        --set resources.requests.cpu="100m" \
        --set labels.version="canary" \
        --wait --timeout=600s
    
    success "Canary deployment created"
}

# Create Istio virtual service for traffic splitting
create_virtual_service() {
    local canary_weight=$1
    local stable_weight=$((100 - canary_weight))
    
    log "Creating Istio VirtualService with $canary_weight% canary traffic"
    
    cat <<EOF | kubectl apply -f -
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: ${APP_NAME}-traffic-split
  namespace: $NAMESPACE
spec:
  hosts:
  - ${APP_NAME}
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: ${APP_NAME}-canary
        port:
          number: 80
      weight: 100
  - route:
    - destination:
        host: ${APP_NAME}
        port:
          number: 80
      weight: $stable_weight
    - destination:
        host: ${APP_NAME}-canary
        port:
          number: 80
      weight: $canary_weight
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: ${APP_NAME}-destination-rule
  namespace: $NAMESPACE
spec:
  host: ${APP_NAME}
  subsets:
  - name: stable
    labels:
      version: stable
  - name: canary
    labels:
      version: canary
EOF
    
    success "Traffic split configured: $stable_weight% stable, $canary_weight% canary"
}

# Get metrics from Prometheus
get_metrics() {
    local service_name=$1
    local duration=$2  # in minutes
    
    local prometheus_url="http://prometheus.monitoring.svc.cluster.local:9090"
    local end_time=$(date +%s)
    local start_time=$((end_time - duration * 60))
    
    # Error rate query
    local error_rate_query="rate(http_requests_total{service=\"$service_name\",status=~\"5..\"}[5m]) / rate(http_requests_total{service=\"$service_name\"}[5m]) * 100"
    local error_rate=$(curl -s "${prometheus_url}/api/v1/query?query=${error_rate_query}&time=${end_time}" | jq -r '.data.result[0].value[1] // "0"')
    
    # Latency query (95th percentile)
    local latency_query="histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service=\"$service_name\"}[5m])) * 1000"
    local latency=$(curl -s "${prometheus_url}/api/v1/query?query=${latency_query}&time=${end_time}" | jq -r '.data.result[0].value[1] // "0"')
    
    echo "$error_rate,$latency"
}

# Monitor canary deployment
monitor_canary() {
    local weight=$1
    local duration=$2
    
    log "Monitoring canary deployment for $duration seconds (${weight}% traffic)"
    
    local start_time=$(date +%s)
    local end_time=$((start_time + duration))
    local check_count=0
    local error_count=0
    
    while [ $(date +%s) -lt $end_time ]; do
        # Get metrics for both stable and canary
        local stable_metrics=$(get_metrics "${APP_NAME}" 5)
        local canary_metrics=$(get_metrics "${APP_NAME}-canary" 5)
        
        local stable_error_rate=$(echo $stable_metrics | cut -d, -f1)
        local stable_latency=$(echo $stable_metrics | cut -d, -f2)
        local canary_error_rate=$(echo $canary_metrics | cut -d, -f1)
        local canary_latency=$(echo $canary_metrics | cut -d, -f2)
        
        # Check if we have valid metrics
        if [[ "$canary_error_rate" != "0" ]] && [[ "$canary_latency" != "0" ]]; then
            log "Stable - Error rate: ${stable_error_rate}%, Latency: ${stable_latency}ms"
            log "Canary - Error rate: ${canary_error_rate}%, Latency: ${canary_latency}ms"
            
            # Check error rate threshold
            if (( $(echo "$canary_error_rate > $ERROR_THRESHOLD" | bc -l) )); then
                error "Canary error rate (${canary_error_rate}%) exceeds threshold (${ERROR_THRESHOLD}%)"
                return 1
            fi
            
            # Check latency threshold
            if (( $(echo "$canary_latency > $LATENCY_THRESHOLD" | bc -l) )); then
                error "Canary latency (${canary_latency}ms) exceeds threshold (${LATENCY_THRESHOLD}ms)"
                return 1
            fi
            
            # Compare with stable version (canary should not be significantly worse)
            if (( $(echo "$canary_error_rate > $stable_error_rate * 2" | bc -l) )); then
                error "Canary error rate is significantly higher than stable version"
                return 1
            fi
            
            if (( $(echo "$canary_latency > $stable_latency * 1.5" | bc -l) )); then
                error "Canary latency is significantly higher than stable version"
                return 1
            fi
        fi
        
        # Health check
        if kubectl get pods -l app.kubernetes.io/name="${APP_NAME}",version=canary -n "$NAMESPACE" -o jsonpath='{.items[*].status.phase}' | grep -q "Running"; then
            log "✓ Canary pods are running"
        else
            warning "✗ Some canary pods are not running"
            ((error_count++))
        fi
        
        ((check_count++))
        
        # If too many consecutive failures, fail the deployment
        if [ $error_count -gt 3 ]; then
            error "Too many consecutive health check failures"
            return 1
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
    done
    
    success "Monitoring completed successfully for ${weight}% traffic"
    return 0
}

# Run canary validation tests
run_canary_tests() {
    log "Running canary-specific validation tests..."
    
    local test_job_name="${APP_NAME}-canary-validation-$(date +%Y%m%d-%H%M%S)"
    
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
      - name: canary-tests
        image: python:3.11-slim
        command:
        - /bin/sh
        - -c
        - |
          pip install requests pytest
          python -c "
          import requests
          import sys
          import json
          
          # Test canary endpoint directly
          canary_url = 'http://${APP_NAME}-canary.${NAMESPACE}.svc.cluster.local'
          
          # Health check
          response = requests.get(f'{canary_url}/health')
          assert response.status_code == 200, f'Canary health check failed: {response.status_code}'
          
          # API functionality test
          response = requests.get(f'{canary_url}/api/v1/functions')
          assert response.status_code == 200, f'Canary API test failed: {response.status_code}'
          
          # Test with canary header through main service
          main_url = 'http://${APP_NAME}.${NAMESPACE}.svc.cluster.local'
          headers = {'canary': 'true'}
          response = requests.get(f'{main_url}/health', headers=headers)
          assert response.status_code == 200, f'Canary header routing failed: {response.status_code}'
          
          print('All canary validation tests passed')
          "
EOF

    kubectl wait --for=condition=complete job/"$test_job_name" -n "$NAMESPACE" --timeout=180s
    
    local job_status=$(kubectl get job "$test_job_name" -n "$NAMESPACE" -o jsonpath='{.status.conditions[0].type}')
    kubectl delete job "$test_job_name" -n "$NAMESPACE"
    
    if [ "$job_status" = "Complete" ]; then
        success "Canary validation tests passed"
        return 0
    else
        error "Canary validation tests failed"
        return 1
    fi
}

# Rollback canary deployment
rollback_canary() {
    error "Rolling back canary deployment..."
    
    # Remove traffic split (100% to stable)
    create_virtual_service 0
    
    # Scale down canary
    kubectl scale deployment "${APP_NAME}-canary" -n "$NAMESPACE" --replicas=0
    
    # Clean up canary resources
    helm uninstall "${APP_NAME}-canary" -n "$NAMESPACE" || true
    kubectl delete virtualservice "${APP_NAME}-traffic-split" -n "$NAMESPACE" || true
    kubectl delete destinationrule "${APP_NAME}-destination-rule" -n "$NAMESPACE" || true
    
    error "Canary deployment rolled back"
}

# Promote canary to stable
promote_canary() {
    log "Promoting canary to stable..."
    
    # Scale up canary to match stable replica count
    local stable_replicas=$(kubectl get deployment "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
    kubectl scale deployment "${APP_NAME}-canary" -n "$NAMESPACE" --replicas="$stable_replicas"
    
    # Wait for canary to scale up
    kubectl wait --for=condition=available deployment/"${APP_NAME}-canary" -n "$NAMESPACE" --timeout=300s
    
    # Update stable deployment with new image
    helm upgrade "$APP_NAME" deployment/helm/metafunction/ \
        --namespace "$NAMESPACE" \
        --set image.repository="$(echo $NEW_IMAGE | cut -d: -f1)" \
        --set image.tag="$(echo $NEW_IMAGE | cut -d: -f2)" \
        --wait --timeout=600s
    
    # Remove traffic split
    kubectl delete virtualservice "${APP_NAME}-traffic-split" -n "$NAMESPACE" || true
    kubectl delete destinationrule "${APP_NAME}-destination-rule" -n "$NAMESPACE" || true
    
    # Clean up canary deployment
    helm uninstall "${APP_NAME}-canary" -n "$NAMESPACE"
    
    success "Canary promoted to stable"
}

# Main canary deployment function
main() {
    if [ $# -eq 0 ]; then
        error "Usage: $0 <new-image>"
        error "Example: $0 myregistry.com/metafunction:v1.2.3"
        exit 1
    fi
    
    log "Starting Canary deployment for MetaFunction"
    log "New image: $NEW_IMAGE"
    
    # Check prerequisites
    check_prerequisites
    
    # Install bc for arithmetic operations
    if ! command -v bc &> /dev/null; then
        warning "Installing bc for arithmetic operations..."
        if command -v apt-get &> /dev/null; then
            apt-get update && apt-get install -y bc
        elif command -v yum &> /dev/null; then
            yum install -y bc
        fi
    fi
    
    # Set trap for cleanup on error
    trap 'error "Canary deployment failed! Rolling back..."; rollback_canary; exit 1' ERR
    
    # Step 1: Create canary deployment
    create_canary_deployment
    
    # Step 2: Run initial canary tests
    if ! run_canary_tests; then
        error "Initial canary tests failed"
        exit 1
    fi
    
    # Step 3: Gradual traffic shift
    for weight in "${CANARY_STEPS[@]}"; do
        log "=== Canary Step: ${weight}% traffic to canary ==="
        
        # Update traffic split
        create_virtual_service $weight
        
        # Monitor this step
        if ! monitor_canary $weight $STEP_DURATION; then
            error "Monitoring failed at ${weight}% traffic"
            exit 1
        fi
        
        # Prompt for continuation (except for final step)
        if [ $weight -ne 100 ]; then
            read -p "Continue to next step? (Y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Nn]$ ]]; then
                log "Deployment paused by user"
                exit 0
            fi
        fi
    done
    
    # Step 4: Final validation at 100% traffic
    log "Running final validation with 100% canary traffic..."
    if ! run_canary_tests; then
        error "Final validation failed"
        exit 1
    fi
    
    # Step 5: Promote canary to stable
    promote_canary
    
    success "Canary deployment completed successfully!"
    
    # Remove error trap
    trap - ERR
}

# Handle script interruption
trap 'error "Canary deployment interrupted!"; rollback_canary; exit 130' INT TERM

# Run main function
main "$@"
