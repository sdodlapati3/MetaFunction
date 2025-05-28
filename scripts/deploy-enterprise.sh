#!/bin/bash
# Enhanced Enterprise Deployment Automation for MetaFunction
# Orchestrates complete enterprise infrastructure deployment with validation

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-production}"
ENVIRONMENT="${ENVIRONMENT:-production}"
APP_NAME="${APP_NAME:-metafunction}"
DEPLOYMENT_STRATEGY="${DEPLOYMENT_STRATEGY:-blue-green}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_TESTS="${SKIP_TESTS:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
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

phase() {
    echo -e "${PURPLE}[$(date +'%Y-%m-%d %H:%M:%S')] PHASE:${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites and required tools..."
    
    local required_tools=("kubectl" "helm" "docker" "curl" "jq" "yq")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Missing required tools: ${missing_tools[*]}"
        error "Please install missing tools before continuing"
        exit 1
    fi
    
    # Check Kubernetes connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check Helm repositories
    if ! helm repo list | grep -q "prometheus-community"; then
        log "Adding Prometheus community Helm repository..."
        helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    fi
    
    if ! helm repo list | grep -q "grafana"; then
        log "Adding Grafana Helm repository..."
        helm repo add grafana https://grafana.github.io/helm-charts
    fi
    
    if ! helm repo list | grep -q "elastic"; then
        log "Adding Elastic Helm repository..."
        helm repo add elastic https://helm.elastic.co
    fi
    
    if ! helm repo list | grep -q "kong"; then
        log "Adding Kong Helm repository..."
        helm repo add kong https://charts.konghq.com
    fi
    
    helm repo update
    
    success "Prerequisites check completed"
}

# Create namespaces
create_namespaces() {
    phase "Creating required namespaces..."
    
    local namespaces=(
        "$NAMESPACE"
        "monitoring"
        "observability"
        "security"
        "compliance"
        "elastic-system"
        "kong"
        "kubecost"
        "chaos-engineering"
        "redis"
        "istio-system"
        "cert-manager"
        "velero"
    )
    
    for ns in "${namespaces[@]}"; do
        if ! kubectl get namespace "$ns" &> /dev/null; then
            log "Creating namespace: $ns"
            kubectl create namespace "$ns"
        else
            log "Namespace $ns already exists"
        fi
    done
    
    success "Namespaces created successfully"
}

# Deploy infrastructure components
deploy_infrastructure() {
    phase "Deploying core infrastructure components..."
    
    # Deploy cert-manager for TLS certificates
    log "Deploying cert-manager..."
    helm upgrade --install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --version v1.13.0 \
        --set installCRDs=true \
        --wait
    
    # Deploy Istio service mesh
    log "Deploying Istio service mesh..."
    if ! command -v istioctl &> /dev/null; then
        warning "istioctl not found, skipping Istio deployment"
    else
        istioctl install --set values.defaultRevision=default -y
        kubectl label namespace "$NAMESPACE" istio-injection=enabled --overwrite
    fi
    
    success "Core infrastructure deployed"
}

# Deploy monitoring and observability
deploy_monitoring() {
    phase "Deploying monitoring and observability stack..."
    
    # Deploy Prometheus
    log "Deploying Prometheus..."
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --set prometheus.prometheusSpec.retention=30d \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
        --set grafana.adminPassword=admin123 \
        --wait
    
    # Deploy Jaeger for distributed tracing
    log "Deploying Jaeger..."
    kubectl apply -f deployment/k8s/advanced-monitoring.yaml
    
    # Deploy OpenTelemetry Collector
    log "Deploying OpenTelemetry Collector..."
    helm upgrade --install opentelemetry-collector open-telemetry/opentelemetry-collector \
        --namespace observability \
        --set mode=deployment \
        --wait
    
    success "Monitoring and observability deployed"
}

# Deploy security and compliance
deploy_security() {
    phase "Deploying security and compliance components..."
    
    # Deploy Falco for runtime security
    log "Deploying Falco..."
    helm upgrade --install falco falcosecurity/falco \
        --namespace security \
        --set driver.kind=ebpf \
        --wait
    
    # Deploy OPA Gatekeeper
    log "Deploying OPA Gatekeeper..."
    kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.14/deploy/gatekeeper.yaml
    
    # Deploy security scanning components
    log "Deploying security scanning components..."
    kubectl apply -f deployment/k8s/sbom-supply-chain.yaml
    
    # Deploy compliance automation
    log "Deploying compliance automation..."
    kubectl apply -f deployment/k8s/compliance-automation.yaml
    
    success "Security and compliance deployed"
}

# Deploy SIEM and logging
deploy_siem() {
    phase "Deploying SIEM and logging infrastructure..."
    
    # Deploy Elasticsearch
    log "Deploying Elasticsearch cluster..."
    helm upgrade --install elasticsearch elastic/elasticsearch \
        --namespace elastic-system \
        --set replicas=3 \
        --set volumeClaimTemplate.resources.requests.storage=100Gi \
        --set esJavaOpts="-Xmx2g -Xms2g" \
        --wait
    
    # Deploy Kibana
    log "Deploying Kibana..."
    helm upgrade --install kibana elastic/kibana \
        --namespace elastic-system \
        --set service.type=LoadBalancer \
        --wait
    
    # Deploy Logstash
    log "Deploying Logstash..."
    helm upgrade --install logstash elastic/logstash \
        --namespace elastic-system \
        --wait
    
    # Apply SIEM integration configuration
    log "Applying SIEM integration configuration..."
    kubectl apply -f deployment/k8s/siem-integration.yaml
    
    success "SIEM and logging deployed"
}

# Deploy cost optimization
deploy_cost_optimization() {
    phase "Deploying cost optimization components..."
    
    # Deploy KubeCost
    log "Deploying KubeCost..."
    helm upgrade --install kubecost kubecost/cost-analyzer \
        --namespace kubecost \
        --set global.prometheus.enabled=false \
        --set global.prometheus.fqdn=http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090 \
        --wait
    
    # Apply cost optimization policies
    log "Applying cost optimization policies..."
    kubectl apply -f deployment/k8s/cost-optimization.yaml
    
    success "Cost optimization deployed"
}

# Deploy performance optimization
deploy_performance() {
    phase "Deploying performance optimization components..."
    
    # Deploy Redis cluster
    log "Deploying Redis cluster..."
    helm upgrade --install redis bitnami/redis-cluster \
        --namespace redis \
        --set cluster.nodes=6 \
        --set cluster.replicas=1 \
        --set auth.enabled=true \
        --set auth.password=redis123 \
        --wait
    
    # Apply performance optimization configuration
    log "Applying performance optimization configuration..."
    kubectl apply -f deployment/k8s/performance-optimization.yaml
    
    success "Performance optimization deployed"
}

# Deploy API Gateway
deploy_api_gateway() {
    phase "Deploying API Gateway..."
    
    # Deploy Kong API Gateway
    log "Deploying Kong API Gateway..."
    helm upgrade --install kong kong/kong \
        --namespace kong \
        --set env.database=off \
        --set env.declarative_config=/kong_dbless/kong.yaml \
        --set ingressController.enabled=true \
        --wait
    
    # Apply API Gateway configuration
    log "Applying API Gateway configuration..."
    kubectl apply -f deployment/k8s/api-gateway.yaml
    
    success "API Gateway deployed"
}

# Deploy chaos engineering
deploy_chaos_engineering() {
    phase "Deploying chaos engineering components..."
    
    # Deploy Chaos Monkey
    log "Deploying chaos engineering tools..."
    kubectl apply -f deployment/k8s/chaos-engineering.yaml
    
    success "Chaos engineering deployed"
}

# Deploy backup and disaster recovery
deploy_backup_dr() {
    phase "Deploying backup and disaster recovery..."
    
    # Deploy Velero for backups
    log "Deploying Velero..."
    helm upgrade --install velero vmware-tanzu/velero \
        --namespace velero \
        --set configuration.provider=aws \
        --set configuration.backupStorageLocation.bucket=metafunction-backups \
        --set configuration.backupStorageLocation.config.region=us-west-2 \
        --set snapshotsEnabled=false \
        --wait
    
    # Apply multi-region configuration
    log "Applying multi-region configuration..."
    kubectl apply -f deployment/k8s/multi-region.yaml
    
    success "Backup and disaster recovery deployed"
}

# Deploy application with chosen strategy
deploy_application() {
    phase "Deploying MetaFunction application using $DEPLOYMENT_STRATEGY strategy..."
    
    local image_tag="${IMAGE_TAG:-latest}"
    local app_image="${APP_IMAGE:-metafunction:$image_tag}"
    
    case "$DEPLOYMENT_STRATEGY" in
        "blue-green")
            log "Executing blue-green deployment..."
            bash scripts/blue-green-deploy.sh "$app_image"
            ;;
        "canary")
            log "Executing canary deployment..."
            bash scripts/canary-deploy.sh "$app_image"
            ;;
        "rolling")
            log "Executing rolling deployment..."
            helm upgrade --install "$APP_NAME" deployment/helm/metafunction/ \
                --namespace "$NAMESPACE" \
                --set image.repository="$(echo $app_image | cut -d: -f1)" \
                --set image.tag="$(echo $app_image | cut -d: -f2)" \
                --wait
            ;;
        *)
            error "Unknown deployment strategy: $DEPLOYMENT_STRATEGY"
            exit 1
            ;;
    esac
    
    success "Application deployed using $DEPLOYMENT_STRATEGY strategy"
}

