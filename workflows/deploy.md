# Workflow: Deploy to DigitalOcean

## Objective
Deploy the DexIQ AI Presenter to a DigitalOcean Droplet.

## Required Inputs
- Docker and docker-compose installed on the Droplet
- `.env` file with all API keys configured
- All audio files generated and placed in `frontend/audio/`
- Domain name (optional) with DNS pointing to Droplet IP

## Steps

1. **Provision Droplet** — 2 vCPU, 4GB RAM, Ubuntu 24.04
2. **SSH into Droplet:**
   ```bash
   ssh root@your-droplet-ip
   ```
3. **Install Docker:**
   ```bash
   apt update && apt install -y docker.io docker-compose
   ```
4. **Clone repository:**
   ```bash
   git clone https://github.com/your-repo/ai-presenter.git
   cd ai-presenter
   ```
5. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env  # Fill in API keys
   ```
6. **Deploy:**
   ```bash
   docker-compose up -d --build
   ```
7. **Verify:**
   - Backend health: `curl http://localhost:8000/health`
   - Presenter screen: Open `http://your-ip:8000/static/index.html`
   - Chainlit: Open `http://your-ip:8001`
   - Q&A page: Open `http://your-ip:8000/static/ask.html`
8. **Set up SSL (optional):**
   - Use Caddy or nginx reverse proxy with Let's Encrypt

## Expected Output
- All three screens accessible via browser
- WebSocket connections working between all components

## Edge Cases
- If WebSocket fails behind a reverse proxy, ensure proxy passes `Upgrade` headers.
- If audio doesn't play, check CORS settings and static file mounting.
