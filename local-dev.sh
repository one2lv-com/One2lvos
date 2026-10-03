#!/bin/bash

# Local Development Script for One2lvOS
# This runs the system locally for testing before deployment

set -e

echo "========================================"
echo "One2lvOS Local Development Setup"
echo "========================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if .env exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Please configure .env file with your credentials"
        exit 1
    else
        echo "Error: .env.example not found"
        exit 1
    fi
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    exit 1
fi

print_success "Docker and Docker Compose are installed"

# Stop any running containers
echo ""
echo "Stopping any existing containers..."
docker compose down 2>/dev/null || true

# Build images
echo ""
echo "Building Docker images..."
docker compose build

print_success "Images built successfully"

# Start services
echo ""
echo "Starting services..."
docker compose up -d

print_success "Services started"

# Wait for services to be ready
echo ""
echo "Waiting for services to be ready..."
sleep 15

# Show status
echo ""
echo "Container Status:"
docker compose ps

# Show logs
echo ""
echo "Recent logs:"
docker compose logs --tail=30

echo ""
echo "========================================"
print_success "One2lvOS is now running locally!"
echo "========================================"
echo ""
echo "Access the services at:"
echo "  - Main UI:    http://localhost"
echo "  - AI Lobby:   http://localhost:8787"
echo "  - Core API:   http://localhost:3002"
echo ""
echo "Useful commands:"
echo "  - View logs:        docker compose logs -f"
echo "  - Stop services:    docker compose down"
echo "  - Restart:          docker compose restart"
echo "  - Rebuild:          docker compose build --no-cache"
echo ""