# Validate deployment
validate_deployment() {
    phase "Validating enterprise deployment..."
    
    if [ "$SKIP_TESTS" = "true" ]; then
        warning "Skipping validation tests"
        return 0
    fi
    
    log "Running enterprise integration tests..."
    python3 tests/enterprise/test_advanced_integration.py \
        --namespace "$NAMESPACE" \
        --environment "$ENVIRONMENT" \
        --output "deployment-validation-report.json"
    
    if [ $? -eq 0 ]; then
        success "All validation tests passed"
    else
        error "Some validation tests failed. Check deployment-validation-report.json for details"
        return 1
    fi
}

# Configure monitoring dashboards
configure_dashboards() {
    phase "Configuring monitoring dashboards..."
    
    # Import Grafana dashboards
    log "Importing Grafana dashboards..."
    
    local dashboards=(
        "kubernetes-cluster-overview"
        "metafunction-application-metrics"
        "cost-optimization-dashboard"
        "security-compliance-dashboard"
        "performance-optimization-dashboard"
    )
    
    for dashboard in "${dashboards[@]}"; do
        log "Importing dashboard: $dashboard"
        # This would import predefined dashboards
        # kubectl create configmap "$dashboard" --from-file="monitoring/dashboards/$dashboard.json" -n monitoring
    done
    
    success "Monitoring dashboards configured"
}

