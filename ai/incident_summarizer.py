"""
CloudPilot — Self-Healing Cloud-Native Reliability Platform
AI-powered incident analysis using Gemini API.
"""
import os
import json
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IncidentData:
    """Raw incident data collected from Kubernetes and the application."""
    incident_id: str
    title: str
    severity: str  # P1, P2, P3, P4
    started_at: datetime
    pod_logs: list[str]
    k8s_events: list[str]
    metrics_snapshot: dict
    failure_type: Optional[str] = None
    namespace: str = "cloudpilot"


@dataclass
class IncidentAnalysis:
    """Structured AI-generated incident analysis."""
    incident_id: str
    summary: str
    root_cause: str
    affected_components: list[str]
    remediation_steps: list[str]
    severity_assessment: str
    slo_impact: str
    prevention_measures: list[str]
    confidence: str  # high / medium / low
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    model_used: str = "gemini-3.8-flash"
    is_mock: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Remediation playbooks (rule-based — NOT the AI making infrastructure changes)
# ─────────────────────────────────────────────────────────────────────────────
REMEDIATION_PLAYBOOKS: dict[str, list[str]] = {
    "pod_crash": [
        "1. Check pod logs: kubectl logs <pod> -n cloudpilot --previous",
        "2. Describe pod for events: kubectl describe pod <pod> -n cloudpilot",
        "3. Check resource limits — OOMKilled means increase memory limits",
        "4. Verify readiness/liveness probes are correct",
        "5. Check if image pull is failing: kubectl get events -n cloudpilot",
        "6. Scale deployment to ensure healthy replicas: kubectl scale deploy cloudpilot --replicas=4",
        "7. If code bug, trigger rollback: kubectl rollout undo deploy/cloudpilot -n cloudpilot",
    ],
    "high_latency": [
        "1. Check P99 latency in Grafana — identify slow endpoints",
        "2. Review recent deployments: kubectl rollout history deploy/cloudpilot",
        "3. Check database connection pool saturation",
        "4. Review CPU throttling: kubectl top pods -n cloudpilot",
        "5. Check HPA status: kubectl get hpa -n cloudpilot",
        "6. If CPU-bound, scale up: kubectl scale deploy cloudpilot --replicas=6",
        "7. If external dependency, check downstream service health",
    ],
    "high_error_rate": [
        "1. Check error logs: kubectl logs -l app=cloudpilot -n cloudpilot | grep ERROR",
        "2. Identify most common error codes from Prometheus",
        "3. Check recent code changes or config changes",
        "4. Verify external dependencies (DB, third-party APIs) are healthy",
        "5. If 5xx errors, check for null pointer / unhandled exceptions in logs",
        "6. Consider rolling back: kubectl rollout undo deploy/cloudpilot",
        "7. Increase error budget alerting threshold temporarily during investigation",
    ],
    "oom": [
        "1. Confirm OOMKilled: kubectl get pod <pod> -o json | jq '.status.containerStatuses[].lastState.terminated.reason'",
        "2. Check memory trends in Grafana before OOM",
        "3. Profile memory usage: add memory profiling to identify leaks",
        "4. Increase memory limits in deployment temporarily",
        "5. Implement graceful degradation under memory pressure",
        "6. Set up memory limit alerts before OOM occurs",
    ],
    "cpu_throttling": [
        "1. Check CPU throttling: kubectl top pods -n cloudpilot",
        "2. Review CPU requests vs limits in deployment spec",
        "3. Profile CPU usage to identify hot code paths",
        "4. Consider increasing CPU limits or optimizing code",
        "5. Trigger HPA to scale out: kubectl annotate hpa cloudpilot-hpa scale-up=now",
        "6. Review if workload is better served by vertical scaling",
    ],
    "network_issue": [
        "1. Check network policies: kubectl get networkpolicies -n cloudpilot",
        "2. Test DNS resolution: kubectl exec -it <pod> -- nslookup kubernetes.default",
        "3. Verify service endpoints: kubectl get endpoints -n cloudpilot",
        "4. Check for port conflicts or firewall rules",
        "5. Review ingress configuration",
        "6. Test direct pod-to-pod connectivity",
    ],
}


