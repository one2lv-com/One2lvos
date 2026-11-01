#!/bin/bash
# ============================================================================
# ONE2LVOS PRODUCTION DEPLOYMENT SCRIPT
# ============================================================================
# This script deploys One2lvOS to production
# Usage: ./deploy.sh [start|stop|restart|status|logs]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
PROJECT_NAME="one2lvos"

# Functions
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    if [ ! -f ".env" ] && [ ! -f ".env.production" ]; then
        log_warning ".env file not found, creating from .env.production..."
        if [ -f ".env.production" ]; then
            cp .env.production .env
            log_success ".env created"
        else
            log_error "Neither .env nor .env.production found"
            exit 1
        fi
    fi

    log_success "All requirements met"
}

start_services() {
    log_info "Starting One2lvOS services..."

    # Pull latest images
    log_info "Pulling Docker images..."
    docker compose -f $COMPOSE_FILE pull || log_warning "Some images could not be pulled"

    # Build images
    log_info "Building Docker images..."
    docker compose -f $COMPOSE_FILE build

    # Start services
    log_info "Starting containers..."
    docker compose -f $COMPOSE_FILE up -d

    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 10

    # Check service health
    check_health

    log_success "One2lvOS is online!"
    show_access_info
}

stop_services() {
    log_info "Stopping One2lvOS services..."
    docker compose -f $COMPOSE_FILE down
    log_success "Services stopped"
}

restart_services() {
    log_info "Restarting One2lvOS..."
    stop_services
    start_services
}

show_status() {
    log_info "One2lvOS Service Status:"
    docker compose -f $COMPOSE_FILE ps
}

show_logs() {
    SERVICE=${1:-}
    if [ -z "$SERVICE" ]; then
        docker compose -f $COMPOSE_FILE logs --tail=100 --follow
    else
        docker compose -f $COMPOSE_FILE logs --tail=100 --follow $SERVICE
    fi
}

check_health() {
    log_info "Checking service health..."

    # Check Nginx
    if curl -f -s http://localhost:80/health > /dev/null 2>&1; then
        log_success "✓ Nginx Gateway: Healthy"
    else
        log_warning "✗ Nginx Gateway: Not responding"
    fi

    # Check Node AI Lobby
    if curl -f -s http://localhost:8787/health > /dev/null 2>&1; then
        log_success "✓ Node AI Lobby: Healthy"
    else
        log_warning "✗ Node AI Lobby: Not responding"
    fi

    # Check Python Core
    if curl -f -s http://localhost:3002/health > /dev/null 2>&1; then
        log_success "✓ Python Core: Healthy"
    else
        log_warning "✗ Python Core: Not responding"
    fi
}

show_access_info() {
    IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ONE2LVOS IS ONLINE  ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BLUE}Main UI:${NC}          http://${IP}"
    echo -e "  ${BLUE}Infinity Glasses:${NC} http://${IP}/Infinity_Glasses/"
    echo -e "  ${BLUE}Aetherix:${NC}         http://${IP}/Aetherix/"
    echo -e "  ${BLUE}Lumenis:${NC}          http://${IP}/Lumenis/"
    echo -e "  ${BLUE}AI Lobby:${NC}         http://${IP}/Agentic_Control/"
    echo ""
    echo -e "  ${BLUE}Node API:${NC}         http://${IP}:8787"
    echo -e "  ${BLUE}Python API:${NC}       http://${IP}:3002"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
}

update_system() {
    log_info "Updating One2lvOS..."

    # Pull latest code
    log_info "Pulling latest code from GitHub..."
    git fetch origin main
    git reset --hard origin/main

    # Rebuild and restart
    restart_services

    log_success "Update complete!"
}

init_astra() {
    log_info "Initializing Astra DB collections..."
    docker compose -f $COMPOSE_FILE run --rm astra-init
    log_success "Astra DB initialized"
}

backup_system() {
    BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
    log_info "Creating backup in $BACKUP_DIR..."

    mkdir -p "$BACKUP_DIR"

    # Backup data volumes
    docker compose -f $COMPOSE_FILE run --rm \
        -v one2lvos-node-data:/source \
        -v "$PWD/$BACKUP_DIR":/backup \
        alpine tar czf /backup/node-data.tar.gz -C /source .

    docker compose -f $COMPOSE_FILE run --rm \
        -v one2lvos-python-data:/source \
        -v "$PWD/$BACKUP_DIR":/backup \
        alpine tar czf /backup/python-data.tar.gz -C /source .

    # Backup snapshots
    if [ -d "./snapshots" ]; then
        cp -r ./snapshots "$BACKUP_DIR/"
    fi

    log_success "Backup created: $BACKUP_DIR"
}

# Main script
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                   ONE2LVOS DEPLOYMENT                      ║"
echo "║                  Production Environment                    ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

case "${1:-start}" in
    start)
        check_requirements
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        check_requirements
        restart_services
        ;;
    status)
        show_status
        check_health
        ;;
    logs)
        show_logs $2
        ;;
    update)
        check_requirements
        update_system
        ;;
    init-astra)
        check_requirements
        init_astra
        ;;
    backup)
        check_requirements
        backup_system
        ;;
    health)
        check_health
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [service]|update|init-astra|backup|health}"
        exit 1
        ;;
esac

exit 0
