.PHONY: help build up down restart logs clean deploy test health

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker images
	docker compose build

up: ## Start all services
	docker compose up -d
	@echo "Services started. Access at:"
	@echo "  - UI: http://localhost"
	@echo "  - AI Lobby: http://localhost:8787"
	@echo "  - Core API: http://localhost:3002"

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## View logs from all services
	docker compose logs -f

logs-ui: ## View logs from UI service
	docker compose logs -f ui

logs-lobby: ## View logs from AI Lobby service
	docker compose logs -f ai-lobby

logs-core: ## View logs from Core API service
	docker compose logs -f core-api

logs-nginx: ## View logs from Nginx gateway
	docker compose logs -f nginx

ps: ## Show running containers
	docker compose ps

clean: ## Remove all containers, images, and volumes
	docker compose down -v --rmi all

rebuild: ## Rebuild and restart all services
	docker compose down
	docker compose build --no-cache
	docker compose up -d

deploy: ## Run deployment script
	./deploy.sh

dev: ## Start local development environment
	./local-dev.sh

test: ## Run tests
	python -m pytest test_*.py -v
	npm test

health: ## Check health of all services
	@echo "Checking service health..."
	@curl -sf http://localhost/health && echo "✓ Nginx: healthy" || echo "✗ Nginx: unhealthy"
	@curl -sf http://localhost:8787/health && echo "✓ AI Lobby: healthy" || echo "✗ AI Lobby: unhealthy"
	@curl -sf http://localhost:3002/health && echo "✓ Core API: healthy" || echo "✗ Core API: unhealthy"

stats: ## Show Docker stats
	docker stats --no-stream

prune: ## Clean up unused Docker resources
	docker system prune -af
	docker volume prune -f

backup: ## Create backup of configuration
	tar -czf backup-$$(date +%Y%m%d-%H%M%S).tar.gz .env docker-compose.yml data/

install: ## Install system dependencies
	@echo "Installing system dependencies..."
	@command -v docker >/dev/null 2>&1 || { echo "Installing Docker..."; curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh; }
	@command -v docker compose >/dev/null 2>&1 || { echo "Installing Docker Compose..."; sudo apt-get update && sudo apt-get install -y docker-compose-plugin; }
	@echo "✓ Dependencies installed"

setup: ## Initial setup for new deployment
	@[ -f .env ] || { echo "Creating .env from template..."; cp .env.example .env; echo "Please configure .env file"; exit 1; }
	@echo "Building images..."
	$(MAKE) build
	@echo "Starting services..."
	$(MAKE) up
	@echo "✓ Setup complete"