class IncidentSummarizer:
    """
    AI-powered incident analysis using Gemini API.

    Falls back to mock mode if GEMINI_API_KEY is not configured.
    AI only ANALYZES and RECOMMENDS — it never executes infrastructure commands.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-3.8-flash"
        self._client = None
        self.mock_mode = not bool(self.api_key)

        if not self.mock_mode:
            try:
                from google import genai  # type: ignore
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Gemini AI incident summarizer initialized (live mode)")
            except ImportError:
                logger.warning("google-genai not installed. Falling back to mock mode.")
                self.mock_mode = True
            except Exception as exc:
                logger.warning("Failed to initialize Gemini client: %s. Using mock mode.", exc)
                self.mock_mode = True
        else:
            logger.info(
                "GEMINI_API_KEY not set — using mock incident analysis. "
                "Set GEMINI_API_KEY for real AI analysis."
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def analyze_incident(self, incident_data: IncidentData) -> IncidentAnalysis:
        """
        Analyze an incident using Gemini AI or mock mode.

        This method ONLY produces analysis and recommendations.
        It never executes any infrastructure commands.
        """
        if self.mock_mode or self._client is None:
            return self._mock_analysis(incident_data)

        try:
            return await self._gemini_analysis(incident_data)
        except Exception as exc:
            logger.error("Gemini analysis failed: %s. Falling back to mock.", exc)
            return self._mock_analysis(incident_data)

    async def get_remediation_playbook(self, failure_type: str) -> list[str]:
        """Return a rule-based remediation playbook for a given failure type."""
        normalized = failure_type.lower().replace(" ", "_").replace("-", "_")
        for key, steps in REMEDIATION_PLAYBOOKS.items():
            if key in normalized or normalized in key:
                return steps
        return [
            "1. Collect logs: kubectl logs -l app=cloudpilot -n cloudpilot",
            "2. Check events: kubectl get events -n cloudpilot --sort-by='.lastTimestamp'",
            "3. Review metrics in Grafana dashboard",
            "4. Check recent changes in GitHub Actions CI/CD history",
            "5. Escalate to on-call engineer if unresolved in 15 minutes",
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # Gemini API analysis
    # ─────────────────────────────────────────────────────────────────────────

    async def _gemini_analysis(self, incident_data: IncidentData) -> IncidentAnalysis:
        """Call Gemini API with structured JSON output."""
        prompt = self._build_prompt(incident_data)

        # JSON schema for structured output
        response_schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "root_cause": {"type": "string"},
                "affected_components": {"type": "array", "items": {"type": "string"}},
                "remediation_steps": {"type": "array", "items": {"type": "string"}},
                "severity_assessment": {"type": "string"},
                "slo_impact": {"type": "string"},
                "prevention_measures": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            },
            "required": [
                "summary", "root_cause", "affected_components",
                "remediation_steps", "severity_assessment",
                "slo_impact", "prevention_measures", "confidence",
            ],
        }

        interaction = self._client.interactions.create(  # type: ignore
            model=self.model,
            input=prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": response_schema,
                "temperature": 0.2,  # Low temp for consistent, factual analysis
            },
        )

        data = json.loads(interaction.output_text)
        return IncidentAnalysis(
            incident_id=incident_data.incident_id,
            summary=data["summary"],
            root_cause=data["root_cause"],
            affected_components=data["affected_components"],
            remediation_steps=data["remediation_steps"],
            severity_assessment=data["severity_assessment"],
            slo_impact=data["slo_impact"],
            prevention_measures=data["prevention_measures"],
            confidence=data["confidence"],
            model_used=self.model,
            is_mock=False,
        )

    def _build_prompt(self, d: IncidentData) -> str:
        """Build a rich, structured prompt for incident analysis."""
        logs_text = "\n".join(d.pod_logs[-50:]) if d.pod_logs else "No logs available"
        events_text = "\n".join(d.k8s_events[-20:]) if d.k8s_events else "No events"
        metrics_text = json.dumps(d.metrics_snapshot, indent=2)

        return f"""You are an expert Site Reliability Engineer (SRE) analyzing a production incident
for CloudPilot, a cloud-native platform running on Kubernetes.

## Incident Details
- ID: {d.incident_id}
- Title: {d.title}
- Severity: {d.severity}
- Started At: {d.started_at.isoformat()}
- Failure Type: {d.failure_type or 'Unknown'}
- Namespace: {d.namespace}

## Pod Logs (last 50 lines)
```
{logs_text}
```

## Kubernetes Events
```
{events_text}
```

## Metrics Snapshot at Time of Incident
```json
{metrics_text}
```

## Your Task
Analyze this incident and provide a structured JSON response with:
1. A concise executive summary (2-3 sentences)
2. Most likely root cause based on the evidence
3. Affected components (list of system components)
4. Prioritized remediation steps (numbered, specific kubectl/action commands)
5. Severity assessment (is the declared severity appropriate?)
6. SLO impact (how this affects availability, error budget)
7. Prevention measures (how to prevent recurrence)
8. Confidence level in your analysis (high/medium/low with brief reason)

Be specific and actionable. Reference actual log lines and metrics where relevant.
Focus on observable evidence — do not speculate without supporting data.

