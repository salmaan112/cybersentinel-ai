# Deploying CyberSentinel AI to AWS

## Recommended path: EC2 + docker-compose

This is the path that actually matches your architecture, and it's what
this guide covers. Here's why, honestly:

Your event-bus aggregator polls the other four services over HTTP. With
docker-compose, all five containers share one Docker network and can reach
each other by service name (`http://phishing-detect:8001`, etc.) — this
just works, as configured in docker-compose.yml.

AWS Lambda doesn't give you that. Each Lambda function is isolated with its
own URL; there's no shared "localhost" or internal network between them for
free. Making the aggregator work on Lambda would mean rearchitecting it to
use API Gateway URLs or a service registry — real extra work, not a drop-in
swap. So: Lambda is the right call for a single standalone service, but for
this five-service architecture, one EC2 instance running docker-compose is
simpler, cheaper for a portfolio project, and honestly a better story in an
interview ("I understood the tradeoff and chose EC2 over Lambda because...").

### Steps

1. **Launch an EC2 instance** — t3.small is enough (2 vCPU, 2GB RAM handles
   all 5 lightweight containers fine for demo/portfolio traffic levels).
   Amazon Linux 2023 or Ubuntu 22.04 both work.

2. **Open the right ports** in the instance's Security Group: 8000-8004
   inbound (or just 8000 if you put a reverse proxy in front — see below).

3. **Install Docker on the instance:**
   ```bash
   sudo yum install -y docker    # Amazon Linux
   # or: sudo apt install -y docker.io    # Ubuntu
   sudo systemctl start docker
   sudo usermod -aG docker $USER
   # log out and back in for the group change to take effect
   ```
   Install docker-compose separately (Amazon Linux/Ubuntu don't bundle the
   v2 plugin by default) — follow Docker's official install docs for the
   current command, since it changes with new Docker releases.

4. **Get your code onto the instance** — either `git clone` your repo (if
   pushed to GitHub) or `scp` the project folder up.

5. **Train the models on the instance** (or copy already-trained
   `model.joblib` files up — but given the corruption issue you hit earlier,
   retraining fresh on the target machine is more reliable):
   ```bash
   cd services/phishing-detect && python3 train.py && cd ../..
   cd services/network-ids && python3 train.py && cd ../..
   cd services/auth-anomaly && python3 generate_data.py && python3 train.py && cd ../..
   cd services/prompt-guard && python3 train_baseline.py && cd ../..
   ```

6. **Run everything:**
   ```bash
   docker compose up --build -d
   ```

7. **Serve the dashboard.** The dashboard is a static HTML file — the
   simplest option is `python3 -m http.server 8080` from the `dashboard/`
   folder, or put it behind nginx if you want it on port 80. Either way,
   edit `dashboard/index.html` and change the `AGGREGATOR` constant from
   `http://localhost:8000` to `http://<your-ec2-public-ip>:8000` — right
   now it assumes the dashboard and aggregator are on the same machine as
   your browser, which won't be true once the aggregator moves to EC2.

8. **Point CI/CD at it (optional, stretch goal):** extend
   `.github/workflows/ci.yml` with a deploy job that SSHes into the EC2
   instance and runs `git pull && docker compose up --build -d` after the
   build job passes. This needs your EC2 SSH key added as a GitHub Secret —
   don't commit it to the repo.

## Alternative: if you want to say "I deployed serverless" too

You can still deploy phishing-detect (or any single module) standalone as a
Lambda function using the `mangum` adapter, purely as a secondary artifact
for your resume — "also deployed the phishing-detection module standalone
as an AWS Lambda function using Mangum" is a true, defensible sentence, as
long as you're clear it's a standalone deployment of one module, not the
full unified platform. Don't claim the whole system runs serverless when it
architecturally doesn't — that's the kind of detail an interviewer asking
follow-up questions will find in about two questions.
