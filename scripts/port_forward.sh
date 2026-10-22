#!/usr/bin/env bash
# ==============================================================================
# CloudPilot Port Forwarding Helper
# ==============================================================================

set -euo pipefail

NAMESPACE="cloudpilot"

echo "🔌 Initiating port forwarding for CloudPilot ecosystem..."

# Kill any existing forwards
pkill -f "kubectl port-forward.*${NAMESPACE}" || true

# Forward in background
kubectl port-forward svc/cloudpilot -n "${NAMESPACE}" 8000:80 >/dev/null 2>&1 &
kubectl port-forward svc/prometheus -n "${NAMESPACE}" 9090:9090 >/dev/null 2>&1 &
kubectl port-forward svc/grafana -n "${NAMESPACE}" 3000:3000 >/dev/null 2>&1 &

sleep 2

echo "✅ Port forwarding active!"
echo "---------------------------------------------------------"
echo "  🌐 API Service:   http://localhost:8000"
echo "  📖 API Docs:      http://localhost:8000/api/docs"
echo "  📈 Metrics:       http://localhost:8000/metrics"
echo "  🔥 Prometheus:    http://localhost:9090"
echo "  📊 Grafana:       http://localhost:3000 (admin / cloudpilot)"
echo "---------------------------------------------------------"
echo "To stop port-forwarding, run: pkill -f 'kubectl port-forward'"