IMPORTANT: Only recommend analysis and investigation steps.
Do not recommend autonomous infrastructure changes without human approval.
"""

    # ─────────────────────────────────────────────────────────────────────────
    # Mock analysis (when no API key)
    # ─────────────────────────────────────────────────────────────────────────

    def _mock_analysis(self, incident_data: IncidentData) -> IncidentAnalysis:
        """Generate realistic mock analysis for demo/testing purposes."""
        failure_playbooks = {
            "latency": {
                "summary": (
                    f"Incident {incident_data.incident_id}: Elevated P99 latency detected "
                    "in CloudPilot API service. Requests exceeding 3000ms threshold affecting "
                    "user experience. SLO error budget consumption rate is elevated."
                ),
                "root_cause": (
                    "Artificial latency injection via /api/v1/simulate endpoint causing "
                    "all request handlers to sleep for configured duration. This is consistent "
                    "with intentional chaos engineering experiment or configuration error."
                ),
                "affected_components": ["cloudpilot-api", "load-balancer", "health-probes"],
                "remediation_steps": [
                    "1. Check active simulations: GET /api/v1/simulate/status",
                    "2. Stop simulation if active: DELETE /api/v1/simulate",
                    "3. Verify readiness probe passes: GET /ready",
                    "4. Check P99 latency returning to baseline in Grafana",
                    "5. Review error budget remaining: GET /api/v1/slo/error-budget",
                ],
                "slo_impact": (
                    "High. P99 latency SLI breached (target: 200ms, actual: 3000+ms). "
                    "Error budget consuming at elevated burn rate. "
                    "Availability SLO may be unaffected if readiness probe not failing."
                ),
                "confidence": "high",
            },
            "error_rate": {
                "summary": (
                    f"Incident {incident_data.incident_id}: HTTP 500 error rate spike "
                    "detected. Error budget burn rate exceeds fast-burn threshold. "
                    "Immediate investigation required."
                ),
                "root_cause": (
                    "Error rate injection via failure simulation causing systematic "
                    "HTTP 500 responses. Application logic deliberately returning errors "
                    "for configured percentage of requests."
                ),
                "affected_components": ["cloudpilot-api", "prometheus-alertmanager", "slo-tracker"],
                "remediation_steps": [
                    "1. Stop error injection: DELETE /api/v1/simulate",
                    "2. Verify error rate returning to baseline",
                    "3. Calculate error budget consumed: GET /api/v1/slo/error-budget",
                    "4. Create incident record: POST /api/v1/incidents",
                    "5. Review Prometheus alerts in AlertManager",
                ],
                "slo_impact": (
                    "Critical. Availability SLO directly impacted. "
                    "Error budget consuming at fast-burn rate (>14.4x). "
                    "Monthly error budget could be exhausted in under 1 hour at this rate."
                ),
                "confidence": "high",
            },
            "cpu_stress": {
                "summary": (
                    f"Incident {incident_data.incident_id}: CPU utilization spike detected. "
                    "HPA may be triggered. Service may be throttled affecting latency."
                ),
                "root_cause": (
                    "CPU stress test injected via chaos engineering. "
                    "CPU-intensive background computation consuming all available cores. "
                    "Container CPU limits causing throttling and increased request latency."
                ),
                "affected_components": ["cloudpilot-pod", "hpa-controller", "node-resource-manager"],
                "remediation_steps": [
                    "1. Stop CPU stress: DELETE /api/v1/simulate",
                    "2. Check HPA scaled out correctly: kubectl get hpa -n cloudpilot",
                    "3. Monitor CPU returning to baseline: kubectl top pods -n cloudpilot",
                    "4. Review if CPU limits need adjustment",
                    "5. Check for CPU throttling: container_cpu_cfs_throttled_seconds_total",
                ],
                "slo_impact": (
                    "Medium. Latency SLI may be affected due to CPU throttling. "
                    "HPA should auto-scale to mitigate. "
                    "Monitor error budget for any availability impact."
                ),
                "confidence": "medium",
            },
        }

        failure_type = incident_data.failure_type or "unknown"
        playbook = failure_playbooks.get(
            failure_type,
            {
                "summary": (
                    f"Incident {incident_data.incident_id}: Anomaly detected in CloudPilot service. "
                    "Manual investigation required to determine root cause."
                ),
                "root_cause": (
                    "Insufficient data to determine root cause with confidence. "
                    "Review logs and metrics for correlated events around the incident start time."
                ),
                "affected_components": ["cloudpilot-api"],
                "remediation_steps": [
                    "1. Collect logs: kubectl logs -l app=cloudpilot -n cloudpilot",
                    "2. Check events: kubectl get events -n cloudpilot --sort-by='.lastTimestamp'",
                    "3. Review metrics in Grafana dashboard",
                    "4. Check recent deployments: kubectl rollout history deploy/cloudpilot",
                ],
                "slo_impact": "Unknown. Monitor SLO dashboard for availability impact.",
                "confidence": "low",
            },
        )

        return IncidentAnalysis(
            incident_id=incident_data.incident_id,
            summary=playbook["summary"],
            root_cause=playbook["root_cause"],
            affected_components=playbook["affected_components"],
            remediation_steps=playbook["remediation_steps"],
            severity_assessment=(
                f"Declared severity {incident_data.severity} appears appropriate "
                "based on available metrics and impact assessment."
            ),
            slo_impact=playbook["slo_impact"],
            prevention_measures=[
                "Implement pre-production chaos testing in CI/CD pipeline",
                "Add automated rollback on error rate threshold breach",
                "Set up proactive alerting before SLO budget is 50% consumed",
                "Conduct monthly game days to validate recovery procedures",
                "Document all simulation experiments with expected vs actual behavior",
            ],
            confidence=playbook["confidence"],
            model_used="mock-analysis",
            is_mock=True,
        )
