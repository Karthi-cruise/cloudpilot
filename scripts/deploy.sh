#!/usr/bin/env bash
# ==============================================================================
# CloudPilot Zero-Downtime Deployment & Smoke Test Script
# ==============================================================================

set -euo pipefail

IMAGE_TAG="${1:-latest}"
CLUSTER_NAME="cloudpilot"
NAMESPACE="cloudpilot"

echo "🚀 Deploying CloudPilot image tag: ${IMAGE_TAG}..."

# Build & Load
docker build -t "cloudpilot:${IMAGE_TAG}" .
kind load docker-image "cloudpilot:${IMAGE_TAG}" --name "${CLUSTER_NAME}"

# Update deployment image
kubectl set image deployment/cloudpilot "cloudpilot=cloudpilot:${IMAGE_TAG}" -n "${NAMESPACE}"

# Wait for rolling update
echo "⏳ Waiting for rolling update rollout..."
if ! kubectl rollout status deployment/cloudpilot -n "${NAMESPACE}" --timeout=120s; then
    echo "❌ Deployment rollout failed! Initiating automated rollback..."
    kubectl rollout undo deployment/cloudpilot -n "${NAMESPACE}"
    kubectl rollout status deployment/cloudpilot -n "${NAMESPACE}"
    echo "⚠️ Rollback completed."
    exit 1
fi

# Run Smoke Tests
echo "🧪 Running deployment smoke tests..."
sleep 3
POD=$(kubectl get pod -n "${NAMESPACE}" -l app=cloudpilot -o jsonpath='{.items[0].metadata.name}')
if kubectl exec -n "${NAMESPACE}" "${POD}" -- curl -sf http://localhost:8000/health >/dev/null; then
    echo "✅ Smoke test passed! New version is healthy and accepting traffic."
else
    echo "❌ Smoke test failed on pod ${POD}! Rolling back..."
    kubectl rollout undo deployment/cloudpilot -n "${NAMESPACE}"
    exit 1
fi