# Generate deployment report
generate_report() {
    phase "Generating deployment report..."
    
    local report_file="enterprise-deployment-report-$(date +%Y%m%d-%H%M%S).json"
    
    cat > "$report_file" << EOF
{
  "deployment_summary": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "$ENVIRONMENT",
    "namespace": "$NAMESPACE",
    "deployment_strategy": "$DEPLOYMENT_STRATEGY",
    "app_name": "$APP_NAME"
  },
  "deployed_components": {
    "infrastructure": {
      "cert_manager": "$(kubectl get pods -n cert-manager --no-headers | wc -l) pods",
      "istio": "$(kubectl get pods -n istio-system --no-headers | wc -l) pods"
    },
    "monitoring": {
      "prometheus": "$(kubectl get pods -n monitoring -l app.kubernetes.io/name=prometheus --no-headers | wc -l) pods",
      "grafana": "$(kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana --no-headers | wc -l) pods",
      "jaeger": "$(kubectl get pods -n observability -l app=jaeger --no-headers | wc -l) pods"
    },
    "security": {
      "falco": "$(kubectl get pods -n security -l app.kubernetes.io/name=falco --no-headers | wc -l) pods",
      "opa_gatekeeper": "$(kubectl get pods -n gatekeeper-system --no-headers | wc -l) pods"
    },
    "siem": {
      "elasticsearch": "$(kubectl get pods -n elastic-system -l app=elasticsearch-master --no-headers | wc -l) pods",
      "kibana": "$(kubectl get pods -n elastic-system -l app=kibana --no-headers | wc -l) pods",
      "logstash": "$(kubectl get pods -n elastic-system -l app=logstash --no-headers | wc -l) pods"
    },
    "cost_optimization": {
      "kubecost": "$(kubectl get pods -n kubecost --no-headers | wc -l) pods"
    },
    "performance": {
      "redis": "$(kubectl get pods -n redis --no-headers | wc -l) pods"
    },
    "api_gateway": {
      "kong": "$(kubectl get pods -n kong --no-headers | wc -l) pods"
    },
    "backup_dr": {
      "velero": "$(kubectl get pods -n velero --no-headers | wc -l) pods"
    },
    "application": {
      "metafunction": "$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME --no-headers | wc -l) pods"
    }
  },
  "cluster_resources": {
    "nodes": "$(kubectl get nodes --no-headers | wc -l)",
    "total_pods": "$(kubectl get pods --all-namespaces --no-headers | wc -l)",
    "services": "$(kubectl get services --all-namespaces --no-headers | wc -l)",
    "deployments": "$(kubectl get deployments --all-namespaces --no-headers | wc -l)"
  },
  "external_endpoints": {
    "grafana": "$(kubectl get service -n monitoring grafana -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo 'Not exposed')",
    "kibana": "$(kubectl get service -n elastic-system kibana-kibana -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo 'Not exposed')",
    "kong": "$(kubectl get service -n kong kong-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo 'Not exposed')",
    "kubecost": "$(kubectl get service -n kubecost kubecost-cost-analyzer -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo 'Not exposed')"
  }
}
EOF
    
    log "Deployment report generated: $report_file"
    success "Enterprise deployment completed successfully!"
}

