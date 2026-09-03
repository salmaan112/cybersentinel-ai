# Build from REPO ROOT: docker build -f services/prompt-guard/Dockerfile -t prompt-guard .
FROM python:3.11-slim
WORKDIR /app
COPY services/prompt-guard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/prompt-guard/ ./services/prompt-guard/
COPY event-bus/ ./event-bus/
WORKDIR /app/services/prompt-guard
EXPOSE 8004
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
