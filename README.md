# Flight Disruption Management Agent (FDMA)

AWS-native, serverless prototype that detects flight delays/cancellations, finds impacted PNRs, proposes rebooking options, and captures passenger confirmation.

## Tech
- **AWS**: EventBridge, Lambda, Step Functions, DynamoDB, API Gateway, SNS/Pinpoint (stubs)
- **IaC**: AWS SAM
- **CI**: GitHub Actions (lint + unit tests)

## Local Dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
pytest
```

## Deploy (SAM)
```bash
sam build
sam deploy --guided
```
This deploys:
- Lambdas: `event_simulator`, `impacted_pnr_finder`
- Step Functions: `fdma_state_machine`
- DynamoDB tables: `FDMA_Passengers`, `FDMA_PNRs`, `FDMA_Events`, `FDMA_Offers`

## Jira Linking (GitHub ↔ Jira Cloud)
1. In **Jira**: Project settings → **Integrations** → **Git repositories** → Connect **GitHub** (install *GitHub for Jira* app if prompted).
2. In **GitHub**: Create repo and push this code.
3. Use commit messages and PR titles like: `FDMA-1: scaffold repo + CI`. Jira will auto-link to issue **FDMA-1**.

## Suggested Branch & PR Flow
```bash
git checkout -b feature/FDMA-1-ci-skeleton
git add .
git commit -m "FDMA-1: bootstrap repo, SAM, CI, sample lambdas"
git push -u origin feature/FDMA-1-ci-skeleton
# open PR with title: FDMA-1: bootstrap repo, SAM, CI, sample lambdas
```
