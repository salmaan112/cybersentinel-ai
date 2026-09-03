# Build from REPO ROOT: docker build -f services/network-ids/Dockerfile -t network-ids .
FROM python:3.11-slim
WORKDIR /app
COPY services/network-ids/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/network-ids/ ./services/network-ids/
COPY event-bus/ ./event-bus/
WORKDIR /app/services/network-ids
EXPOSE 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
