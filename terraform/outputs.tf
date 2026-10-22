# ---------------------------------------------------------------------------
# Cluster identifiers
# ---------------------------------------------------------------------------
output "cluster_name" {
  description = "Name of the provisioned kind cluster."
  value       = kind_cluster.cloudpilot.name
}

output "cluster_endpoint" {
  description = "Kubernetes API server endpoint."
  value       = kind_cluster.cloudpilot.endpoint
}

output "kubeconfig" {
  description = "Raw kubeconfig for the kind cluster. Treat as sensitive."
  value       = kind_cluster.cloudpilot.kubeconfig
  sensitive   = true
}

# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------
output "namespace" {
  description = "Kubernetes namespace where CloudPilot workloads are deployed."
  value       = kubernetes_namespace.cloudpilot.metadata[0].name
}

output "monitoring_namespace" {
  description = "Kubernetes namespace where monitoring stack is deployed."
  value       = kubernetes_namespace.monitoring.metadata[0].name
}

# ---------------------------------------------------------------------------
# Access URLs  (valid after port-forward / ingress is active)
# ---------------------------------------------------------------------------
output "app_url" {
  description = "CloudPilot application base URL (after port-forward)."
  value       = "http://localhost:8000"
}

output "grafana_url" {
  description = "Grafana dashboard URL (after port-forward)."
  value       = "http://localhost:3000"
}

output "prometheus_url" {
  description = "Prometheus UI URL (after port-forward)."
  value       = "http://localhost:9090"
}

# ---------------------------------------------------------------------------
# Monitoring stack service names (from sub-module)
# ---------------------------------------------------------------------------
output "grafana_service_name" {
  description = "Kubernetes Service name for Grafana."
  value       = module.monitoring.grafana_service_name
}

output "prometheus_service_name" {
  description = "Kubernetes Service name for Prometheus."
  value       = module.monitoring.prometheus_service_name
}

# ---------------------------------------------------------------------------
# Human-readable next-steps message
# ---------------------------------------------------------------------------
output "setup_instructions" {
  description = "Post-provisioning quickstart guide."
  value       = <<-EOT
  ╔══════════════════════════════════════════════════════════════╗
  ║           CloudPilot infrastructure provisioned!            ║
  ╚══════════════════════════════════════════════════════════════╝

  Access URLs (after port-forward):
    App         → http://localhost:8000
    API Docs    → http://localhost:8000/api/docs
    Metrics     → http://localhost:8000/metrics
    Prometheus  → http://localhost:9090
    Grafana     → http://localhost:3000  (admin / ${var.grafana_admin_password})

  Next steps:
    make deploy        # Build image & roll out application
    make port-forward  # Start all port-forwards in background
    make chaos         # Run LitmusChaos experiments

  Kubeconfig:
    export KUBECONFIG=$(terraform output -raw kubeconfig | base64 -d > /tmp/cloudpilot.yaml && echo /tmp/cloudpilot.yaml)
  EOT
}
