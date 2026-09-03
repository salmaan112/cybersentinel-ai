# Build from REPO ROOT: docker build -f event-bus/Dockerfile -t event-bus .
FROM python:3.11-slim
WORKDIR /app
COPY event-bus/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY event-bus/ .
EXPOSE 8000
CMD ["uvicorn", "aggregator:app", "--host", "0.0.0.0", "--port", "8000"]
