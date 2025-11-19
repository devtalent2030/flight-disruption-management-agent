#!/usr/bin/env bash
set -euo pipefail

# ---------- Config ----------
AWS_REGION="${AWS_REGION:-ca-central-1}"
DASHBOARD_NAME="${DASHBOARD_NAME:-FDMA-Demo}"
ALERT_EMAIL="${ALERT_EMAIL:-}"             # set if you want email alerts (alarms + budget)
BUDGET_NAME="${BUDGET_NAME:-FDMA-Demo-Monthly}"
BUDGET_LIMIT_USD="${BUDGET_LIMIT_USD:-25}"
# Lambda name fragments to auto-resolve (adjust if you rename)
WANTED_FUNCS=("event_simulator" "impacted_pnr_finder" "options_scoring" "create_offer" "notify_passenger" "decision_api")

# ---------- Helpers ----------
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1"; exit 1; }; }
need aws; need jq

log() { printf "\n\033[1;36m[FDMA]\033[0m %s\n" "$*"; }

# ---------- Discover resources ----------
log "Discovering resources in $AWS_REGION ..."
STATE_MACHINE_ARN="$(aws stepfunctions list-state-machines --region "$AWS_REGION" \
  --query 'stateMachines[].stateMachineArn' --output text | tr '\t' '\n' | head -n1 || true)"
LAMBDA_JSON="/tmp/fdma-lambdas.json"
aws lambda list-functions --region "$AWS_REGION" > "$LAMBDA_JSON"

RESOLVED_FUNCS=()
for frag in "${WANTED_FUNCS[@]}"; do
  name="$(jq -r --arg f "$frag" '.Functions[] | select(.FunctionName|contains($f)) .FunctionName' "$LAMBDA_JSON" | head -n1)"
  [[ -n "$name" && "$name" != "null" ]] && RESOLVED_FUNCS+=("$name")
done

REST_API_ID="$(aws apigateway get-rest-apis --region "$AWS_REGION" \
  --query 'items[].{id:id,name:name}[?contains(name, `decision`) || contains(name, `Decision`) || contains(name, `fdma`)].id' \
  --output text 2>/dev/null | head -n1 || true)"
HTTP_API_ID="$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
  --query 'Items[].{id:ApiId,name:Name}[?contains(Name, `decision`) || contains(Name, `Decision`) || contains(Name, `fdma`)].id' \
  --output text 2>/dev/null | head -n1 || true)"

DDB_OFFERS="$(aws dynamodb list-tables --region "$AWS_REGION" --query 'TableNames[]' --output text | tr '\t' '\n' | grep -i '^Offers$'   | head -n1 || true)"
DDB_PNRS="$(  aws dynamodb list-tables --region "$AWS_REGION" --query 'TableNames[]' --output text | tr '\t' '\n' | grep -i '^PNRs$'     | head -n1 || true)"
DDB_VOUCHERS="$(aws dynamodb list-tables --region "$AWS_REGION" --query 'TableNames[]' --output text | tr '\t' '\n' | grep -i '^Vouchers$'| head -n1 || true)"

log "State Machine: ${STATE_MACHINE_ARN:-<none>}"
log "Lambdas: ${RESOLVED_FUNCS[*]:-<none>}"
log "API (REST): ${REST_API_ID:-<none>} | API (HTTPv2): ${HTTP_API_ID:-<none>}"
log "DynamoDB: Offers=${DDB_OFFERS:-<none>} PNRs=${DDB_PNRS:-<none>} Vouchers=${DDB_VOUCHERS:-<none>}"

