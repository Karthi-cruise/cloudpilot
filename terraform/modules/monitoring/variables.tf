variable "namespace" {
  description = "Kubernetes namespace in which the monitoring stack will be deployed."
  type        = string
}

variable "grafana_password" {
  description = "Password for the Grafana 'admin' user."
  type        = string
  sensitive   = true
}

variable "prometheus_retention" {
  description = "Prometheus TSDB retention duration string (e.g. '7d', '30d')."
  type        = string
  default     = "7d"
  validation {
    condition     = can(regex("^[0-9]+(d|h|m|s|y)$", var.prometheus_retention))
    error_message = "prometheus_retention must be a valid Prometheus duration, e.g. '7d', '24h', '30m'."
  }
}
