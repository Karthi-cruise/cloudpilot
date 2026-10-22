<div align="center">

# ☁️ CloudPilot
### **Self-Healing Cloud-Native Reliability & Platform Engineering System**

[![CI/CD Pipeline](https://img.shields.io/badge/CI%2FCD-10--Stage%20Pipeline-success?style=for-the-badge&logo=githubactions)](.github/workflows/ci.yml)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.31-blue?style=for-the-badge&logo=kubernetes)](k8s/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-623CE4?style=for-the-badge&logo=terraform)](terraform/)
[![Prometheus](https://img.shields.io/badge/Observability-Prometheus%20%2B%20Grafana-E6522C?style=for-the-badge&logo=prometheus)](monitoring/)
[![DevSecOps](https://img.shields.io/badge/Security-Trivy%20%7C%20Bandit-critical?style=for-the-badge&logo=securityscorecard)](.github/workflows/security.yml)
[![AI Engine](https://img.shields.io/badge/AIOps-Gemini%20API-orange?style=for-the-badge&logo=google)](ai/)

<p align="center">
  A production-grade cloud-native engineering platform featuring automated 10-stage CI/CD pipelines, Kubernetes microservices, Google SRE error budget tracking, chaos engineering failure injection, and Gemini AI-powered incident diagnosis.
</p>

[Architecture](#-architecture) • [Features](#-key-features) • [Quick Start](#-quick-start-5-minutes) • [SRE & SLOs](#-sre--slo-engine) • [Chaos Engineering](#-chaos-engineering--self-healing) • [AIOps](#-aiops-incident-summarizer) • [Resume Bullets](#-resume-ready-bullet-points)

---

</div>

## 📌 Project Overview

**CloudPilot** is an internal platform engineering product that simulates the full operational lifecycle of enterprise microservices. Rather than just deploying a container, CloudPilot automates the entire loop:

1. **Developer pushes code** to GitHub.
2. **10-stage CI/CD & DevSecOps pipeline** triggers: automated testing, code quality gates, Bandit SAST analysis, pip-audit dependency CVE checks, multi-stage Docker build, and Trivy container vulnerability scanning.
3. **Continuous Deployment** delivers rolling updates to a Kubernetes cluster with zero downtime, protected by Pod Disruption Budgets, Horizontal Pod Autoscalers, and anti-affinity rules.
4. **Automated Smoke Tests & Rollback** automatically revert releases if health checks fail.
5. **SRE Telemetry & Observability** tracks live SLO compliance, 99.5% availability targets, and Google SRE multi-window burn rate alerts.
6. **Chaos Engineering Engine** executes failure injection experiments (pod kills, artificial latency, error bursts, CPU starvation) and measures detection time and MTTR.
7. **Gemini AIOps Triage** ingests pod logs, Kubernetes events, and metric snapshots to generate structured root cause hypotheses and prioritized remediation runbooks.

---

## 🏗 Architecture

```
Developer Push → GitHub Repository
                       │
                       ▼
        ┌──────────────────────────────────┐
        │  10-Stage CI/CD & DevSecOps Gate │
        │  • Pytest (>80% coverage)        │
        │  • Bandit SAST Code Scanner      │
        │  • pip-audit Dependency CVEs     │
        │  • Multi-Stage Docker Build      │
        │  • Trivy Container Scan          │
        │  • Push to GitHub Container Reg. │
        └──────────────────┬───────────────┘
                           │
                           ▼
          ┌───────────────────────────────────┐
          │     Kubernetes Cluster (kind)     │
          │  ┌─────────────────────────────┐  │
          │  │ CloudPilot Pods (3 Replicas)│  │
          │  │ • Liveness / Readiness      │  │
          │  │ • HPA (CPU > 60% Scale Out) │  │
          │  │ • Pod Disruption Budget     │  │
          │  │ • Network Policies          │  │
          │  └──────────────┬──────────────┘  │
          └─────────────────┼─────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
   ┌──────────────────────┐    ┌──────────────────────┐
   │ Observability Stack  │    │ Chaos Engine (SRE)   │
   │ • Prometheus Scrapes │    │ • Pod Termination    │
   │ • Grafana Dashboard  │    │ • Latency Injection  │
   │ • AlertManager       │    │ • HTTP 500 Spikes    │
   │ • Fast/Slow Burn SLO │    │ • CPU Starvation     │
   └──────────┬───────────┘    └──────────┬───────────┘
              │                           │
              └─────────────┬─────────────┘
                            ▼
               ┌────────────────────────┐
               │ Gemini AIOps Incident  │
               │ Summarizer & Diagnosis │
               │ (Root Cause & Playbook)│
               └────────────────────────┘
```

---

## 🛠 Technology Stack

| Layer | Technologies | Purpose |
|---|---|---|
| **API Application** | Python 3.12, FastAPI, Pydantic v2 | High-throughput REST API, CRUD endpoints, telemetry |
| **Testing & Quality** | Pytest, pytest-cov, Black, Flake8, isort | Unit testing (>80% coverage), formatting, linting |
| **Containers** | Docker (multi-stage non-root build) | Secure, hardened, low-footprint image |
| **Container Registry**| GitHub Packages (ghcr.io) | OCI compliant container image distribution |
| **Orchestration** | Kubernetes 1.31 (kind / Minikube / EKS) | Deployments, HPA, PDB, Services, NetworkPolicies |
| **Package Manager** | Helm 3 | Parameterized, repeatable Kubernetes manifests |
| **Infrastructure as Code**| Terraform 1.9+ | Declarative cluster and monitoring provisioning |
| **Observability** | Prometheus, Grafana, AlertManager | Metrics scraping, PromQL alerts, real-time dashboard |
| **DevSecOps** | Trivy, Bandit, pip-audit | SAST, dependency auditing, container vulnerability gate |
| **SRE & Reliability** | Custom Python SLO Engine | Real-time availability, error budgets, burn rate alerts |
| **Chaos Engineering** | Custom Failure Injection CLI | Outage simulation, MTTR and recovery measurement |
| **AIOps & GenAI** | Google Gemini API (`gemini-3.8-flash`) | Automated log parsing, root cause analysis, playbooks |

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Docker
- `kubectl`
- `kind` (`brew install kind`)
- Python 3.11+
- `helm` (`brew install helm`)

### 1. One-Command Setup
Clone the repository and run the automated setup:
```bash
git clone https://github.com/Karthi-cruise/cloudpilot.git
cd cloudpilot

# Sets up venv, installs deps, builds image, provisions kind, and deploys K8s
make setup
```

### 2. Forward Services Locally
```bash
make port-forward
```
Access the operational interfaces:
- 🌐 **CloudPilot API**: [http://localhost:8000](http://localhost:8000)
- 📖 **Interactive Swagger Docs**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- 📊 **Prometheus Metrics**: [http://localhost:8000/metrics](http://localhost:8000/metrics)
- 🔥 **Prometheus Server**: [http://localhost:9090](http://localhost:9090)
- 📈 **Grafana Dashboards**: [http://localhost:3000](http://localhost:3000) *(User: `admin` | Password: `cloudpilot`)*

---

## 📊 SRE & SLO Engine

CloudPilot implements **Google SRE Book** principles for error budget management and multi-window burn rate alerts:

```
Availability Target : 99.50%
Allowed Downtime    : 0.50% (216 minutes / 30 days)
Burn Rate Alerting  : Fast Burn (14.4x in 1h) -> P1 Page
                      Slow Burn (6.0x in 6h)  -> P2 Ticket
```

### Querying Live SLO Status
```bash
make slo-report
```
*Output:*
```text
=================================================================
📊 CLOUDPILOT SERVICE LEVEL OBJECTIVE (SLO) REPORT
=================================================================
 Target Availability:            99.50%
 Measured Availability (1h):     99.82%  [HEALTHY]
 Error Budget Remaining (30d):   214.2 minutes (99.1%)
 P99 Latency:                    18.40 ms (Target: < 200 ms)
 Active Fast Burn Alert:         NO
 Burn Rate (1h):                 0.36x
=================================================================
```

---

## 💥 Chaos Engineering & Self-Healing

CloudPilot includes a standalone failure injection suite to test resilience under simulated incident conditions.

```bash
# Run full automated chaos experiment suite
make chaos
```

### What Happens During a Chaos Run:
1. **Pod Crash Experiment**: Zero-grace-period termination of a random pod. Kubernetes ReplicaSet detects the failure in `< 3s` and schedules a replacement pod within `8.5s`.
2. **Latency Injection**: Injects 3000ms delay into requests. Readiness probe trips to `503`, isolating the pod from the traffic pool.
3. **Error Rate Spiking**: Injects 50% HTTP 500 errors. The SLO engine logs the failure, records error budget consumption, and triggers `CloudPilotSLOFastBurn`.
4. **CPU Starvation**: Executes compute-heavy loops. Horizontal Pod Autoscaler (HPA) observes CPU > 60% and scales replicas from 3 to 5.

### Results Output:
```text
================================================================================
EXPERIMENT             | TYPE         | DETECT   | RECOVERY (MTTR) | SLO IMPACT
--------------------------------------------------------------------------------
CHAOS-1729602-pod_kill | pod_kill     | 2.10s    | 8.40s           | -0.00%
CHAOS-1729602-latency  | latency      | 4.80s    | 1.80s           | -0.08%
CHAOS-1729602-err_rate | error_rate   | 1.90s    | 2.50s           | -0.32%
CHAOS-1729602-cpu_load | cpu_stress   | 3.20s    | 12.10s          | -0.00%
================================================================================
🎯 Average MTTR (Self-Healing Time): 6.20 seconds
================================================================================
```

---

## 🤖 AIOps Incident Summarizer

CloudPilot integrates the **Gemini API** (`gemini-3.8-flash`) to automate incident triage. When an alert fires or an incident is logged, the summarizer ingests:
- Container stdout/stderr logs
- Kubernetes cluster events (`kubectl get events`)
- Metric snapshots at the time of the outage

```bash
make ai-incident
```
*Sample Output:*
```json
{
  "incident_id": "INC-001",
  "summary": "Elevated HTTP 500 error rate detected causing rapid error budget consumption.",
  "root_cause": "Systemic upstream database timeout triggered by connection pool exhaustion during load spike.",
  "affected_components": ["cloudpilot-api", "slo-tracker", "kube-service-endpoints"],
  "remediation_steps": [
    "1. Check active simulations: curl -s http://localhost:8000/api/v1/simulate/status",
    "2. If unexpected, terminate simulation: curl -X DELETE http://localhost:8000/api/v1/simulate",
    "3. Inspect connection pool saturation metrics in Grafana",
    "4. Scale deployment if traffic volume exceeds capacity: kubectl scale deploy cloudpilot --replicas=6",
    "5. Re-evaluate 1h SLO error budget remaining"
  ],
  "confidence": "high",
  "is_mock": false
}
```

---

## 💰 Cloud Cost & Capacity Estimator

Tracks allocated CPU and RAM across Kubernetes namespaces and calculates approximate run rates:

```bash
make cost-estimate
```
*Sample Output:*
```text
=================================================================
💰 CLOUDPILOT INFRASTRUCTURE COST & CAPACITY ESTIMATOR
=================================================================
 Replicas Active:            3
 Total CPU Allocated:        0.300 vCPUs
 Total RAM Allocated:        0.384 GB
-----------------------------------------------------------------
 Estimated Hourly Cost:      $0.0169/hr
 Estimated Monthly Workload: $12.34/mo
 Control Plane Fee:          $73.00/mo
 Total Monthly Run Rate:     $85.34/mo
-----------------------------------------------------------------
 Capacity Efficiency:        65.0%
 Estimated Idle Waste:       $4.32/mo
=================================================================
```

---

## 🛡️ DevSecOps Security Suite

CloudPilot enforces security policy as code across code, dependencies, and containers:

```bash
# Run full security audit
make security-scan
```
- **Bandit**: Static Application Security Testing (SAST) for Python code.
- **pip-audit**: Cross-checks dependencies against Open Source Vulnerability (OSV) databases.
- **Trivy**: Container image vulnerability scanner failing CI if CRITICAL or HIGH CVEs are found.
- **Security Contexts**: Kubernetes manifests enforce `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, and drop all Linux capabilities (`capabilities: drop: [ALL]`).

---

## 📂 Project Structure

```text
cloudpilot/
├── app/                        # FastAPI core service
│   ├── main.py                 # Lifespan, middlewares, router registration
│   ├── metrics.py              # Prometheus metric collectors & exporters
│   ├── slo.py                  # Sliding window SLO & error budget engine
│   ├── models.py               # Pydantic v2 schemas
│   ├── middleware.py           # Metrics & structured JSON logging
│   └── routers/
│       ├── health.py           # /health, /ready, /live probes
│       ├── items.py            # Microservices resource inventory CRUD
│       ├── slo_router.py       # REST API for SLO status & burn rate
│       ├── incidents.py        # Incident tracking, MTTR, & AI diagnosis
│       └── simulate.py         # Failure injection endpoints
├── tests/                      # Automated test suite
│   ├── conftest.py             # Fixtures & state isolation
│   ├── test_health.py          # Probe & version verification
│   ├── test_items.py           # CRUD functional tests
│   ├── test_slo.py             # SLO & error budget tests
│   ├── test_simulate.py        # Chaos simulation tests
│   └── test_incidents.py       # Incident lifecycle & webhook tests
├── ai/
│   └── incident_summarizer.py  # Gemini API incident diagnosis engine
├── k8s/                        # Production Kubernetes manifests
│   ├── namespace.yaml
│   ├── rbac.yaml
│   ├── configmap.yaml
│   ├── deployment.yaml         # Anti-affinity, non-root, rolling updates
│   ├── service.yaml
│   ├── hpa.yaml                # Autoscaling: CPU > 60%, RAM > 70%
│   ├── pdb.yaml                # Pod Disruption Budget (min 2 pods)
│   ├── networkpolicy.yaml      # Zero-trust network segmentation
│   ├── prometheus/             # Prometheus deployment, RBAC & ConfigMap
│   └── grafana/                # Grafana deployment, service, datasources
│       └── dashboards/
│           └── cloudpilot.json # Pre-built SRE Grafana dashboard
├── helm/
│   └── cloudpilot/             # Parameterized Helm chart
├── terraform/                  # Infrastructure as Code
│   ├── main.tf                 # kind cluster & monitoring modules
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/monitoring/     # kube-prometheus-stack Helm release
├── chaos/
│   └── failure_injector.py     # Chaos engineering CLI
├── sre/
│   ├── slo_calculator.py       # Standalone SLO CLI tool
│   └── cost_estimator.py       # Infrastructure capacity & cost estimator
├── scripts/
│   ├── setup.sh                # End-to-end local environment setup
│   ├── deploy.sh               # Deployment with smoke test & auto-rollback
│   ├── port_forward.sh         # Background port forwarding
│   └── chaos_test.sh           # Automated chaos test runner
├── .github/workflows/
│   ├── ci.yml                  # 10-stage CI/CD pipeline
│   ├── security.yml            # Scheduled SAST, CVE & container scan
│   └── chaos.yml               # Scheduled chaos engineering pipeline
├── Dockerfile                  # Hardened multi-stage container build
├── docker-compose.yml          # Local development stack
├── pyproject.toml              # Pytest, Black, isort, coverage config
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development & security tools
├── Makefile                    # Unified developer interface
└── README.md                   # Project documentation
```

---

## 💼 Resume-Ready Bullet Points

```markdown
CloudPilot — Self-Healing Cloud-Native Reliability & Platform Engineering System
Python · FastAPI · Docker · Kubernetes · GitHub Actions · Terraform · Helm · Prometheus · Grafana · Trivy · Gemini AI

• Engineered an automated 10-stage CI/CD and DevSecOps pipeline on GitHub Actions integrating 
  Pytest (>80% coverage), Bandit SAST, pip-audit dependency scanning, multi-stage Docker builds, 
  and Trivy container vulnerability scanning, enforcing automated rollback on deployment failure.

• Implemented an SRE-grade SLO tracking engine based on Google SRE methodologies, monitoring 99.5% 
  availability targets and multi-window burn rate alerts (14.4x fast burn, 6.0x slow burn) via 
  Prometheus PromQL rules and custom Grafana dashboards.

• Architected high-availability Kubernetes deployments featuring Pod Anti-Affinity, Horizontal Pod 
  Autoscalers (CPU > 60%), Pod Disruption Budgets (minAvailable: 2), and non-root security contexts.

• Developed a custom Chaos Engineering framework to inject pod crashes, latency, and error bursts, 
  empirically verifying Kubernetes self-healing and measuring Mean Time to Recovery (MTTR) under 10 seconds.

• Integrated Google Gemini AI to analyze container logs, Kubernetes events, and metric snapshots during 
  outages, generating structured root cause hypotheses and prioritized remediation runbooks.

• Provisioned reproducible Kubernetes infrastructure and Prometheus/Grafana monitoring stacks 
  using Terraform and Helm, reducing local environment spin-up time to under 3 minutes.
```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
