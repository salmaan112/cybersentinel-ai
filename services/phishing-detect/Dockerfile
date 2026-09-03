# Build this from the REPO ROOT, not from inside services/phishing-detect/:
#   docker build -f services/phishing-detect/Dockerfile -t phishing-detect .
# (docker-compose.yml at the repo root already does this correctly.)
# This is necessary because the service imports event-bus/schema.py, which
# must be copied into the image alongside the service's own code.
FROM python:3.11-slim

WORKDIR /app

COPY services/phishing-detect/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/phishing-detect/ ./services/phishing-detect/
COPY event-bus/ ./event-bus/

WORKDIR /app/services/phishing-detect

# Model must already exist (model.joblib committed, or trained in an earlier
# CI/build step) — training inside the image build would bake stale data
# into every rebuild and make builds slow. See README.

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
