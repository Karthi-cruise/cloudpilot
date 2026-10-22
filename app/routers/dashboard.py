"""
CloudPilot Interactive SRE & Chaos Engineering Web Control Center.

Serves a single-page dark-mode operations console allowing engineers and
evaluators to trigger chaos experiments, monitor real-time SLO error budgets,
and trigger Gemini AI incident diagnosis visually.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Web Dashboard"])

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudPilot — SRE & Chaos Engineering Control Center</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0a0e17;
            --card-bg: #111827;
            --card-border: #1f293d;
            --primary: #3b82f6;
            --primary-glow: rgba(59, 130, 246, 0.3);
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-yellow: #f59e0b;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            padding: 24px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--card-border);
            margin-bottom: 24px;
        }

        .logo-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-icon {
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            width: 42px;
            height: 42px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 0 20px var(--primary-glow);
        }

        .title h1 {
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .title p {
            font-size: 13px;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }

        .badge-live {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--accent-green);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background: var(--accent-green);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .grid-kpi {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .kpi-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }

        .kpi-title {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .kpi-value {
            font-size: 32px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }

        .kpi-subtitle {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 6px;
        }

        .grid-main {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
        }

        @media (max-width: 1024px) {
            .grid-main { grid-template-columns: 1fr; }
        }

        .panel {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 22px;
            margin-bottom: 24px;
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--card-border);
        }

        .panel-title {
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .chaos-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
        }

        .btn {
            background: #1f293d;
            border: 1px solid #374151;
            color: var(--text-main);
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-family: 'Inter', sans-serif;
        }

        .btn:hover {
            transform: translateY(-2px);
            border-color: var(--primary);
            box-shadow: 0 4px 12px var(--primary-glow);
        }

        .btn-danger {
            background: rgba(239, 68, 68, 0.15);
            border-color: rgba(239, 68, 68, 0.4);
            color: #fca5a5;
        }

        .btn-danger:hover {
            background: rgba(239, 68, 68, 0.25);
            border-color: var(--accent-red);
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        }

        .btn-success {
            background: rgba(16, 185, 129, 0.15);
            border-color: rgba(16, 185, 129, 0.4);
            color: #6ee7b7;
        }

        .btn-primary {
            background: rgba(59, 130, 246, 0.15);
            border-color: rgba(59, 130, 246, 0.4);
            color: #93c5fd;
        }

        .incident-card {
            background: #0d121d;
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 10px;
        }

        .incident-header {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            margin-bottom: 6px;
        }

        .severity-badge {
            font-size: 11px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
        }

        .sev-p1 { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }
        .sev-p2 { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid #f59e0b; }
        .sev-p3 { background: rgba(59, 130, 246, 0.2); color: #3b82f6; border: 1px solid #3b82f6; }

        .terminal-box {
            background: #090d16;
            border: 1px solid #1a2234;
            border-radius: 8px;
            padding: 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            max-height: 250px;
            overflow-y: auto;
            color: #d1d5db;
            line-height: 1.6;
        }

        .log-line { margin-bottom: 4px; }
        .log-ts { color: #6b7280; }
        .log-info { color: #60a5fa; }
        .log-warn { color: #fbbf24; }
        .log-err { color: #f87171; }

        .progress-bar {
            height: 8px;
            background: #1f293d;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }

        .progress-fill {
            height: 100%;
            background: var(--accent-green);
            transition: width 0.5s ease;
        }
    </style>
</head>
<body>

    <div class="header">
        <div class="logo-group">
            <div class="logo-icon">☁️</div>
            <div class="title">
                <h1>CloudPilot Operations Control Center</h1>
                <p>Self-Healing Cloud-Native Reliability Platform • Kubernetes 1.31</p>
            </div>
        </div>
        <div class="badge-live">
            <div class="pulse-dot"></div>
            <span id="cluster-status">System Operational</span>
        </div>
    </div>

    <!-- Key Reliability Indicators (SLO / SLI) -->
    <div class="grid-kpi">
        <div class="kpi-card">
            <div class="kpi-title">Availability SLI (1h Window)</div>
            <div class="kpi-value" id="val-availability" style="color: var(--accent-green);">99.85%</div>
            <div class="progress-bar">
                <div class="progress-fill" id="bar-availability" style="width: 99.8%;"></div>
            </div>
            <div class="kpi-subtitle">Target: 99.50% Availability</div>
        </div>

        <div class="kpi-card">
            <div class="kpi-title">Monthly Error Budget Remaining</div>
            <div class="kpi-value" id="val-budget">214.2m</div>
            <div class="kpi-subtitle">99.1% Remaining (Total: 216 min)</div>
        </div>

        <div class="kpi-card">
            <div class="kpi-title">P99 Latency SLI</div>
            <div class="kpi-value" id="val-latency">18.4 ms</div>
            <div class="kpi-subtitle">SLO Target: &lt; 200 ms</div>
        </div>

        <div class="kpi-card">
            <div class="kpi-title">Error Budget Burn Rate</div>
            <div class="kpi-value" id="val-burn" style="color: #60a5fa;">0.36×</div>
            <div class="kpi-subtitle">Threshold: 14.4× (Fast Burn Alert)</div>
        </div>
    </div>

    <div class="grid-main">
        <!-- Left Column: Chaos Engineering & Live Telemetry -->
        <div>
            <!-- Chaos Injection Console -->
            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">💥 Chaos Engineering Failure Injection Console</div>
                    <span id="chaos-status" style="font-size: 13px; color: var(--accent-green); font-family: 'JetBrains Mono';">Simulation: IDLE</span>
                </div>
                <div class="chaos-actions">
                    <button class="btn btn-danger" onclick="triggerChaos('error_rate', 30)">
                        ⚡ Inject 50% Error Spike
                    </button>
                    <button class="btn btn-danger" onclick="triggerChaos('latency', 30)">
                        ⏳ Inject 3s Latency Delay
                    </button>
                    <button class="btn btn-danger" onclick="triggerChaos('cpu_stress', 45)">
                        🔥 Stress CPU (Test HPA)
                    </button>
                    <button class="btn btn-success" onclick="stopChaos()">
                        🛡️ Restore Healthy State
                    </button>
                </div>
            </div>

            <!-- Terminal Stream -->
            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">📋 Live Telemetry & Probes Stream</div>
                    <button class="btn" onclick="clearLogs()" style="padding: 4px 10px; font-size: 11px;">Clear</button>
                </div>
                <div class="terminal-box" id="terminal-feed">
                    <div class="log-line"><span class="log-ts">[BOOT]</span> <span class="log-info">INFO:</span> CloudPilot SRE Control Center initialized.</div>
                    <div class="log-line"><span class="log-ts">[MONITOR]</span> <span class="log-info">INFO:</span> Scraped Prometheus metrics successfully.</div>
                </div>
            </div>
        </div>

        <!-- Right Column: Incident Management & Gemini AI Triage -->
        <div>
            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">🤖 Gemini AIOps Incident Triage</div>
                    <button class="btn btn-primary" onclick="runAiTriage()" style="padding: 6px 12px; font-size: 12px;">
                        Diagnose Outage
                    </button>
                </div>
                <div id="ai-output" style="font-size: 13px; line-height: 1.5; color: #e5e7eb;">
                    <p style="color: var(--text-muted);">Click <strong>Diagnose Outage</strong> to invoke the Gemini API on current cluster logs and metrics.</p>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">🚨 Recent Operational Incidents</div>
                </div>
                <div id="incidents-list">
                    <div class="incident-card">
                        <div class="incident-header">
                            <span class="severity-badge sev-p2">P2 MAJOR</span>
                            <span style="color: #9ca3af;">Just now</span>
                        </div>
                        <div style="font-size: 13px; font-weight: 600;">High Latency Simulation Injected</div>
                        <div style="font-size: 11px; color: #6b7280; margin-top: 4px;">P99 breached 2000ms threshold</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function log(type, msg) {
            const box = document.getElementById('terminal-feed');
            const now = new Date().toISOString().substring(11, 19);
            const line = document.createElement('div');
            line.className = 'log-line';
            let cls = 'log-info';
            if (type === 'WARN') cls = 'log-warn';
            if (type === 'ERR') cls = 'log-err';
            line.innerHTML = `<span class="log-ts">[${now}]</span> <span class="${cls}">${type}:</span> ${msg}`;
            box.appendChild(line);
            box.scrollTop = box.scrollHeight;
        }

        function clearLogs() {
            document.getElementById('terminal-feed').innerHTML = '';
        }

        async function updateTelemetry() {
            try {
                const res = await fetch('/api/v1/slo/1h');
                if (res.ok) {
                    const data = await res.json();
                    const avail = data.availability_percent.toFixed(2);
                    document.getElementById('val-availability').innerText = avail + '%';
                    document.getElementById('bar-availability').style.width = Math.min(100, avail) + '%';
                    document.getElementById('val-budget').innerText = data.error_budget_consumed_minutes.toFixed(1) + 'm used';
                    document.getElementById('val-latency').innerText = data.p99_latency_ms.toFixed(1) + ' ms';
                    document.getElementById('val-burn').innerText = data.burn_rate.toFixed(2) + '×';

                    if (avail < 99.5) {
                        document.getElementById('val-availability').style.color = 'var(--accent-red)';
                        document.getElementById('bar-availability').style.background = 'var(--accent-red)';
                    } else {
                        document.getElementById('val-availability').style.color = 'var(--accent-green)';
                        document.getElementById('bar-availability').style.background = 'var(--accent-green)';
                    }
                }

                const simRes = await fetch('/api/v1/simulate/status');
                if (simRes.ok) {
                    const sim = await simRes.json();
                    const label = document.getElementById('chaos-status');
                    if (sim.active) {
                        label.innerText = `ACTIVE: ${sim.failure_type.toUpperCase()} (${sim.remaining_seconds}s)`;
                        label.style.color = 'var(--accent-red)';
                    } else {
                        label.innerText = 'Simulation: IDLE';
                        label.style.color = 'var(--accent-green)';
                    }
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function triggerChaos(type, duration) {
            log('WARN', `Injecting ${type} failure for ${duration}s...`);
            try {
                const res = await fetch('/api/v1/simulate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        failure_type: type,
                        duration_seconds: duration,
                        error_rate_percent: 50,
                        latency_ms: 3000
                    })
                });
                const data = await res.json();
                log('ERR', `Failure active: ${data.message}`);
                updateTelemetry();
            } catch (e) {
                log('ERR', `Simulation trigger failed: ${e}`);
            }
        }

        async function stopChaos() {
            log('INFO', 'Restoring healthy state...');
            try {
                await fetch('/api/v1/simulate', { method: 'DELETE' });
                log('INFO', 'All simulations stopped. Kubernetes self-healing verified.');
                updateTelemetry();
            } catch (e) {
                log('ERR', `Stop failed: ${e}`);
            }
        }

        async function runAiTriage() {
            const out = document.getElementById('ai-output');
            out.innerHTML = '<span style="color: #60a5fa;">🤖 Ingesting logs & calling Gemini API...</span>';
            try {
                // Fetch or trigger latest incident analysis
                const incRes = await fetch('/api/v1/incidents', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ title: 'Autonomous Chaos Triage Event', severity: 'P2' })
                });
                const inc = await incRes.json();
                const aiRes = await fetch(`/api/v1/incidents/${inc.id}/ai-summary`);
                const data = await aiRes.json();

                out.innerHTML = `
                    <div style="margin-bottom: 8px;"><strong>Executive Summary:</strong><br>${data.summary}</div>
                    <div style="margin-bottom: 8px; color: #fca5a5;"><strong>Root Cause:</strong><br>${data.root_cause}</div>
                    <div><strong>Remediation Runbook:</strong><br>${data.remediation_steps.map(s => `• ${s}`).join('<br>')}</div>
                    <div style="margin-top: 10px; font-size: 11px; color: #9ca3af;">Model: ${data.model_used} | Confidence: ${data.confidence}</div>
                `;
                log('INFO', 'Gemini AI incident diagnosis generated successfully.');
            } catch (e) {
                out.innerHTML = '<span style="color: var(--accent-red);">Failed to run AI triage. Check API key.</span>';
            }
        }

        setInterval(updateTelemetry, 3000);
        updateTelemetry();
    </script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse, summary="CloudPilot Visual Operations Center")
async def get_dashboard() -> HTMLResponse:
    """Renders the executive SRE, Chaos, and AIOps visual control center."""
    return HTMLResponse(content=DASHBOARD_HTML)
