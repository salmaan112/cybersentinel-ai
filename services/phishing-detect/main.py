"""
Phishing-Detect microservice.
POST /check-url  -> risk score + verdict
Emits an Alert (shared schema) whenever a URL scores above the medium threshold.
"""
import sys
import os
import joblib
from fastapi import FastAPI
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "event-bus"))
from schema import Alert, Module, Severity, score_to_severity  # noqa: E402
from features import url_to_dataframe  # noqa: E402

app = FastAPI(title="CyberSentinel — Phishing Detect")
model = joblib.load(os.path.join(os.path.dirname(__file__), "model.joblib"))

# In-memory alert log for now — Phase 5 swaps this for the real Redis/DB event bus
ALERT_LOG: list[Alert] = []


class URLCheckRequest(BaseModel):
    url: str


class URLCheckResponse(BaseModel):
    url: str
    risk_score: float
    severity: Severity
    verdict: str
    alert_raised: bool


@app.post("/check-url", response_model=URLCheckResponse)
def check_url(req: URLCheckRequest):
    features_df = url_to_dataframe(req.url)
    risk_score = float(model.predict_proba(features_df)[0][1])
    severity = score_to_severity(risk_score)
    verdict = "phishing" if risk_score >= 0.5 else "legitimate"

    alert_raised = severity in (Severity.medium, Severity.high, Severity.critical)
    if alert_raised:
        alert = Alert(
            module=Module.phishing,
            severity=severity,
            score=risk_score,
            source=req.url,
            details={"verdict": verdict},
        )
        ALERT_LOG.append(alert)

    return URLCheckResponse(
        url=req.url,
        risk_score=round(risk_score, 4),
        severity=severity,
        verdict=verdict,
        alert_raised=alert_raised,
    )


@app.get("/alerts")
def get_alerts():
    """Temporary endpoint so the dashboard (Phase 5) has something to poll
    before the real event bus is wired in."""
    return ALERT_LOG


@app.get("/health")
def health():
    return {"status": "ok", "module": "phishing-detect"}
