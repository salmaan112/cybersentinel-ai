# Infra

## Local Docker (needs Docker Desktop installed on your machine)
From the repo root:
  docker compose up --build

This builds and starts all 5 services + the aggregator together, wired with
correct container-to-container networking (see docker-compose.yml comments).

Then open dashboard/index.html in your browser as before — it still talks
to localhost:8000, which Docker maps straight through to your machine.

## AWS Deployment
See DEPLOY.md for the full guide, including why EC2+docker-compose was
chosen over Lambda for this specific multi-service architecture.

## CI/CD
.github/workflows/ci.yml (at repo root) runs on every push/PR to main:
  1. Smoke-tests each service (imports cleanly, /health returns 200)
  2. Builds all 5 Docker images

Pushing built images to a real registry (ECR) needs your AWS credentials
added as GitHub Secrets — intentionally not included here since that's
specific to your AWS account, not something to hardcode into the repo.
