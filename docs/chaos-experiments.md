# CloudPilot Chaos Engineering & Resilience Playbook

## 1. Principles of Chaos Engineering in CloudPilot

Resilience cannot be verified in theory — it must be proven empirically under stress. CloudPilot's Chaos Engineering engine validates:
1. **Automated Detection Latency**: How quickly Prometheus and Kubernetes probes detect an outage.
2. **Mean Time to Recovery (MTTR)**: How fast the system returns to healthy state without human intervention.
3. **SLO Budget Consumption**: The empirical penalty against availability targets during failures.

---

## 2. Experiment Catalog

### Experiment 1: Pod Termination (Process Crash)
- **Hypothesis**: Terminating an active pod container will cause Kubernetes ReplicaSet to schedule a replacement replica within 15 seconds. Pod Disruption Budget (minAvailable: 2) prevents service disruption.
- **Trigger**:
  ```bash
  python3 chaos/failure_injector.py kill-pod
  ```
- **Observed Metrics**:
  - Detection Time: < 3 seconds
  - Recovery Time (MTTR): ~8.5 seconds
  - Availability Impact: 0.00% (seamless traffic redirection to remaining replicas)

### Experiment 2: Latency Degradation
- **Hypothesis**: Artificial 3000ms latency will trip the readiness probe, isolating the degraded pod from the endpoints pool while preserving process uptime.
- **Trigger**:
  ```bash
  python3 chaos/failure_injector.py inject-latency --duration 30 --latency-ms 3000
  ```
- **Observed Metrics**:
  - Detection Time: ~5.0 seconds
  - P99 Latency: Spikes to 3.2s
  - Recovery Time: ~1.8s after simulation expiry

### Experiment 3: Error Rate Burst (Systemic 500s)
- **Hypothesis**: A 50% error rate triggers Prometheus `CloudPilotSLOFastBurn` alert, creates an incident via AlertManager webhook, and updates the SLO tracker in real-time.
- **Trigger**:
  ```bash
  python3 chaos/failure_injector.py inject-errors --duration 30 --rate 50
  ```
- **Observed Metrics**:
  - Detection Time: ~2.0 seconds
  - Recovery Time: < 3.0 seconds
  - SLO Error Budget Consumed: ~4.2 minutes

### Experiment 4: CPU Starvation (Autoscaler Verification)
- **Hypothesis**: Heavy CPU loops consume container compute resources, pushing pod CPU utilization above 60% and triggering the Horizontal Pod Autoscaler (HPA) to scale replicas from 3 to 5+.
- **Trigger**:
  ```bash
  python3 chaos/failure_injector.py cpu-stress --duration 60
  ```
- **Observed Metrics**:
  - HPA Scale-Up Triggered: Yes (scaled to 5 replicas)
  - Time to Scale: ~45 seconds

---

## 3. Running Continuous Chaos

To execute all experiments in sequence and generate an automated report:
```bash
make chaos
```
Results are saved to `chaos-report.json` and printed in a formatted telemetry table.
