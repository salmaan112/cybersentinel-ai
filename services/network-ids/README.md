# Network-IDS Service

## Setup
pip install -r requirements.txt

## Train (already run once — model.joblib, label_encoders.joblib included)
python3 train.py

## Run the API
uvicorn main:app --reload --port 8002

## Test
curl -X POST http://localhost:8002/analyze-traffic \
  -H "Content-Type: application/json" \
  -d '{"protocol_type":"tcp","service":"private","flag":"S0","count":123,"serror_rate":1.0,"source_ip":"203.0.113.9"}'

## Metrics (NSL-KDD official test set, binary normal-vs-attack)
- Accuracy: 80.3%
- Precision: 96.8%
- Recall: 67.7%
- ROC AUC: 0.969

## Known limitation (v1)
Recall of 67.7% means roughly a third of attacks in the test set are missed.
This is a well-documented property of NSL-KDD's test set, which deliberately
includes attack subtypes absent from training (unlike the phishing dataset).
Planned v2 fix: add an unsupervised anomaly detector (Isolation Forest,
trained only on normal traffic) as a second layer to catch attacks the
supervised classifier hasn't seen before — this is standard practice in
real IDS systems (signature-based + anomaly-based detection combined).
