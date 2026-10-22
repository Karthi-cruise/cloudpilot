# ---------------------------------------------------------------------------
# kube-prometheus-stack — Prometheus + Alertmanager + Grafana
# ---------------------------------------------------------------------------
resource "helm_release" "kube_prometheus_stack" {
  name       = "prometheus-stack"
  namespace  = var.namespace
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "65.1.1"

  # Allow up to 10 minutes for all CRDs + pods to settle.
  timeout           = 600
  wait              = true
  wait_for_jobs     = true
  create_namespace  = false
  cleanup_on_fail   = true
  atomic            = true

  values = [<<-EOT
    # ----------------------------------------------------------------
    # Grafana
    # ----------------------------------------------------------------
    grafana:
      adminPassword: "${var.grafana_password}"
      service:
        type: ClusterIP
      persistence:
        enabled: false
      # Dashboard provider that the sidecar will populate.
      dashboardProviders:
        dashboardproviders.yaml:
          apiVersion: 1
          providers:
            - name: cloudpilot
              orgId: 1
              folder: CloudPilot
              type: file
              disableDeletion: false
              editable: true
              options:
                path: /var/lib/grafana/dashboards/cloudpilot
      # ConfigMap sidecar auto-loads dashboards labelled grafana_dashboard=1.
      sidecar:
        dashboards:
          enabled: true
          label: grafana_dashboard
          labelValue: "1"
          searchNamespace: ALL
        datasources:
          enabled: true
          label: grafana_datasource

    # ----------------------------------------------------------------
    # Prometheus
    # ----------------------------------------------------------------
    prometheus:
      prometheusSpec:
        retention: "${var.prometheus_retention}"
        # Discover ServiceMonitors / PodMonitors across all namespaces
        # regardless of Helm release label selectors.
        podMonitorSelectorNilUsesHelmValues: false
        serviceMonitorSelectorNilUsesHelmValues: false
        ruleSelectorNilUsesHelmValues: false
        probeSelectorNilUsesHelmValues: false
        ruleNamespaceSelector: {}
        serviceMonitorNamespaceSelector: {}
        podMonitorNamespaceSelector: {}
        probeNamespaceSelector: {}
        storageSpec:
          volumeClaimTemplate:
            spec:
              accessModes: ["ReadWriteOnce"]
              resources:
                requests:
                  storage: 5Gi

    # ----------------------------------------------------------------
    # Alertmanager
    # ----------------------------------------------------------------
    alertmanager:
      alertmanagerSpec:
        storage:
          volumeClaimTemplate:
            spec:
              accessModes: ["ReadWriteOnce"]
              resources:
                requests:
                  storage: 1Gi

    # ----------------------------------------------------------------
    # Exporters
    # ----------------------------------------------------------------
    kubeStateMetrics:
      enabled: true

    nodeExporter:
      enabled: true

    # ----------------------------------------------------------------
    # Default alert rules (optional, keeps noise low in local dev)
    # ----------------------------------------------------------------
    defaultRules:
      create: true
      rules:
        alertmanager: true
        etcd: false
        configReloaders: true
        general: true
        k8s: true
        kubeApiserverAvailability: true
        kubeApiserverBurnrate: true
        kubeApiserverHistogram: true
        kubeApiserverSlos: true
        kubeControllerManager: false
        kubelet: true
        kubeProxy: false
        kubePrometheusGeneral: true
        kubePrometheusNodeRecording: true
        kubernetesApps: true
        kubernetesResources: true
        kubernetesStorage: true
        kubernetesSystem: true
        kubeSchedulerAlerting: false
        kubeSchedulerRecording: false
        kubeStateMetrics: true
        network: true
        node: true
        nodeExporterAlerting: true
        nodeExporterRecording: true
        prometheus: true
        prometheusOperator: true
  EOT
  ]
}

# ---------------------------------------------------------------------------
# ServiceMonitor — scrape CloudPilot app metrics on :8000/metrics every 15 s
# ---------------------------------------------------------------------------
# The CRD is installed by the Helm chart above so we must wait for it.
resource "kubernetes_manifest" "cloudpilot_service_monitor" {
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"

    metadata = {
      name      = "cloudpilot"
      namespace = var.namespace
      labels = {
        app             = "cloudpilot"
        release         = "prometheus-stack"
      }
    }

    spec = {
      # Match Services in any namespace that carry app=cloudpilot.
      namespaceSelector = {
        any = true
      }
      selector = {
        matchLabels = {
          app = "cloudpilot"
        }
      }
      endpoints = [
        {
          port     = "http"
          path     = "/metrics"
          interval = "15s"
          scheme   = "http"
        }
      ]
    }
  }

  depends_on = [helm_release.kube_prometheus_stack]
}

# ---------------------------------------------------------------------------
# PrometheusRule — SLO burn-rate alerts for CloudPilot
# ---------------------------------------------------------------------------
resource "kubernetes_manifest" "cloudpilot_slo_rules" {
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "PrometheusRule"

    metadata = {
      name      = "cloudpilot-slo-rules"
      namespace = var.namespace
      labels = {
        app     = "cloudpilot"
        release = "prometheus-stack"
      }
    }

    spec = {
      groups = [
        {
          name = "cloudpilot.slo"
          rules = [
            {
              alert = "CloudPilotHighErrorRate"
              expr  = "sum(rate(http_requests_total{job=\"cloudpilot\",status=~\"5..\"}[5m])) / sum(rate(http_requests_total{job=\"cloudpilot\"}[5m])) > 0.005"
              for   = "2m"
              labels = {
                severity = "warning"
                team     = "platform-engineering"
              }
              annotations = {
                summary     = "CloudPilot error rate exceeds SLO budget"
                description = "5xx error rate is {{ $value | humanizePercentage }} over the last 5 minutes."
              }
            },
            {
              alert = "CloudPilotDown"
              expr  = "up{job=\"cloudpilot\"} == 0"
              for   = "1m"
              labels = {
                severity = "critical"
                team     = "platform-engineering"
              }
              annotations = {
                summary     = "CloudPilot instance is down"
                description = "CloudPilot instance {{ $labels.instance }} has been down for more than 1 minute."
              }
            }
          ]
        }
      ]
    }
  }

  depends_on = [helm_release.kube_prometheus_stack]
}
