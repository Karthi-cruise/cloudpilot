# ---------------------------------------------------------------------------
# Cluster
# ---------------------------------------------------------------------------
variable "cluster_name" {
  description = "Name of the kind Kubernetes cluster."
  type        = string
  default     = "cloudpilot"
}

# ---------------------------------------------------------------------------
# Kubernetes
# ---------------------------------------------------------------------------
variable "namespace" {
  description = "Kubernetes namespace in which CloudPilot workloads are deployed."
  type        = string
  default     = "cloudpilot"
}

variable "environment" {
  description = "Deployment environment. Controls labelling and certain defaults."
  type        = string
  default     = "local"
  validation {
    condition     = contains(["local", "staging", "production"], var.environment)
    error_message = "environment must be one of: local, staging, production."
  }
}

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
variable "app_version" {
  description = "SemVer application version string (used in image tags and labels)."
  type        = string
  default     = "1.0.0"
}

variable "app_replicas" {
  description = "Number of CloudPilot application pod replicas."
  type        = number
  default     = 3
  validation {
    condition     = var.app_replicas >= 1 && var.app_replicas <= 20
    error_message = "app_replicas must be between 1 and 20 (inclusive)."
  }
}

variable "log_level" {
  description = "Application log verbosity level (DEBUG, INFO, WARNING, ERROR)."
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "log_level must be one of: DEBUG, INFO, WARNING, ERROR."
  }
}

variable "image_repository" {
  description = "Container image repository path (without tag)."
  type        = string
  default     = "ghcr.io/Karthi-cruise/cloudpilot"
}

variable "image_tag" {
  description = "Container image tag to deploy."
  type        = string
  default     = "latest"
}

# ---------------------------------------------------------------------------
# SLO
# ---------------------------------------------------------------------------
variable "slo_availability_target" {
  description = "Target availability percentage for CloudPilot's SLO (e.g. 99.5)."
  type        = number
  default     = 99.5
  validation {
    condition     = var.slo_availability_target > 0 && var.slo_availability_target <= 100
    error_message = "slo_availability_target must be a percentage between 0 (exclusive) and 100 (inclusive)."
  }
}

# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------
variable "grafana_admin_password" {
  description = "Password for the Grafana 'admin' user. Override this in non-local environments."
  type        = string
  default     = "cloudpilot-admin"
  sensitive   = true
}

variable "prometheus_retention" {
  description = "Prometheus TSDB retention duration (e.g. '7d', '30d')."
  type        = string
  default     = "7d"
}

# ---------------------------------------------------------------------------
# AI / Secrets
# ---------------------------------------------------------------------------
variable "gemini_api_key" {
  description = "Google Gemini API key used by the AI incident-summarizer sidecar. Leave empty to skip Secret creation."
  type        = string
  default     = ""
  sensitive   = true
}