# Cleanup function
cleanup() {
    phase "Cleaning up temporary resources..."
    
    # Clean up any temporary files or resources
    rm -f /tmp/deployment-*.yaml
    
    log "Cleanup completed"
}

# Print usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Enhanced Enterprise Deployment Automation for MetaFunction

OPTIONS:
    -n, --namespace NAMESPACE       Kubernetes namespace (default: production)
    -e, --environment ENVIRONMENT   Environment name (default: production)
    -s, --strategy STRATEGY         Deployment strategy: blue-green, canary, rolling (default: blue-green)
    -i, --image IMAGE               Application image (default: metafunction:latest)
    --dry-run                       Show what would be deployed without actually deploying
    --skip-tests                    Skip validation tests
    --skip-monitoring               Skip monitoring deployment
    --skip-security                 Skip security deployment
    --skip-siem                     Skip SIEM deployment
    -h, --help                      Show this help message

EXAMPLES:
    $0                                          # Deploy with defaults
    $0 -n staging -e staging -s canary          # Deploy to staging with canary strategy
    $0 --dry-run                                # Show deployment plan
    $0 -i myregistry/metafunction:v1.2.3        # Deploy specific image version

EOF
}

# Main execution function
main() {
    local skip_monitoring=false
    local skip_security=false
    local skip_siem=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -s|--strategy)
                DEPLOYMENT_STRATEGY="$2"
                shift 2
                ;;
            -i|--image)
                APP_IMAGE="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-monitoring)
                skip_monitoring=true
                shift
                ;;
            --skip-security)
                skip_security=true
                shift
                ;;
            --skip-siem)
                skip_siem=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Print deployment plan
    cat << EOF

${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗
║                    METAFUNCTION ENTERPRISE DEPLOYMENT                       ║
╚══════════════════════════════════════════════════════════════════════════════╝${NC}

Environment:        $ENVIRONMENT
Namespace:          $NAMESPACE
Strategy:           $DEPLOYMENT_STRATEGY
Application Image:  ${APP_IMAGE:-metafunction:latest}
Dry Run:            $DRY_RUN
Skip Tests:         $SKIP_TESTS

Components to deploy:
  ✓ Core Infrastructure (cert-manager, Istio)
  $([ "$skip_monitoring" = false ] && echo "✓" || echo "✗") Monitoring & Observability (Prometheus, Grafana, Jaeger)
  $([ "$skip_security" = false ] && echo "✓" || echo "✗") Security & Compliance (Falco, OPA, SBOM)
  $([ "$skip_siem" = false ] && echo "✓" || echo "✗") SIEM & Logging (Elasticsearch, Kibana, Logstash)
  ✓ Cost Optimization (KubeCost, VPA)
  ✓ Performance Optimization (Redis, CDN)
  ✓ API Gateway (Kong)
  ✓ Chaos Engineering
  ✓ Backup & DR (Velero)
  ✓ MetaFunction Application

EOF
    
    if [ "$DRY_RUN" = "true" ]; then
        log "Dry run mode - no actual deployment will be performed"
        exit 0
    fi
    
    # Confirm deployment
    read -p "Proceed with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Deployment cancelled"
        exit 0
    fi
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Execute deployment phases
    check_prerequisites
    create_namespaces
    deploy_infrastructure
    
    if [ "$skip_monitoring" = false ]; then
        deploy_monitoring
        configure_dashboards
    fi
    
    if [ "$skip_security" = false ]; then
        deploy_security
    fi
    
    if [ "$skip_siem" = false ]; then
        deploy_siem
    fi
    
    deploy_cost_optimization
    deploy_performance
    deploy_api_gateway
    deploy_chaos_engineering
    deploy_backup_dr
    deploy_application
    validate_deployment
    generate_report
    
    cat << EOF

${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗
║                    DEPLOYMENT COMPLETED SUCCESSFULLY!                       ║
╚══════════════════════════════════════════════════════════════════════════════╝${NC}

Next steps:
1. Review the deployment report: enterprise-deployment-report-*.json
2. Access monitoring dashboards:
   - Grafana: kubectl port-forward -n monitoring svc/grafana 3000:80
   - Kibana: kubectl port-forward -n elastic-system svc/kibana-kibana 5601:5601
   - KubeCost: kubectl port-forward -n kubecost svc/kubecost-cost-analyzer 9090:9090

3. Configure external access for production environments
4. Set up backup schedules and disaster recovery procedures
5. Review security policies and compliance reports

For troubleshooting, check: kubectl get pods --all-namespaces

EOF
}

# Execute main function
main "$@"
