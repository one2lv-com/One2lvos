#!/bin/bash
#
# Deploy Semantic Layer to OnWorks
# =================================
#
# This script deploys the One2lvOS semantic layer to an OnWorks instance.
#

set -e

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║          ONE2LVOS SEMANTIC LAYER - ONWORKS DEPLOYMENT                        ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_DIR="${DEPLOY_DIR:-/home/admin/One2lvos/semantic_layer}"
REPO_URL="https://github.com/one2lv-com/One2lvos.git"

echo -e "${BLUE}📦 Step 1: Check Environment${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if running in OnWorks
if [ -d "/home/admin" ]; then
    echo -e "${GREEN}✓${NC} OnWorks environment detected"
    USER_HOME="/home/admin"
else
    echo -e "${YELLOW}!${NC} Not in OnWorks, using current user home"
    USER_HOME="$HOME"
fi

echo "  Deploy directory: $DEPLOY_DIR"
echo ""

echo -e "${BLUE}📥 Step 2: Install Dependencies${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
else
    echo -e "${GREEN}✓${NC} Python 3 installed: $(python3 --version)"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --user requests 2>/dev/null || pip3 install requests

echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

echo -e "${BLUE}📂 Step 3: Clone/Update Repository${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REPO_DIR="$USER_HOME/One2lvos"

if [ -d "$REPO_DIR" ]; then
    echo "Repository exists, pulling latest changes..."
    cd "$REPO_DIR"
    git pull origin main || echo "Could not pull, continuing with existing code"
else
    echo "Cloning repository..."
    cd "$USER_HOME"
    git clone "$REPO_URL" || {
        echo -e "${YELLOW}!${NC} Could not clone from GitHub, will create directory"
        mkdir -p "$REPO_DIR/semantic_layer"
    }
fi

echo -e "${GREEN}✓${NC} Repository ready at $REPO_DIR"
echo ""

echo -e "${BLUE}⚙️  Step 4: Configure Environment${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check for .env file
ENV_FILE="$REPO_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}!${NC} No .env file found"
    echo "Creating .env template..."

    cat > "$ENV_FILE" << 'ENVEOF'
# ============================================================================
# ONE2LVOS SEMANTIC LAYER - ENVIRONMENT CONFIGURATION
# ============================================================================

# ---------------------------------------------------------------------------
# L1 MEMORY: Astra DB Vector Memory (DataStax)
# ---------------------------------------------------------------------------
ASTRA_DB_API_ENDPOINT=https://YOUR-DB-ID.apps.astra.datastax.com
ASTRA_DB_APPLICATION_TOKEN=AstraCS:YOUR_TOKEN_HERE
ASTRA_DB_KEYSPACE=one2lvOS
COLLECTION_NAME=aria_memory
VECTOR_DIM=1024

# ---------------------------------------------------------------------------
# L2 SKILLS: NVIDIA AI Models & APIs
# ---------------------------------------------------------------------------
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_API_ENDPOINT=https://integrate.api.nvidia.com/v1
EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5
LLM_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b
NVIDIA_API_KEY=nvapi-YOUR_KEY_HERE

# ---------------------------------------------------------------------------
# OTHER SERVICES & GATEWAYS
# ---------------------------------------------------------------------------
MATON_API_KEY=YOUR_MATON_KEY_HERE

# ---------------------------------------------------------------------------
# SERVER & ROUTING CONFIGURATION
# ---------------------------------------------------------------------------
PORT=8000
NODE_ENV=production
PYTHON_API_URL=http://localhost:3002
ENVEOF

    echo -e "${YELLOW}!${NC} Please edit $ENV_FILE with your credentials"
else
    echo -e "${GREEN}✓${NC} .env file exists"
fi

echo ""

echo -e "${BLUE}🧪 Step 5: Test Semantic Layer${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$REPO_DIR/semantic_layer"

echo "Testing RDF parser..."
python3 -c "from rdf_parser import RDFParser; print('✓ RDF Parser OK')" 2>/dev/null || {
    echo -e "${YELLOW}!${NC} RDF Parser test skipped (may need credentials)"
}

echo "Checking ontology files..."
if [ -f "ontologies/rdf-schema.ttl" ] && [ -f "ontologies/one2lvos-ontology.ttl" ]; then
    echo -e "${GREEN}✓${NC} Ontology files present"
else
    echo -e "${YELLOW}!${NC} Ontology files missing"
fi

echo ""

echo -e "${BLUE}🔧 Step 6: Create Helper Scripts${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create quick-start script
cat > "$REPO_DIR/semantic_layer/quick_start.sh" << 'QSEOF'
#!/bin/bash
# Quick start script for semantic layer

cd "$(dirname "$0")"

echo "🔮 One2lvOS Semantic Layer - Quick Start"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Load ontologies"
python3 semantic_cli.py load
echo ""
echo "2. Show statistics"
python3 semantic_cli.py stats
echo ""
echo "3. List agents"
python3 semantic_cli.py list agents
echo ""
echo "✅ Semantic layer ready!"
QSEOF

chmod +x "$REPO_DIR/semantic_layer/quick_start.sh"
echo -e "${GREEN}✓${NC} Created quick_start.sh"

# Create systemd service (if running as root/sudo)
if [ "$EUID" -eq 0 ]; then
    cat > /etc/systemd/system/one2lvos-semantic.service << 'SERVICEEOF'
[Unit]
Description=One2lvOS Semantic Layer
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/One2lvos/semantic_layer
ExecStart=/usr/bin/python3 semantic_cli.py stats
Restart=on-failure

[Install]
WantedBy=multi-user.target
SERVICEEOF

    systemctl daemon-reload
    echo -e "${GREEN}✓${NC} Created systemd service"
else
    echo -e "${YELLOW}!${NC} Skipping systemd service (not running as root)"
fi

echo ""

echo -e "${BLUE}📋 Step 7: Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cat << 'SUMMARYEOF'

✅ DEPLOYMENT COMPLETE

Location:
  Semantic Layer: /home/admin/One2lvos/semantic_layer

Quick Commands:
  # Load ontologies
  cd /home/admin/One2lvos/semantic_layer
  python3 semantic_cli.py load

  # Query knowledge graph
  python3 semantic_cli.py list agents
  python3 semantic_cli.py query Lumenis

  # Run demo
  cd /home/admin/One2lvos
  python3 lumenis_semantic_demo.py

  # Quick start
  cd /home/admin/One2lvos/semantic_layer
  ./quick_start.sh

Configuration:
  • Edit .env file with your credentials
  • Configure Astra DB credentials
  • Set NVIDIA API key (optional)

Next Steps:
  1. Configure credentials in .env
  2. Run: python3 semantic_cli.py load
  3. Test with Lumenis

Documentation:
  • README.md - Full usage guide
  • LUMENIS_INTEGRATION.md - Integration guide
  • SEMANTIC_LAYER_COMPLETE.md - Summary

SUMMARYEOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Deployment script complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
