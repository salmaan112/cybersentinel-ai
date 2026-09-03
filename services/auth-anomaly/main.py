"""
Auth-Anomaly microservice.
POST /check-login -> risk score for a single login event, given recent
history for that user/IP (the caller passes in the small window of prior
events needed to compute velocity features — in a real deployment this
would come from a login-events table/cache, not the caller).
"""
import sys
import os
import json
import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "event-bus"))
from schema import Alert, Module, Severity, score_to_severity  # noqa: E402
from features import engineer_features  # noqa: E402

HERE = os.path.dirname(__file__)
app = FastAPI(title="CyberSentinel — Auth Anomaly")

model = joblib.load(os.path.join(HERE, "model.joblib"))
with open(os.path.join(HERE, "model_features.json")) as f:
    FEATURE_ORDER = json.load(f)

ALERT_LOG: list[Alert] = []


class LoginEvent(BaseModel):
    user_id: str
    timestamp: datetime
    ip: str
    lat: float
    lon: float
    success: int = 1


class LoginCheckRequest(BaseModel):
    current: LoginEvent
    recent_history: List[LoginEvent] = []  # this user's/IP's recent prior events


class LoginCheckResponse(BaseModel):
    risk_score: float
    severity: Severity
    verdict: str
    alert_raised: bool


@app.post("/check-login", response_model=LoginCheckResponse)
def check_login(req: LoginCheckRequest):
    events = [e.model_dump() for e in req.recent_history] + [req.current.model_dump()]
    df = pd.DataFrame(events)
    df["city"] = "unknown"
    df["label"] = "normal"

    engineered, _ = engineer_features(df)
    last_row = engineered.iloc[[-1]][FEATURE_ORDER]

    risk_score = float(model.predict_proba(last_row)[0][1])
    severity = score_to_severity(risk_score)
    verdict = "suspicious" if risk_score >= 0.5 else "normal"

    alert_raised = severity in (Severity.medium, Severity.high, Severity.critical)
    if alert_raised:
        alert = Alert(
            module=Module.auth_anomaly,
            severity=severity,
            score=risk_score,
            source=f"{req.current.user_id}@{req.current.ip}",
            details={"verdict": verdict},
        )
        ALERT_LOG.append(alert)

    return LoginCheckResponse(
        risk_score=round(risk_score, 4),
        severity=severity,
        verdict=verdict,
        alert_raised=alert_raised,
    )


@app.get("/alerts")
def get_alerts():
    return ALERT_LOG


@app.get("/health")
def health():
    return {"status": "ok", "module": "auth-anomaly"}
