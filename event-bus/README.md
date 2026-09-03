# Event-Bus Aggregator

## Setup
pip install -r requirements.txt

## Run
uvicorn aggregator:app --reload --port 8000

Must be started AFTER the four module services (ports 8001-8004) are already
running, since it polls their /alerts and /health endpoints.
