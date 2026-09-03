# Phishing-Detect Service

## Setup
pip install -r requirements.txt

## Train (already run once, model.joblib included)
python3 train.py

## Run the API
uvicorn main:app --reload --port 8001

## Test
curl -X POST http://localhost:8001/check-url \
  -H "Content-Type: application/json" \
  -d '{"url": "http://secure-paypal-login.verify-account.tk"}'

## Known limitations (v1)
- Network-dependent features (domain age, SSL cert, Google-index status)
  are excluded — model uses only URL-string-computable features. This
  keeps the service fast with no external calls, but caps ceiling accuracy.
- Raw IP-based phishing URLs are under-detected (~0.36 risk score) — needs
  more IP-based phishing examples in training data. Documented as v2 work.
- Benign class was augmented with 20 real deep-link URLs (x15 each) to fix
  a dataset bias where any URL path length was treated as suspicious.
