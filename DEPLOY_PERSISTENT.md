# One2lvOS Persistent Deployment

This deployment keeps the browser UI, Node AI Lobby, and Python One2lv core running as separate services.

## Architecture

```text
Internet :8080/443
       |
       v
   Nginx gateway
    /       |       \
   UI      /api      /core
            |          |
         Node Lobby  Python Core
          :8787       :3002
```

All three containers use `restart: unless-stopped`. The gateway waits for the core and lobby health checks before starting. Runtime state is stored in named Docker volumes.

## Start on a Linux server

Requirements: Docker Engine and Docker Compose v2.

```bash
git clone https://github.com/one2lv-com/One2lvos.git /opt/one2lvos
cd /opt/one2lvos

docker compose up -d --build

docker compose ps
```

The UI is available at:

```text
http://SERVER_IP:8080/
```

Health endpoints:

```text
http://SERVER_IP:8080/health
http://SERVER_IP:8080/core/health
http://SERVER_IP:8080/core/status
```

## Keep it online

The stack is detached and each service has `restart: unless-stopped`.

```bash
docker compose up -d
```

A reboot of the Docker host will bring the services back when Docker starts. To inspect them:

```bash
docker compose ps
docker compose logs -f
```

## Automatic main -> build -> deploy

`.github/workflows/deploy-host.yml` deploys every push to `main` to the production Docker host over SSH.

Configure these GitHub Actions **production environment secrets**:

- `DEPLOY_HOST` — server hostname or IP
- `DEPLOY_USER` — SSH user
- `DEPLOY_PATH` — deployment directory, normally `/opt/one2lvos`
- `DEPLOY_SSH_KEY` — dedicated Ed25519 private key
- `DEPLOY_KNOWN_HOSTS` — exact SSH host-key entry for the server

GitHub Actions secrets are encrypted and only exposed to workflows that explicitly reference them; use a dedicated deployment credential with the minimum permissions required. See GitHub's documentation on Actions secrets and deployments.

The workflow then:

1. validates the deployment files;
2. connects to the host;
3. clones the repo on first deployment or resets it to `origin/main`;
4. rebuilds the containers;
5. starts them detached;
6. checks container health and the gateway endpoint.

## Optional public HTTPS

Put a TLS reverse proxy/load balancer such as Caddy, Nginx, or a managed cloud proxy in front of port 8080. Keep ports 8787 and 3002 private; only the gateway needs to be internet-facing.

## Secrets

Do not commit API keys, Astra tokens, NVIDIA credentials, or production passwords. Supply them to the Node/Python services through the host environment or a protected `.env`/secret mechanism. The repository's AI Lobby already has a persistent `data/` directory and the Compose deployment mounts it as a volume.

## Redeploy manually

```bash
cd /opt/one2lvos
git fetch origin main
git reset --hard origin/main
docker compose up -d --build --remove-orphans
```
