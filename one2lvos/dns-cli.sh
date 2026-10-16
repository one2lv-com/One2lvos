#!/bin/bash
# ============================================================================
# ONE2LVOS DNS GATEWAY - COMMAND LINE INTERFACE
# ============================================================================

REACTOR_URL="http://localhost:8000"
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

function show_help() {
    echo -e "${CYAN}ONE2LVOS DNS Gateway CLI${NC}"
    echo ""
    echo "Usage: ./dns-cli.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  list                    - List all registered domains"
    echo "  resolve <domain>        - Resolve a domain to IP:PORT"
    echo "  register <name> <port>  - Register a new service"
    echo "  remove <domain>         - Remove a domain"
    echo "  status                  - Show DNS gateway status"
    echo "  hosts                   - Export hosts file"
    echo "  services                - List all services"
    echo ""
    echo "Examples:"
    echo "  ./dns-cli.sh list"
    echo "  ./dns-cli.sh resolve reactor"
    echo "  ./dns-cli.sh register myapp 8888"
    echo "  ./dns-cli.sh status"
}

function check_reactor() {
    if ! curl -s "$REACTOR_URL/health" > /dev/null 2>&1; then
        echo -e "${RED}❌ Reactor Core is not running${NC}"
        echo "Start it with: ./start-reactor.sh"
        exit 1
    fi
}

case "$1" in
    list|ls)
        check_reactor
        echo -e "${CYAN}📋 Registered Domains:${NC}"
        curl -s "$REACTOR_URL/dns/list" | python3 -m json.tool
        ;;

    resolve)
        check_reactor
        if [ -z "$2" ]; then
            echo -e "${RED}Usage: ./dns-cli.sh resolve <domain>${NC}"
            exit 1
        fi
        echo -e "${CYAN}🔍 Resolving: $2${NC}"
        curl -s "$REACTOR_URL/dns/resolve/$2" | python3 -m json.tool
        ;;

    register|reg)
        check_reactor
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo -e "${RED}Usage: ./dns-cli.sh register <name> <port> [service_type]${NC}"
            exit 1
        fi
        SERVICE_TYPE="${4:-custom}"
        echo -e "${CYAN}📝 Registering: $2 on port $3${NC}"
        curl -s -X POST "$REACTOR_URL/dns/register" \
            -H "Content-Type: application/json" \
            -d "{\"name\":\"$2\",\"port\":$3,\"service_type\":\"$SERVICE_TYPE\"}" \
            | python3 -m json.tool
        ;;

    remove|rm)
        check_reactor
        if [ -z "$2" ]; then
            echo -e "${RED}Usage: ./dns-cli.sh remove <domain>${NC}"
            exit 1
        fi
        echo -e "${CYAN}🗑️  Removing: $2${NC}"
        curl -s -X POST "$REACTOR_URL/dns" \
            -H "Content-Type: application/json" \
            -d "{\"action\":\"remove\",\"domain\":\"$2\"}" \
            | python3 -m json.tool
        ;;

    status)
        check_reactor
        echo -e "${CYAN}📊 DNS Gateway Status:${NC}"
        curl -s "$REACTOR_URL/dns/status" | python3 -m json.tool
        ;;

    hosts)
        check_reactor
        echo -e "${CYAN}📄 Exporting hosts file...${NC}"
        RESPONSE=$(curl -s "$REACTOR_URL/dns/hosts")
        echo "$RESPONSE" | python3 -m json.tool
        CONTENT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['content'])")
        echo ""
        echo -e "${GREEN}Hosts file content:${NC}"
        echo "$CONTENT"
        ;;

    services)
        check_reactor
        echo -e "${CYAN}🔍 Discovering services...${NC}"
        curl -s "$REACTOR_URL/services" | python3 -m json.tool
        ;;

    help|--help|-h)
        show_help
        ;;

    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
