terraform {
  required_version = ">= 1.9.0"
  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "~> 0.6.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.33.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.15.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.0"
    }
  }
}

# ---------------------------------------------------------------------------
# Kind cluster
# ---------------------------------------------------------------------------
resource "kind_cluster" "cloudpilot" {
  name           = var.cluster_name
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    # Control-plane node — exposes port 8080 → 80 for ingress traffic.
    node {
      role = "control-plane"
      kubeadm_config_patches = [
        <<-EOT
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
        EOT
      ]
      extra_port_mappings {
        container_port = 80
        host_port      = 8080
        protocol       = "TCP"
      }
    }

    node {
      role = "worker"
    }

    node {
      role = "worker"
    }
  }
}

# ---------------------------------------------------------------------------
# Convenience locals — keep provider blocks DRY
# ---------------------------------------------------------------------------
locals {
  kube_host                   = kind_cluster.cloudpilot.endpoint
  kube_client_certificate     = kind_cluster.cloudpilot.client_certificate
  kube_client_key             = kind_cluster.cloudpilot.client_key
  kube_cluster_ca_certificate = kind_cluster.cloudpilot.cluster_ca_certificate

  common_labels = {
    app        = "cloudpilot"
    managed-by = "terraform"
    version    = var.app_version
  }
}

# ---------------------------------------------------------------------------
# Provider configuration (post-cluster)
# ---------------------------------------------------------------------------
provider "kubernetes" {
  host                   = local.kube_host
  client_certificate     = base64decode(local.kube_client_certificate)
  client_key             = base64decode(local.kube_client_key)
  cluster_ca_certificate = base64decode(local.kube_cluster_ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = local.kube_host
    client_certificate     = base64decode(local.kube_client_certificate)
    client_key             = base64decode(local.kube_client_key)
    cluster_ca_certificate = base64decode(local.kube_cluster_ca_certificate)
  }
}

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------
resource "kubernetes_namespace" "cloudpilot" {
  metadata {
    name = var.namespace
    labels = {
      name        = var.namespace
      team        = "platform-engineering"
      environment = var.environment
      managed-by  = "terraform"
    }
  }

  depends_on = [kind_cluster.cloudpilot]
}

resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
    labels = {
      name       = "monitoring"
      managed-by = "terraform"
    }
  }

  depends_on = [kind_cluster.cloudpilot]
}

# ---------------------------------------------------------------------------
# RBAC — ServiceAccount + Role + RoleBinding
# ---------------------------------------------------------------------------
resource "kubernetes_service_account" "cloudpilot" {
  metadata {
    name      = "cloudpilot-sa"
    namespace = kubernetes_namespace.cloudpilot.metadata[0].name
    labels    = local.common_labels
  }
}

resource "kubernetes_role" "cloudpilot" {
  metadata {
    name      = "cloudpilot-role"
    namespace = kubernetes_namespace.cloudpilot.metadata[0].name
  }

  # Read-only access to core workload / config resources
  rule {
    api_groups = [""]
    resources  = ["pods", "configmaps", "events", "endpoints"]
    verbs      = ["get", "list", "watch"]
  }

  rule {
    api_groups = ["apps"]
    resources  = ["deployments", "replicasets"]
    verbs      = ["get", "list", "watch"]
  }
}

resource "kubernetes_role_binding" "cloudpilot" {
  metadata {
    name      = "cloudpilot-rolebinding"
    namespace = kubernetes_namespace.cloudpilot.metadata[0].name
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.cloudpilot.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.cloudpilot.metadata[0].name
    namespace = kubernetes_namespace.cloudpilot.metadata[0].name
  }
}

# ---------------------------------------------------------------------------
# ConfigMap — runtime tunables injected as environment variables
# ---------------------------------------------------------------------------
resource "kubernetes_config_map" "cloudpilot" {
  metadata {
    name      = "cloudpilot-config"
    namespace = kubernetes_namespace.cloudpilot.metadata[0].name
    labels    = local.common_labels
  }

  data = {
    VERSION                 = var.app_version
    LOG_LEVEL               = var.log_level
    SLO_AVAILABILITY_TARGET = tostring(var.slo_availability_target)
    METRICS_PORT            = "8000"
  }
}

# ---------------------------------------------------------------------------
# Secret — Gemini API key (only created when a key is supplied)
# ---------------------------------------------------------------------------
resource "kubernetes_secret" "gemini_api_key" {
  count = var.gemini_api_key != "" ? 1 : 0

  metadata {
    name      = "cloudpilot-secrets"
    namespace = kubernetes_namespace.cloudpilot.metadata[0].name
    labels    = local.common_labels
  }

  data = {
    GEMINI_API_KEY = var.gemini_api_key
  }

  type = "Opaque"
}

# ---------------------------------------------------------------------------
# Monitoring module — Prometheus + Grafana via kube-prometheus-stack
# ---------------------------------------------------------------------------
module "monitoring" {
  source = "./modules/monitoring"

  namespace            = kubernetes_namespace.monitoring.metadata[0].name
  grafana_password     = var.grafana_admin_password
  prometheus_retention = var.prometheus_retention

  depends_on = [kubernetes_namespace.monitoring]
}
