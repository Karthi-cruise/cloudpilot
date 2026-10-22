#!/usr/bin/env bash
# ==============================================================================
# CloudPilot Chaos Experiment Runner
# ==============================================================================

set -euo pipefail

echo "💥 Running CloudPilot Chaos Engineering Experiment Suite..."
python3 chaos/failure_injector.py full-experiment
echo "📊 Fetching live SLO impact..."
python3 sre/slo_calculator.py --window 1h || true
echo "💰 Generating capacity cost report..."
python3 sre/cost_estimator.py || true
