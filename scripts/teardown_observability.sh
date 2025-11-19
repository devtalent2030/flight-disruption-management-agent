#!/usr/bin/env bash
set -euo pipefail
AWS_REGION="${AWS_REGION:-ca-central-1}"
DASHBOARD_NAME="${DASHBOARD_NAME:-FDMA-Demo}"

aws cloudwatch delete-dashboards --dashboard-names "$DASHBOARD_NAME" --region "$AWS_REGION" || true
for name in $(aws cloudwatch describe-alarms --query 'MetricAlarms[?starts_with(AlarmName, `FDMA-`)].AlarmName' --output text --region "$AWS_REGION"); do
  aws cloudwatch delete-alarms --alarm-names "$name" --region "$AWS_REGION" || true
done
echo "✅ Observability teardown complete."
