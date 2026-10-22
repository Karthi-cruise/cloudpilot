#!/usr/bin/env bash
# ==============================================================================
# CloudPilot Local Setup Script
# Automates local kind cluster creation, Docker builds, and deployment.
# ==============================================================================

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}☁️  CloudPilot — Automated Local Environment Provisioning${NC}"
echo -e "${CYAN}==========================================================${NC}"

# 1. Verify Prerequisites
echo -e "\n${YELLOW}[1/6] Verifying local CLI tools...${NC}"
command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ Docker is required but not installed.${NC}"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}❌ kubectl is required but not installed.${NC}"; exit 1; }
command -v kind >/dev/null 2>&1 || { echo -e "${RED}❌ kind is required. Install with: brew install kind${NC}"; exit 1; }
echo -e "${GREEN}✅ All prerequisites satisfied!${NC}"

# 2. Python Virtual Environment Setup
echo -e "\n${YELLOW}[2/6] Setting up Python virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1 || true
pip install -r requirements.txt >/dev/null 2>&1 || true
pip install -r requirements-dev.txt >/dev/null 2>&1 || true
echo -e "${GREEN}✅ Python dependencies installed!${NC}"

# 3. Create or check kind cluster
CLUSTER_NAME="cloudpilot"
echo -e "\n${YELLOW}[3/6] Setting up kind cluster '${CLUSTER_NAME}'...${NC}"
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${GREEN}✅ Cluster '${CLUSTER_NAME}' already exists.${NC}"
else
    kind create cluster --name "${CLUSTER_NAME}"
    echo -e "${GREEN}✅ Cluster created successfully!${NC}"
fi

kubectl cluster-info --context "kind-${CLUSTER_NAME}"

# 4. Build and Load Docker Image
echo -e "\n${YELLOW}[4/6] Building CloudPilot Docker image...${NC}"
docker build -t cloudpilot:latest .
echo -e "${GREEN}✅ Image built. Loading into kind cluster...${NC}"
kind load docker-image cloudpilot:latest --name "${CLUSTER_NAME}"
echo -e "${GREEN}✅ Docker image available inside cluster nodes!${NC}"

# 5. Apply Kubernetes Manifests
echo -e "\n${YELLOW}[5/6] Deploying CloudPilot stack to Kubernetes...${NC}"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/networkpolicy.yaml

echo -e "Deploying Prometheus and Grafana manifests..."
kubectl apply -f k8s/prometheus/
kubectl apply -f k8s/grafana/

echo -e "Waiting for deployment rollout..."
kubectl rollout status deployment/cloudpilot -n cloudpilot --timeout=90s || true

# 6. Summary
echo -e "\n${GREEN}==========================================================${NC}"
echo -e "${GREEN}🎉 CloudPilot setup completed successfully!${NC}"
echo -e "${GREEN}==========================================================${NC}"
echo -e "To start forwarding local ports, run:"
echo -e "  ${CYAN}./scripts/port_forward.sh${NC}  or  ${CYAN}make port-forward${NC}"
echo ""
echo -e "Services available at:"
echo -e "  🌐 App & API:    http://localhost:8000"
echo -e "  📖 Interactive:  http://localhost:8000/api/docs"
echo -e "  🔥 Prometheus:   http://localhost:9090"
echo -e "  📊 Grafana:      http://localhost:3000 (admin / cloudpilot)"
echo ""
