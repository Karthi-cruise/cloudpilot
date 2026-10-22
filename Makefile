# CloudPilot — Comprehensive Makefile
# Self-Healing Cloud-Native Reliability Platform
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME     := cloudpilot
IMAGE_NAME   := cloudpilot
IMAGE_TAG    := latest
REGISTRY     := ghcr.io
Karthi-cruise        := Karthi-cruise
FULL_IMAGE   := $(REGISTRY)/$(Karthi-cruise)/$(IMAGE_NAME):$(IMAGE_TAG)
KUBE_NS      := cloudpilot
PYTHON       := python3
VENV         := .venv
PIP          := $(VENV)/bin/pip
PYTEST       := $(VENV)/bin/pytest
BLACK        := $(VENV)/bin/black
ISORT        := $(VENV)/bin/isort
FLAKE8       := $(VENV)/bin/flake8
BANDIT       := $(VENV)/bin/bandit
TRIVY        := trivy

# Colors
RED     := \033[0;31m
GREEN   := \033[0;32m
YELLOW  := \033[0;33m
BLUE    := \033[0;34m
MAGENTA := \033[0;35m
CYAN    := \033[0;36m
WHITE   := \033[0;37m
RESET   := \033[0m

.DEFAULT_GOAL := help

.PHONY: help install install-dev venv test test-verbose lint format format-check \
        security-scan bandit pip-audit trivy-scan build build-dev push \
        docker-up docker-down docker-logs docker-shell \
        cluster-create cluster-delete cluster-status \
        deploy deploy-helm undeploy rollout-status rollback scale \
        chaos chaos-kill chaos-latency chaos-errors chaos-cpu chaos-stop chaos-full \
        slo-report cost-estimate ai-incident \
        port-forward port-forward-stop \
        monitoring-up logs clean setup demo \
        terraform-init terraform-plan terraform-apply terraform-destroy \
        ci-local check-prereqs

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────
help: ## 📖 Show this help message
	@echo ""
	@echo "$(CYAN)☁️  CloudPilot — Self-Healing Cloud-Native Reliability Platform$(RESET)"
	@echo "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-25s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Quick Start:$(RESET)"
	@echo "  make setup        → Full local environment setup"
	@echo "  make demo         → Run complete demo"
	@echo "  make chaos        → Run chaos engineering experiments"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Prerequisites check
# ─────────────────────────────────────────────────────────────────────────────
check-prereqs: ## 🔍 Check all prerequisites are installed
	@echo "$(BLUE)🔍 Checking prerequisites...$(RESET)"
	@command -v docker >/dev/null 2>&1 || (echo "$(RED)❌ docker not found$(RESET)" && exit 1)
	@command -v kubectl >/dev/null 2>&1 || (echo "$(RED)❌ kubectl not found$(RESET)" && exit 1)
	@command -v kind >/dev/null 2>&1 || (echo "$(RED)❌ kind not found. Install: brew install kind$(RESET)" && exit 1)
	@command -v helm >/dev/null 2>&1 || (echo "$(RED)❌ helm not found. Install: brew install helm$(RESET)" && exit 1)
	@command -v terraform >/dev/null 2>&1 || (echo "$(YELLOW)⚠️  terraform not found (optional)$(RESET)")
	@command -v $(PYTHON) >/dev/null 2>&1 || (echo "$(RED)❌ python3 not found$(RESET)" && exit 1)
	@echo "$(GREEN)✅ All required prerequisites found!$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Python environment
# ─────────────────────────────────────────────────────────────────────────────
venv: ## 🐍 Create Python virtual environment
	@echo "$(BLUE)🐍 Creating virtual environment...$(RESET)"
	@$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)✅ Virtual environment created at $(VENV)/$(RESET)"

install: venv ## 📦 Install production dependencies
	@echo "$(BLUE)📦 Installing production dependencies...$(RESET)"
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@echo "$(GREEN)✅ Production dependencies installed!$(RESET)"

install-dev: install ## 📦 Install all dependencies (production + dev)
	@echo "$(BLUE)📦 Installing dev dependencies...$(RESET)"
	@$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✅ All dependencies installed!$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────
test: ## 🧪 Run tests with coverage (fail if <80%)
	@echo "$(BLUE)🧪 Running tests with coverage...$(RESET)"
	@$(PYTEST) tests/ \
		-v \
		--cov=app \
		--cov-report=html:htmlcov \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=80 \
		--tb=short
	@echo "$(GREEN)✅ All tests passed! Coverage report: htmlcov/index.html$(RESET)"

test-verbose: ## 🧪 Run tests with verbose output and no capture
	@$(PYTEST) tests/ -v -s --tb=long --cov=app --cov-report=term-missing

test-fast: ## ⚡ Run tests quickly (no coverage)
	@$(PYTEST) tests/ -v --tb=short -q

# ─────────────────────────────────────────────────────────────────────────────
# Code quality
# ─────────────────────────────────────────────────────────────────────────────
lint: ## 🔎 Run all linters (black check, isort check, flake8)
	@echo "$(BLUE)🔎 Running linters...$(RESET)"
	@$(BLACK) --check --diff app/ tests/ ai/ sre/ chaos/
	@$(ISORT) --check-only --diff app/ tests/ ai/ sre/ chaos/
	@$(FLAKE8) app/ tests/ ai/ sre/ chaos/ --max-line-length=100 --extend-ignore=E203,W503
	@echo "$(GREEN)✅ All linting passed!$(RESET)"

format: ## ✨ Auto-format code (black + isort)
	@echo "$(BLUE)✨ Formatting code...$(RESET)"
	@$(BLACK) app/ tests/ ai/ sre/ chaos/ --line-length=100
	@$(ISORT) app/ tests/ ai/ sre/ chaos/ --profile=black
	@echo "$(GREEN)✅ Code formatted!$(RESET)"

format-check: ## ✨ Check formatting without changing files
	@$(BLACK) --check app/ tests/ ai/ sre/ chaos/
	@$(ISORT) --check-only app/ tests/ ai/ sre/ chaos/

# ─────────────────────────────────────────────────────────────────────────────
# Security scanning
# ─────────────────────────────────────────────────────────────────────────────
bandit: ## 🔒 Run Bandit SAST scan on Python code
	@echo "$(BLUE)🔒 Running Bandit SAST scan...$(RESET)"
	@$(BANDIT) -r app/ ai/ sre/ chaos/ -ll -f json -o bandit-report.json || true
	@$(BANDIT) -r app/ ai/ sre/ chaos/ -ll
	@echo "$(GREEN)✅ Bandit scan complete! Report: bandit-report.json$(RESET)"

pip-audit: ## 🔒 Audit Python dependencies for CVEs
	@echo "$(BLUE)🔒 Running pip-audit...$(RESET)"
	@$(VENV)/bin/pip-audit -r requirements.txt --format=json -o pip-audit-report.json || true
	@$(VENV)/bin/pip-audit -r requirements.txt
	@echo "$(GREEN)✅ pip-audit complete!$(RESET)"

trivy-scan: ## 🔒 Scan Docker image with Trivy (fail on CRITICAL/HIGH)
	@echo "$(BLUE)🔒 Running Trivy container scan...$(RESET)"
	@$(TRIVY) image \
		--severity CRITICAL,HIGH \
		--exit-code 1 \
		--format table \
		$(IMAGE_NAME):$(IMAGE_TAG) || \
	(echo "$(YELLOW)⚠️  Building image first...$(RESET)" && $(MAKE) build && \
	$(TRIVY) image --severity CRITICAL,HIGH --exit-code 1 $(IMAGE_NAME):$(IMAGE_TAG))
	@echo "$(GREEN)✅ Trivy scan passed!$(RESET)"

security-scan: bandit pip-audit trivy-scan ## 🛡️ Run all security scans
	@echo "$(GREEN)✅ All security scans passed!$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Docker
# ─────────────────────────────────────────────────────────────────────────────
build: ## 🐳 Build Docker image (multi-stage production build)
	@echo "$(BLUE)🐳 Building Docker image...$(RESET)"
	@docker build \
		--tag $(IMAGE_NAME):$(IMAGE_TAG) \
		--tag $(IMAGE_NAME):$$(git rev-parse --short HEAD 2>/dev/null || echo 'local') \
		--label "org.opencontainers.image.created=$$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
		--label "org.opencontainers.image.revision=$$(git rev-parse HEAD 2>/dev/null || echo 'local')" \
		--label "org.opencontainers.image.source=https://github.com/$(Karthi-cruise)/$(APP_NAME)" \
		.
	@echo "$(GREEN)✅ Image built: $(IMAGE_NAME):$(IMAGE_TAG)$(RESET)"
	@docker image ls $(IMAGE_NAME)

build-dev: ## 🐳 Build development image (with dev tools)
	@docker build --target builder --tag $(IMAGE_NAME):dev .

push: ## 🐳 Push image to GitHub Container Registry
	@echo "$(BLUE)🐳 Pushing to $(REGISTRY)/$(Karthi-cruise)/$(IMAGE_NAME)...$(RESET)"
	@docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(FULL_IMAGE)
	@docker push $(FULL_IMAGE)
	@echo "$(GREEN)✅ Image pushed: $(FULL_IMAGE)$(RESET)"

docker-up: ## 🚀 Start local stack with docker-compose
	@echo "$(BLUE)🚀 Starting local stack...$(RESET)"
	@docker-compose up -d --build
	@echo "$(GREEN)✅ Stack running!$(RESET)"
	@echo ""
	@echo "  App:         http://localhost:8000"
	@echo "  API Docs:    http://localhost:8000/api/docs"
	@echo "  Prometheus:  http://localhost:9090"
	@echo "  Grafana:     http://localhost:3000 (admin/cloudpilot)"
	@echo "  AlertMgr:    http://localhost:9093"

docker-down: ## 🛑 Stop docker-compose stack
	@docker-compose down --volumes

docker-logs: ## 📋 Follow docker-compose logs
	@docker-compose logs -f app

docker-shell: ## 🐚 Open shell in running app container
	@docker-compose exec app /bin/sh

# ─────────────────────────────────────────────────────────────────────────────
# Kubernetes cluster (kind)
# ─────────────────────────────────────────────────────────────────────────────
cluster-create: ## ☸️  Create kind Kubernetes cluster
	@echo "$(BLUE)☸️  Creating kind cluster...$(RESET)"
	@kind get clusters 2>/dev/null | grep -q $(APP_NAME) && \
		echo "$(YELLOW)⚠️  Cluster already exists$(RESET)" || \
		kind create cluster --name $(APP_NAME) --config kind-config.yaml 2>/dev/null || \
		kind create cluster --name $(APP_NAME)
	@kubectl cluster-info --context kind-$(APP_NAME)
	@echo "$(GREEN)✅ Cluster ready!$(RESET)"

cluster-delete: ## 🗑️  Delete kind cluster
	@echo "$(YELLOW)🗑️  Deleting kind cluster...$(RESET)"
	@kind delete cluster --name $(APP_NAME)
	@echo "$(GREEN)✅ Cluster deleted.$(RESET)"

cluster-status: ## 📊 Show cluster status
	@echo "$(BLUE)📊 Cluster Status$(RESET)"
	@kubectl get nodes
	@echo ""
	@kubectl get pods -n $(KUBE_NS) 2>/dev/null || echo "Namespace not deployed yet"

load-image: ## 📦 Load Docker image into kind cluster
	@echo "$(BLUE)📦 Loading image into kind cluster...$(RESET)"
	@kind load docker-image $(IMAGE_NAME):$(IMAGE_TAG) --name $(APP_NAME)
	@echo "$(GREEN)✅ Image loaded!$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Kubernetes deployment
# ─────────────────────────────────────────────────────────────────────────────
deploy: ## 🚀 Deploy to Kubernetes (kubectl apply)
	@echo "$(BLUE)🚀 Deploying to Kubernetes...$(RESET)"
	@kubectl apply -f k8s/namespace.yaml
	@kubectl apply -f k8s/rbac.yaml
	@kubectl apply -f k8s/configmap.yaml
	@kubectl apply -f k8s/deployment.yaml
	@kubectl apply -f k8s/service.yaml
	@kubectl apply -f k8s/hpa.yaml
	@kubectl apply -f k8s/pdb.yaml
	@kubectl apply -f k8s/networkpolicy.yaml
	@echo "$(BLUE)⏳ Waiting for rollout...$(RESET)"
	@kubectl rollout status deployment/cloudpilot -n $(KUBE_NS) --timeout=120s
	@echo "$(GREEN)✅ Deployed successfully!$(RESET)"
	@kubectl get pods -n $(KUBE_NS)

deploy-helm: ## 🚀 Deploy using Helm chart
	@echo "$(BLUE)🚀 Deploying via Helm...$(RESET)"
	@helm upgrade --install cloudpilot ./helm/cloudpilot \
		--namespace $(KUBE_NS) \
		--create-namespace \
		--set image.tag=$(IMAGE_TAG) \
		--wait --timeout=120s
	@echo "$(GREEN)✅ Helm deployment complete!$(RESET)"
	@helm status cloudpilot -n $(KUBE_NS)

undeploy: ## 🗑️  Remove deployment from Kubernetes
	@echo "$(YELLOW)🗑️  Removing deployment...$(RESET)"
	@kubectl delete -f k8s/ -n $(KUBE_NS) --ignore-not-found
	@kubectl delete namespace $(KUBE_NS) --ignore-not-found
	@echo "$(GREEN)✅ Undeployed.$(RESET)"

rollout-status: ## 📊 Check deployment rollout status
	@kubectl rollout status deployment/cloudpilot -n $(KUBE_NS)
	@kubectl get pods -n $(KUBE_NS) -o wide

rollback: ## ⏮️  Rollback to previous deployment
	@echo "$(YELLOW)⏮️  Rolling back deployment...$(RESET)"
	@kubectl rollout undo deployment/cloudpilot -n $(KUBE_NS)
	@kubectl rollout status deployment/cloudpilot -n $(KUBE_NS)
	@echo "$(GREEN)✅ Rollback complete!$(RESET)"

scale: ## ⚖️  Scale deployment (usage: make scale REPLICAS=5)
	@echo "$(BLUE)⚖️  Scaling to $(REPLICAS) replicas...$(RESET)"
	@kubectl scale deployment/cloudpilot -n $(KUBE_NS) --replicas=$(REPLICAS)
	@kubectl rollout status deployment/cloudpilot -n $(KUBE_NS)

logs: ## 📋 Follow application logs
	@kubectl logs -f -l app=cloudpilot -n $(KUBE_NS) --all-containers=true

# ─────────────────────────────────────────────────────────────────────────────
# Port forwarding
# ─────────────────────────────────────────────────────────────────────────────
port-forward: ## 🔌 Forward all services to localhost (background)
	@echo "$(BLUE)🔌 Starting port forwarding...$(RESET)"
	@kubectl port-forward svc/cloudpilot -n $(KUBE_NS) 8000:80 &
	@kubectl port-forward svc/prometheus -n $(KUBE_NS) 9090:9090 &
	@kubectl port-forward svc/grafana -n $(KUBE_NS) 3000:3000 &
	@sleep 2
	@echo "$(GREEN)✅ Port forwarding active!$(RESET)"
	@echo ""
	@echo "  🌐 App:        http://localhost:8000"
	@echo "  📖 API Docs:   http://localhost:8000/api/docs"
	@echo "  📊 Metrics:    http://localhost:8000/metrics"
	@echo "  🔥 Prometheus: http://localhost:9090"
	@echo "  📈 Grafana:    http://localhost:3000 (admin/cloudpilot-admin)"

port-forward-stop: ## 🔌 Stop all port forwarding
	@pkill -f "kubectl port-forward" || true
	@echo "$(GREEN)✅ Port forwarding stopped.$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Chaos Engineering
# ─────────────────────────────────────────────────────────────────────────────
chaos: ## 💥 Run full chaos experiment (all failure types)
	@echo "$(MAGENTA)💥 Starting full chaos experiment...$(RESET)"
	@$(VENV)/bin/python chaos/failure_injector.py full-experiment
	@echo "$(GREEN)✅ Chaos experiment complete! Check chaos-report.json$(RESET)"

chaos-kill: ## 💥 Kill a random pod
	@echo "$(MAGENTA)💥 Killing random pod...$(RESET)"
	@$(VENV)/bin/python chaos/failure_injector.py kill-pod --namespace $(KUBE_NS)

chaos-latency: ## 💥 Inject latency (default: 3000ms for 60s)
	@echo "$(MAGENTA)💥 Injecting latency...$(RESET)"
	@$(VENV)/bin/python chaos/failure_injector.py inject-latency \
		--duration $(or $(DURATION),60) \
		--latency-ms $(or $(LATENCY),3000)

chaos-errors: ## 💥 Inject HTTP 500 errors (default: 50% for 30s)
	@echo "$(MAGENTA)💥 Injecting error rate...$(RESET)"
	@$(VENV)/bin/python chaos/failure_injector.py inject-errors \
		--duration $(or $(DURATION),30) \
		--rate $(or $(RATE),50)

chaos-cpu: ## 💥 Inject CPU stress (default: 60s)
	@echo "$(MAGENTA)💥 Injecting CPU stress...$(RESET)"
	@$(VENV)/bin/python chaos/failure_injector.py cpu-stress \
		--duration $(or $(DURATION),60)

chaos-stop: ## 🛑 Stop all active chaos
	@echo "$(BLUE)🛑 Stopping all chaos simulations...$(RESET)"
	@curl -s -X DELETE http://localhost:8000/api/v1/simulate | python3 -m json.tool
	@echo "$(GREEN)✅ Chaos stopped.$(RESET)"

chaos-report: ## 📋 Show chaos experiment report
	@$(VENV)/bin/python chaos/failure_injector.py report

# ─────────────────────────────────────────────────────────────────────────────
# SRE & Observability
# ─────────────────────────────────────────────────────────────────────────────
slo-report: ## 📊 Show SLO status report (all windows)
	@echo "$(BLUE)📊 SLO Report$(RESET)"
	@$(VENV)/bin/python sre/slo_calculator.py --report --prometheus-url http://localhost:9090

slo-watch: ## 👁️  Watch SLO in real-time (refresh every 10s)
	@$(VENV)/bin/python sre/slo_calculator.py --watch 10

cost-estimate: ## 💰 Show infrastructure cost estimate
	@echo "$(BLUE)💰 Cost Estimation$(RESET)"
	@$(VENV)/bin/python sre/cost_estimator.py --namespace $(KUBE_NS)

ai-incident: ## 🤖 Run AI incident analysis on latest incident
	@echo "$(BLUE)🤖 Running AI incident analysis...$(RESET)"
	@$(VENV)/bin/python -c "\
import asyncio, json; \
from datetime import datetime; \
from ai.incident_summarizer import IncidentSummarizer, IncidentData; \
async def main(): \
    s = IncidentSummarizer(); \
    data = IncidentData( \
        incident_id='INC-001', title='High Error Rate Detected', severity='P2', \
        started_at=datetime.utcnow(), \
        pod_logs=['ERROR: Connection timeout', 'ERROR: HTTP 500', 'WARNING: High latency'], \
        k8s_events=['Pod cloudpilot-xxx restarted', 'HPA scaled to 5 replicas'], \
        metrics_snapshot={'error_rate': 0.45, 'p99_latency_ms': 2500, 'availability': 55.0}, \
        failure_type='error_rate' \
    ); \
    analysis = await s.analyze_incident(data); \
    print(json.dumps({ \
        'summary': analysis.summary, \
        'root_cause': analysis.root_cause, \
        'remediation_steps': analysis.remediation_steps, \
        'confidence': analysis.confidence, \
        'is_mock': analysis.is_mock \
    }, indent=2)) \
asyncio.run(main())"

# ─────────────────────────────────────────────────────────────────────────────
# Monitoring
# ─────────────────────────────────────────────────────────────────────────────
monitoring-up: ## 📈 Deploy Prometheus + Grafana to K8s
	@echo "$(BLUE)📈 Deploying monitoring stack...$(RESET)"
	@kubectl apply -f k8s/prometheus/
	@kubectl apply -f k8s/grafana/
	@echo "$(GREEN)✅ Monitoring deployed!$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Terraform
# ─────────────────────────────────────────────────────────────────────────────
terraform-init: ## 🏗️  Initialize Terraform
	@echo "$(BLUE)🏗️  Initializing Terraform...$(RESET)"
	@cd terraform && terraform init
	@echo "$(GREEN)✅ Terraform initialized!$(RESET)"

terraform-plan: ## 🏗️  Terraform plan (preview changes)
	@echo "$(BLUE)🏗️  Running Terraform plan...$(RESET)"
	@cd terraform && terraform plan -out=tfplan

terraform-apply: ## 🏗️  Apply Terraform (provision infrastructure)
	@echo "$(BLUE)🏗️  Applying Terraform...$(RESET)"
	@cd terraform && terraform apply tfplan
	@echo "$(GREEN)✅ Infrastructure provisioned!$(RESET)"
	@cd terraform && terraform output setup_instructions

terraform-destroy: ## 🗑️  Destroy Terraform infrastructure
	@echo "$(RED)⚠️  Destroying all Terraform infrastructure...$(RESET)"
	@cd terraform && terraform destroy -auto-approve
	@echo "$(YELLOW)Infrastructure destroyed.$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Full local CI simulation
# ─────────────────────────────────────────────────────────────────────────────
ci-local: lint test bandit pip-audit ## 🔄 Run full CI pipeline locally
	@echo "$(GREEN)✅ Full CI pipeline passed locally!$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Setup & Demo
# ─────────────────────────────────────────────────────────────────────────────
setup: check-prereqs install-dev cluster-create build load-image deploy ## 🚀 Full local setup from scratch
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(GREEN)║         ☁️  CloudPilot Setup Complete!                 ║$(RESET)"
	@echo "$(GREEN)╠════════════════════════════════════════════════════════╣$(RESET)"
	@echo "$(GREEN)║  Run 'make port-forward' to access:                   ║$(RESET)"
	@echo "$(GREEN)║  🌐 App:       http://localhost:8000                  ║$(RESET)"
	@echo "$(GREEN)║  📖 API Docs:  http://localhost:8000/api/docs         ║$(RESET)"
	@echo "$(GREEN)║  🔥 Metrics:   http://localhost:8000/metrics          ║$(RESET)"
	@echo "$(GREEN)║  📊 Grafana:   http://localhost:3000                  ║$(RESET)"
	@echo "$(GREEN)║                                                        ║$(RESET)"
	@echo "$(GREEN)║  Next steps:                                           ║$(RESET)"
	@echo "$(GREEN)║  make slo-report   → View SLO status                  ║$(RESET)"
	@echo "$(GREEN)║  make chaos        → Run chaos experiments             ║$(RESET)"
	@echo "$(GREEN)║  make ai-incident  → Run AI incident analysis          ║$(RESET)"
	@echo "$(GREEN)╚════════════════════════════════════════════════════════╝$(RESET)"

demo: ## 🎬 Run complete demo (setup + chaos + slo report + ai analysis)
	@echo "$(CYAN)🎬 CloudPilot Demo Starting...$(RESET)"
	@echo ""
	@echo "$(YELLOW)Step 1: Check SLO status...$(RESET)"
	@curl -s http://localhost:8000/api/v1/slo | python3 -m json.tool || echo "Run 'make port-forward' first"
	@echo ""
	@echo "$(YELLOW)Step 2: Inject failure (50% errors for 30s)...$(RESET)"
	@$(VENV)/bin/python chaos/failure_injector.py inject-errors --duration 30 --rate 50
	@echo ""
	@echo "$(YELLOW)Step 3: Show SLO impact...$(RESET)"
	@curl -s http://localhost:8000/api/v1/slo | python3 -m json.tool || true
	@echo ""
	@echo "$(YELLOW)Step 4: Run AI incident analysis...$(RESET)"
	@$(MAKE) ai-incident
	@echo ""
	@echo "$(YELLOW)Step 5: Generate cost estimate...$(RESET)"
	@$(MAKE) cost-estimate
	@echo ""
	@echo "$(GREEN)✅ Demo complete! Open Grafana at http://localhost:3000 to see dashboards.$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────
clean: ## 🧹 Clean all build artifacts and caches
	@echo "$(YELLOW)🧹 Cleaning...$(RESET)"
	@rm -rf __pycache__ .pytest_cache htmlcov .coverage coverage.xml
	@rm -rf app/__pycache__ tests/__pycache__ ai/__pycache__ sre/__pycache__ chaos/__pycache__
	@rm -f bandit-report.json pip-audit-report.json chaos-report.json
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Cleaned!$(RESET)"

clean-all: clean docker-down ## 🧹 Clean everything including Docker and K8s
	@docker rmi $(IMAGE_NAME):$(IMAGE_TAG) 2>/dev/null || true
	@$(MAKE) cluster-delete 2>/dev/null || true
	@rm -rf $(VENV)
	@echo "$(GREEN)✅ Everything cleaned!$(RESET)"
