# CloudPilot Site Reliability Engineering (SRE) Runbook

This document outlines the Service Level Objectives (SLOs), Service Level Indicators (SLIs), error budget policies, and operational runbooks for CloudPilot.

---

## 1. Service Level Indicators & Objectives

| Service Level Indicator (SLI) | SLO Target | Measurement Window | Alerting Method |
|---|---|---|---|
| **Availability SLI** | **99.5%** | 30-day rolling window | Multi-window multi-burn-rate |
| **Latency SLI (P99)** | **< 200 ms** | 5-minute rolling window | PromQL threshold alert |
| **Error Rate SLI** | **< 0.5%** | 5-minute rolling window | PromQL threshold alert |

### Error Budget Math
- **Target**: 99.5% Availability
- **Allowed Downtime Fraction**: 0.5% (0.005)
- **Monthly Allowed Downtime / Budget**:
  $$0.005 \times 30 \text{ days} \times 24 \text{ hours} \times 60 \text{ minutes} = 216 \text{ minutes}$$

---

## 2. Burn Rate Alerting Matrix (Google SRE Methodology)

| Alert Name | Burn Rate | Budget Consumed in Window | Window | Time to 100% Budget Exhaustion | Severity | Action |
|---|---|---|---|---|---|---|
| `CloudPilotSLOFastBurn` | **14.4×** | 2% in 1 hour | 1 Hour | **2.08 Days** | **P1 (Critical)** | PagerDuty / On-call page |
| `CloudPilotSLOSlowBurn` | **6.0×** | 5% in 6 hours | 6 Hours | **5.00 Days** | **P2 (Major)** | Jira Ticket / Slack Alert |
| `CloudPilotHighLatency` | N/A | N/A | 5 Mins | N/A | **P3 (Warning)** | Slack Alert |

---

## 3. Incident Triage Procedures

### Alert: `CloudPilotSLOFastBurn` (P1)
**Condition**: Error rate is burning the monthly budget 14.4x faster than acceptable.

#### Immediate Response Checklist
1. **Identify Failing Pods**:
   ```bash
   kubectl get pods -n cloudpilot -l app=cloudpilot -o wide
   ```
2. **Review Real-Time Application Logs**:
   ```bash
   kubectl logs -n cloudpilot -l app=cloudpilot --tail=100 -f
   ```
3. **Inspect Recent Kubernetes Events**:
   ```bash
   kubectl get events -n cloudpilot --sort-by='.lastTimestamp'
   ```
4. **Trigger AI Incident Diagnosis**:
   ```bash
   make ai-incident
   ```
5. **Check Active Simulations**:
   ```bash
   curl -s http://localhost:8000/api/v1/simulate/status
   # If test simulation is accidentally active, terminate it:
   curl -s -X DELETE http://localhost:8000/api/v1/simulate
   ```
6. **Execute Rollback if Caused by Recent Release**:
   ```bash
   kubectl rollout undo deployment/cloudpilot -n cloudpilot
   kubectl rollout status deployment/cloudpilot -n cloudpilot
   ```

---

## 4. Diagnostic PromQL Cheat Sheet

- **Current Request Rate**:
  ```promql
  sum(rate(cloudpilot_requests_total[1m]))
  ```
- **Error Rate Percentage**:
  ```promql
  sum(rate(cloudpilot_errors_total[5m])) / sum(rate(cloudpilot_requests_total[5m])) * 100
  ```
- **P99 Latency (Seconds)**:
  ```promql
  histogram_quantile(0.99, sum(rate(cloudpilot_request_duration_seconds_bucket[5m])) by (le))
  ```
- **Error Budget Burn Rate (1 Hour Window)**:
  ```promql
  (sum(rate(cloudpilot_errors_total[1h])) / sum(rate(cloudpilot_requests_total[1h]))) / (1 - 0.995)
  ```
