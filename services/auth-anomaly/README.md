# Auth-Anomaly Service

## Setup
pip install -r requirements.txt

## Generate data + train (already run once — model.joblib included)
python3 generate_data.py
python3 train.py

## Run the API
uvicorn main:app --reload --port 8003

## Test
curl -X POST http://localhost:8003/check-login \
  -H "Content-Type: application/json" \
  -d '{"current":{"user_id":"user_0042","timestamp":"2026-08-01T03:00:14","ip":"198.51.100.7","lat":51.5074,"lon":-0.1278,"success":0},"recent_history":[]}'

## Metrics
- Accuracy: 99.9%, Precision: 96.4%, Recall: 100%, ROC AUC: 1.0

## Design notes (important for your write-up)
- No real login data was used anywhere — all events are synthetic (Faker +
  explicit rule-based generation), by design, since real credential logs
  are sensitive.
- First training pass scored a suspicious 100% across every metric — this
  was a genuine finding, not a good result: the synthetic attacks were
  trivially separable from normal behavior on a single feature
  (failed_attempts_from_ip_5min). Fixed by adding realistic-but-benign
  edge cases (typo-retry logins, shared office IPs, legitimate business
  travel) to the normal class, forcing the model to learn a real decision
  boundary instead of one hard threshold.
- API design note: the caller supplies recent_history because this service
  is stateless — in production this window would come from a real
  events table/Redis cache keyed by user_id and ip, not from the caller.