# ---------- Build Dashboard JSON ----------
LAMBDA_WIDGETS='[]'
for fn in "${RESOLVED_FUNCS[@]}"; do
  W=$(jq -n --arg r "$AWS_REGION" --arg fn "$fn" '
    {"type":"metric","x":0,"y":0,"width":6,"height":6,
     "properties":{"region":$r,"title":("Lambda: "+$fn),
       "metrics":[
         ["AWS/Lambda","Invocations","FunctionName",$fn,{"stat":"Sum"}],
         ["...","Errors","FunctionName",$fn,{"stat":"Sum","yAxis":"right"}],
         ["...","Duration","FunctionName",$fn,{"stat":"p90"}]
       ],
       "view":"timeSeries","stacked":false,"period":60,"legend":{"position":"bottom"}}}')
  LAMBDA_WIDGETS=$(jq -n --argjson arr "$LAMBDA_WIDGETS" --argjson w "$W" '$arr + [$w]')
done

SFN_WIDGET=$(jq -n --arg r "$AWS_REGION" --arg arn "$STATE_MACHINE_ARN" '
  if ($arn|length)>0 then
    {"type":"metric","x":0,"y":0,"width":12,"height":6,
     "properties":{"region":$r,"title":"Step Functions: Executions",
       "metrics":[
         ["AWS/States","ExecutionsStarted","StateMachineArn",$arn,{"stat":"Sum"}],
         ["...","ExecutionsSucceeded","StateMachineArn",$arn,{"stat":"Sum"}],
         ["...","ExecutionsFailed","StateMachineArn",$arn,{"stat":"Sum"}],
         ["...","ExecutionTime","StateMachineArn",$arn,{"stat":"p90"}]
       ],
       "view":"timeSeries","stacked":false,"period":60,"legend":{"position":"bottom"}}}
  else
    {"type":"text","x":0,"y":0,"width":12,"height":6,"properties":{"markdown":"**Step Functions** not found"}}
  end
')

API_WIDGET=$(jq -n --arg r "$AWS_REGION" --arg rest "$REST_API_ID" --arg http "$HTTP_API_ID" '
  if ($rest|length)>0 then
    {"type":"metric","x":12,"y":0,"width":12,"height":6,
     "properties":{"region":$r,"title":"API Gateway (REST): 4XX / 5XX",
       "metrics":[
         ["AWS/ApiGateway","4XXError","ApiId",$rest,{"stat":"Sum"}],
         ["...","5XXError","ApiId",$rest,{"stat":"Sum"}],
         ["...","Latency","ApiId",$rest,{"stat":"p90"}]
       ],
       "view":"timeSeries","stacked":false,"period":60}}
  elif ($http|length)>0 then
    {"type":"metric","x":12,"y":0,"width":12,"height":6,
     "properties":{"region":$r,"title":"API Gateway (HTTP v2): 4XX / 5XX",
       "metrics":[
         ["AWS/ApiGateway","4XXError","ApiId",$http,{"stat":"Sum"}],
         ["...","5XXError","ApiId",$http,{"stat":"Sum"}],
         ["...","Latency","ApiId",$http,{"stat":"p90"}]
       ],
       "view":"timeSeries","stacked":false,"period":60}}
  else
    {"type":"text","x":12,"y":0,"width":12,"height":6,"properties":{"markdown":"**API Gateway** not found"}}
  end
')

DDB_WIDGET=$(jq -n --arg r "$AWS_REGION" --arg o "$DDB_OFFERS" --arg p "$DDB_PNRS" --arg v "$DDB_VOUCHERS" '
  {"type":"metric","x":0,"y":6,"width":24,"height":6,
   "properties":{"region":$r,"title":"DynamoDB: Throttle & Latency",
     "metrics":[
       (if ($o|length)>0 then ["AWS/DynamoDB","ThrottledRequests","TableName",$o,{"stat":"Sum"}] else empty end),
       (if ($o|length)>0 then ["...","SuccessfulRequestLatency","TableName",$o,{"stat":"p90"}] else empty end),
       (if ($p|length)>0 then ["AWS/DynamoDB","ThrottledRequests","TableName",$p,{"stat":"Sum"}] else empty end),
       (if ($p|length)>0 then ["...","SuccessfulRequestLatency","TableName",$p,{"stat":"p90"}] else empty end),
       (if ($v|length)>0 then ["AWS/DynamoDB","ThrottledRequests","TableName",$v,{"stat":"Sum"}] else empty end),
       (if ($v|length)>0 then ["...","SuccessfulRequestLatency","TableName",$v,{"stat":"p90"}] else empty end)
     ],
     "view":"timeSeries","stacked":false,"period":60}}')

FDMA_WIDGET=$(jq -n --arg r "$AWS_REGION" '
  {"type":"metric","x":0,"y":12,"width":24,"height":6,
   "properties":{"region":$r,"title":"FDMA KPIs",
     "metrics":[
       ["FDMA","OffersCreated",{"stat":"Sum"}],
       ["FDMA","OfferAccepted",{"stat":"Sum"}],
       ["FDMA","OfferDeclined",{"stat":"Sum"}],
       ["FDMA","TimeToFirstOfferMs",{"stat":"p90"}]
     ],
     "view":"timeSeries","stacked":false,"period":60}}')

DASH="/tmp/fdma-dashboard.json"
jq -n \
  --argjson sfn "$SFN_WIDGET" \
  --argjson api "$API_WIDGET" \
  --argjson ddb "$DDB_WIDGET" \
  --argjson kpi "$FDMA_WIDGET" \
  --argjson lambdas "$LAMBDA_WIDGETS" '
  {"widgets": ([ $sfn, $api, $ddb, $kpi ] + $lambdas)}' > "$DASH"

log "Putting CloudWatch dashboard: $DASHBOARD_NAME"
aws cloudwatch put-dashboard --region "$AWS_REGION" \
  --dashboard-name "$DASHBOARD_NAME" \
  --dashboard-body "file://$DASH"

log "Dashboard ready:
https://${AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=${DASHBOARD_NAME}"

# ---------- Basic Alarms (optional, needs ALERT_EMAIL) ----------
if [[ -n "${ALERT_EMAIL}" ]]; then
  log "Ensuring SNS topic + subscription for alarms"
  TOPIC_ARN="$(aws sns create-topic --name fdma-alarms --query 'TopicArn' --output text --region "$AWS_REGION")"
  aws sns subscribe --topic-arn "$TOPIC_ARN" --protocol email --notification-endpoint "$ALERT_EMAIL" --region "$AWS_REGION" >/dev/null || true

  # Alarm: any Step Functions failure
  if [[ -n "$STATE_MACHINE_ARN" ]]; then
    aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
      --alarm-name "FDMA-SFN-Failures" \
      --alarm-description "Step Functions failed executions > 0 over 5m" \
      --metric-name "ExecutionsFailed" \
      --namespace "AWS/States" \
      --statistic Sum --period 300 --evaluation-periods 1 \
      --threshold 0 --comparison-operator GreaterThanThreshold \
      --dimensions "Name=StateMachineArn,Value=${STATE_MACHINE_ARN}" \
      --treat-missing-data notBreaching \
      --alarm-actions "$TOPIC_ARN"
  fi

  # Alarm: any Lambda errors across your resolved functions (creates one per function)
  for fn in "${RESOLVED_FUNCS[@]}"; do
    aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
      --alarm-name "FDMA-LambdaErrors-${fn}" \
      --alarm-description "Lambda errors > 0 over 5m for ${fn}" \
      --metric-name "Errors" \
      --namespace "AWS/Lambda" \
      --statistic Sum --period 300 --evaluation-periods 1 \
      --threshold 0 --comparison-operator GreaterThanThreshold \
      --dimensions "Name=FunctionName,Value=${fn}" \
      --treat-missing-data notBreaching \
      --alarm-actions "$TOPIC_ARN"
  done

  log "Alarms created. Check your email to confirm the SNS subscription to receive alerts."
fi

# ---------- Budget (account-wide, idempotent) ----------
if [[ -n "${ALERT_EMAIL}" ]]; then
  log "Ensuring monthly cost budget: ${BUDGET_NAME} ($${BUDGET_LIMIT_USD})"
  ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
  set +e
  aws budgets describe-budget --account-id "$ACCOUNT_ID" --budget-name "$BUDGET_NAME" >/dev/null 2>&1
  EXIST=$?
  set -e

  if [[ $EXIST -ne 0 ]]; then
    aws budgets create-budget \
      --account-id "$ACCOUNT_ID" \
      --budget "{
        \"BudgetName\":\"$BUDGET_NAME\",
        \"BudgetLimit\": {\"Amount\":\"$BUDGET_LIMIT_USD\",\"Unit\":\"USD\"},
        \"TimeUnit\":\"MONTHLY\",\"BudgetType\":\"COST\",
        \"TimePeriod\": {\"Start\":\"$(date -u +\"%Y-%m-01T00:00:00Z\")\"}
      }" \
      --notifications-with-subscribers "[
        {\"Notification\":{\"NotificationType\":\"ACTUAL\",\"ComparisonOperator\":\"GREATER_THAN\",\"Threshold\":80,\"ThresholdType\":\"PERCENTAGE\"},
         \"Subscribers\":[{\"SubscriptionType\":\"EMAIL\",\"Address\":\"$ALERT_EMAIL\"}]},
        {\"Notification\":{\"NotificationType\":\"ACTUAL\",\"ComparisonOperator\":\"GREATER_THAN\",\"Threshold\":100,\"ThresholdType\":\"PERCENTAGE\"},
         \"Subscribers\":[{\"SubscriptionType\":\"EMAIL\",\"Address\":\"$ALERT_EMAIL\"}]}
      ]" >/dev/null
    log "Budget created and wired to $ALERT_EMAIL"
  else
    log "Budget already exists; skipping create."
  fi
fi

log "✅ Observability setup complete."
