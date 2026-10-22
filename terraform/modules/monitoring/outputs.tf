output "grafana_service_name" {
  description = "Kubernetes Service name for Grafana (useful for kubectl port-forward)."
  value       = "prometheus-stack-grafana"
}

output "prometheus_service_name" {
  description = "Kubernetes Service name for Prometheus (useful for kubectl port-forward)."
  value       = "prometheus-stack-kube-prom-prometheus"
}

output "alertmanager_service_name" {
  description = "Kubernetes Service name for Alertmanager."
  value       = "prometheus-stack-kube-prom-alertmanager"
}

output "helm_release_name" {
  description = "Helm release name for the kube-prometheus-stack chart."
  value       = helm_release.kube_prometheus_stack.name
}

output "helm_release_status" {
  description = "Deployment status of the kube-prometheus-stack Helm release."
  value       = helm_release.kube_prometheus_stack.status
}
