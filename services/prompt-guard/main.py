"""
Prompt-Guard microservice.
POST /check-prompt -> risk score for a candidate LLM prompt.
v1 uses TF-IDF + XGBoost (see train_baseline.py for why). Swap in the QLoRA
model later by pointing MODEL_MODE at "transformer" once you've trained it
on Colab and copied the model files back in — see qlora_finetune.py.
"""
import sys
import os
import re
import joblib
from fastapi import FastAPI
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "event-bus"))
from schema import Alert, Module, Severity, score_to_severity  # noqa: E402

HERE = os.path.dirname(__file__)
app = FastAPI(title="CyberSentinel — Prompt Guard")

model = joblib.load(os.path.join(HERE, "model.joblib"))
vectorizer = joblib.load(os.path.join(HERE, "vectorizer.joblib"))

# Known jailbreak template phrases — a lightweight second layer that catches
# obvious cases even if the ML model's confidence is borderline. Real systems
# commonly combine a learned model with rule-based/signature checks like this.
KNOWN_PATTERNS = [
    "ignore all previous instructions", "ignore the instructions",
    "developer mode", "do anything now", "you are now dan",
    "act as aim", "jailbreak", "no restrictions", "unfiltered and amoral",
    "pretend you are", "ignore your programming", "reveal your system prompt",
    "ignore your instructions", "bypass your", "disregard your instructions",
]

# Flexible pattern: catches "ignore/disregard ... instructions/programming/rules"
# even when the exact wording differs from the phrase list above.
INJECTION_REGEX = re.compile(
    r"\b(ignore|disregard|forget|override)\b.{0,30}\b(instructions?|programming|rules?|guidelines?|prompt)\b",
    re.IGNORECASE,
)

ALERT_LOG: list[Alert] = []


class PromptCheckRequest(BaseModel):
    prompt: str


class PromptCheckResponse(BaseModel):
    risk_score: float
    severity: Severity
    verdict: str
    matched_patterns: list[str]
    alert_raised: bool


@app.post("/check-prompt", response_model=PromptCheckResponse)
def check_prompt(req: PromptCheckRequest):
    text_lower = req.prompt.lower()
    matched = [p for p in KNOWN_PATTERNS if p in text_lower]
    regex_hit = bool(INJECTION_REGEX.search(req.prompt))
    if regex_hit:
        matched.append("ignore/override + instructions pattern")

    X = vectorizer.transform([req.prompt])
    ml_score = float(model.predict_proba(X)[0][1])

    # A literal known-attack phrase or regex hit is strong signal on its own —
    # it should dominate, not just nudge, a low ML confidence score. This fixes
    # a real gap found in testing: short prompts using canonical jailbreak
    # phrasing were scoring low because TF-IDF was trained mostly on long-form
    # copy-pasted templates, not short paraphrases.
    if matched:
        floor = 0.7
        risk_score = min(1.0, max(ml_score, floor) + 0.08 * (len(matched) - 1))
    else:
        risk_score = ml_score
    severity = score_to_severity(risk_score)
    verdict = "malicious" if risk_score >= 0.5 else "safe"

    alert_raised = severity in (Severity.medium, Severity.high, Severity.critical)
    if alert_raised:
        alert = Alert(
            module=Module.prompt_guard,
            severity=severity,
            score=risk_score,
            source=req.prompt[:80],
            details={"verdict": verdict, "matched_patterns": matched},
        )
        ALERT_LOG.append(alert)

    return PromptCheckResponse(
        risk_score=round(risk_score, 4),
        severity=severity,
        verdict=verdict,
        matched_patterns=matched,
        alert_raised=alert_raised,
    )


@app.get("/alerts")
def get_alerts():
    return ALERT_LOG


@app.get("/health")
def health():
    return {"status": "ok", "module": "prompt-guard"}
