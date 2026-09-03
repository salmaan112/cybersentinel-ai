# Build from REPO ROOT: docker build -f services/auth-anomaly/Dockerfile -t auth-anomaly .
FROM python:3.11-slim
WORKDIR /app
COPY services/auth-anomaly/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/auth-anomaly/ ./services/auth-anomaly/
COPY event-bus/ ./event-bus/
WORKDIR /app/services/auth-anomaly
EXPOSE 8003
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
