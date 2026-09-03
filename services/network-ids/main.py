"""
Network-IDS microservice.
POST /analyze-traffic -> attack probability + verdict, based on NSL-KDD-style
connection-level features (duration, protocol_type, service, flag, byte counts,
etc. — the same 41 features the model was trained on, minus the label).
"""
import sys
import os
import json
import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "event-bus"))
from schema import Alert, Module, Severity, score_to_severity  # noqa: E402

HERE = os.path.dirname(__file__)
app = FastAPI(title="CyberSentinel — Network IDS")

model = joblib.load(os.path.join(HERE, "model.joblib"))
encoders = joblib.load(os.path.join(HERE, "label_encoders.joblib"))
with open(os.path.join(HERE, "model_features.json")) as f:
    FEATURE_ORDER = json.load(f)

ALERT_LOG: list[Alert] = []


class TrafficFlow(BaseModel):
    duration: int = 0
    protocol_type: str = "tcp"
    service: str = "http"
    flag: str = "SF"
    src_bytes: int = 0
    dst_bytes: int = 0
    land: int = 0
    wrong_fragment: int = 0
    urgent: int = 0
    hot: int = 0
    num_failed_logins: int = 0
    logged_in: int = 0
    num_compromised: int = 0
    root_shell: int = 0
    su_attempted: int = 0
    num_root: int = 0
    num_file_creations: int = 0
    num_shells: int = 0
    num_access_files: int = 0
    num_outbound_cmds: int = 0
    is_host_login: int = 0
    is_guest_login: int = 0
    count: int = 1
    srv_count: int = 1
    serror_rate: float = 0.0
    srv_serror_rate: float = 0.0
    rerror_rate: float = 0.0
    srv_rerror_rate: float = 0.0
    same_srv_rate: float = 1.0
    diff_srv_rate: float = 0.0
    srv_diff_host_rate: float = 0.0
    dst_host_count: int = 1
    dst_host_srv_count: int = 1
    dst_host_same_srv_rate: float = 1.0
    dst_host_diff_srv_rate: float = 0.0
    dst_host_same_src_port_rate: float = 0.0
    dst_host_srv_diff_host_rate: float = 0.0
    dst_host_serror_rate: float = 0.0
    dst_host_srv_serror_rate: float = 0.0
    dst_host_rerror_rate: float = 0.0
    dst_host_srv_rerror_rate: float = 0.0
    source_ip: Optional[str] = "unknown"


class TrafficResponse(BaseModel):
    risk_score: float
    severity: Severity
    verdict: str
    alert_raised: bool


def encode_flow(flow: TrafficFlow) -> pd.DataFrame:
    row = flow.model_dump(exclude={"source_ip"})
    for col in ["protocol_type", "service", "flag"]:
        le = encoders[col]
        val = row[col]
        if val not in set(le.classes_):
            val = le.classes_[0]  # unseen category -> safe fallback, same as training
        row[col] = le.transform([val])[0]
    return pd.DataFrame([row])[FEATURE_ORDER]


@app.post("/analyze-traffic", response_model=TrafficResponse)
def analyze_traffic(flow: TrafficFlow):
    df = encode_flow(flow)
    risk_score = float(model.predict_proba(df)[0][1])
    severity = score_to_severity(risk_score)
    verdict = "attack" if risk_score >= 0.5 else "normal"

    alert_raised = severity in (Severity.medium, Severity.high, Severity.critical)
    if alert_raised:
        alert = Alert(
            module=Module.network_ids,
            severity=severity,
            score=risk_score,
            source=flow.source_ip or "unknown",
            details={"verdict": verdict, "service": flow.service, "protocol": flow.protocol_type},
        )
        ALERT_LOG.append(alert)

    return TrafficResponse(
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
    return {"status": "ok", "module": "network-ids"}
