Make it executable:

chmod +x scripts/setup_observability.sh


Run it anytime (after sam deploy):

AWS_REGION=ca-central-1 ALERT_EMAIL="you@example.com" ./scripts/setup_observability.sh


scripts/teardown_observability.sh