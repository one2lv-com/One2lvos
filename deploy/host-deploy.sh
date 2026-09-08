#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${ONE2LV_DEPLOY_DIR:-/opt/one2lvos}"
REPO_URL="${ONE2LV_REPO_URL:-https://github.com/one2lv-com/One2lvos.git}"
BRANCH="${ONE2LV_BRANCH:-main}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is required. Install Docker Engine + Compose v2 first."
  exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
  mkdir -p "$(dirname "$APP_DIR")"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
fi

cd "$APP_DIR"
docker compose up -d --build --remove-orphans
docker compose ps

echo
echo "One2lvOS is running."
echo "UI: http://$(hostname -I | awk '{print $1}'):${ONE2LV_PORT:-8080}/"
echo "Core: http://$(hostname -I | awk '{print $1}'):${ONE2LV_PORT:-8080}/core/status"
echo "Logs: docker compose logs -f"
