# Running the Full CyberSentinel AI Platform

You need 5 terminal windows open at once — one per service, plus the aggregator.
Each service is independent; if one isn't running yet, the others still work
fine (the dashboard just shows it as "offline").

## Terminal 1 — Phishing Detection (port 8001)
cd services\phishing-detect
python -m uvicorn main:app --port 8001

## Terminal 2 — Network IDS (port 8002)
cd services\network-ids
python -m uvicorn main:app --port 8002

## Terminal 3 — Auth Anomaly (port 8003)
cd services\auth-anomaly
python -m uvicorn main:app --port 8003

## Terminal 4 — Prompt Guard (port 8004)
cd services\prompt-guard
python -m uvicorn main:app --port 8004

## Terminal 5 — Event-Bus Aggregator (port 8000) — start this LAST
cd event-bus
pip install -r requirements.txt
python -m uvicorn aggregator:app --port 8000

## Then open the dashboard
Double-click dashboard/index.html (or right-click -> Open with -> your browser).
No build step, no npm install — it's a single static HTML file that talks to
the aggregator over fetch().

You should see all four module status dots turn green within a few seconds.
Click "Simulate attack" to fire one real malicious input at each module and
watch alerts populate the live feed in real time — this is your demo moment.

## Common issue
If a status dot stays grey, that service either isn't running or crashed on
startup — check that terminal window for a traceback (most likely cause:
you're in the wrong folder, or the model wasn't retrained after a fresh
git clone / zip extraction — run python train.py in that service's folder
first).
