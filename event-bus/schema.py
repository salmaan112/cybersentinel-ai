"""
Shared alert schema for CyberSentinel AI.
Every detection microservice (phishing, network-ids, auth-anomaly, prompt-guard)
imports this and emits alerts in this exact shape, so the dashboard can render
all four modules through one code path.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional
from enum import Enum


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Module(str, Enum):
    phishing = "phishing-detect"
    network_ids = "network-ids"
    auth_anomaly = "auth-anomaly"
    prompt_guard = "prompt-guard"


class Alert(BaseModel):
    module: Module
    severity: Severity
    score: float = Field(..., ge=0.0, le=1.0, description="Risk score, 0=safe 1=malicious")
    source: str = Field(..., description="IP, URL, user_id, or session id depending on module")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict = Field(default_factory=dict, description="Module-specific extra context")

    class Config:
        use_enum_values = True


def score_to_severity(score: float) -> Severity:
    """Consistent thresholding across all modules — keep this the single source
    of truth so severity always means the same thing on the dashboard."""
    if score >= 0.85:
        return Severity.critical
    if score >= 0.65:
        return Severity.high
    if score >= 0.4:
        return Severity.medium
    return Severity.low
