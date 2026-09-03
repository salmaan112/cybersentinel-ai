# CyberSentinel AI

A unified multi-vector threat detection platform combining phishing/URL
detection, network intrusion detection, credential-stuffing/login anomaly
detection, and LLM prompt-injection detection — behind one live dashboard,
with Docker + CI/CD + AWS deployment.

## Project structure
```
cybersentinel-ai/
├── services/
│   ├── phishing-detect/   # XGBoost, URL features        (port 8001)
│   ├── network-ids/       # XGBoost, NSL-KDD dataset      (port 8002)
│   ├── auth-anomaly/      # XGBoost, synthetic login logs (port 8003)
│   └── prompt-guard/      # TF-IDF+XGBoost baseline + QLoRA script (port 8004)
├── event-bus/             # Aggregator that unifies all 4 modules' alerts (port 8000)
├── dashboard/             # Static HTML live ops console (open directly in browser)
├── infra/                 # AWS deployment guide
├── .github/workflows/     # CI: smoke-tests + Docker builds on every push
├── docker-compose.yml     # Run everything together with one command
└── RUN_ALL.md             # Step-by-step guide to running the full platform locally
```

## Quickest path to seeing it work: RUN_ALL.md

That file has the exact terminal commands, in order, to get all 5 services
running and the dashboard showing live data — including the "Simulate
attack" demo button.

## Each service's own README

Every folder under `services/` has its own README with that module's setup
steps, real accuracy/precision/recall numbers, and — importantly — the
specific bugs found and fixed while building it. Read those before you
write your project report; they're the most interview-worthy material here
("I found X, here's why it happened, here's how I fixed it" beats a bare
accuracy number every time).

## Docker (once you're comfortable running it manually)
```
docker compose up --build
```
See infra/README.md and infra/DEPLOY.md for the AWS deployment path and
why EC2+docker-compose was chosen over Lambda for this architecture.

## Known limitations (be upfront about these in your report)
- phishing-detect: raw IP-based phishing URLs are under-detected (~0.36 risk
  score) — needs more IP-based examples in training data.
- network-ids: 67.7% recall on NSL-KDD's official test set, which
  deliberately includes attack subtypes never seen in training — a
  documented, expected property of this benchmark, not a bug. Planned fix:
  add an unsupervised anomaly detector layer.
- prompt-guard v1 uses classical ML (TF-IDF+XGBoost), not the originally
  planned QLoRA fine-tune, because this sandbox has no internet access to
  Hugging Face. The QLoRA script (qlora_finetune.py) is provided to run on
  Colab — comparing both approaches is a stronger report finding than
  either alone.
- Docker/docker-compose config has been validated for correct file paths
  and valid YAML, but not actually built/run (no Docker daemon in this
  sandbox) — expect to debug at least one small issue on first real build.
