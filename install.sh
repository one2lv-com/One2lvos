#!/bin/bash
# One2lvOS Installation Script
# Installs dependencies and configures environment

set -e

echo "=================================================="
echo "  One2lvOS Installation Script"
echo "  Version: 1.0.2"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
print_step() {
    echo -e "${CYAN}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if running with sufficient permissions
check_permissions() {
    print_step "Checking permissions..."
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root. This is okay but not required for user-space installation."
    fi
    print_success "Permissions check complete"
}

# Detect OS and package manager
detect_os() {
    print_step "Detecting operating system..."

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
        echo "  OS: $NAME"
        echo "  Version: $VERSION_ID"

        # Determine package manager
        if command -v apt &> /dev/null; then
            PKG_MANAGER="apt"
            PKG_INSTALL="apt install -y"
            PKG_UPDATE="apt update"
        elif command -v yum &> /dev/null; then
            PKG_MANAGER="yum"
            PKG_INSTALL="yum install -y"
            PKG_UPDATE="yum check-update"
        elif command -v dnf &> /dev/null; then
            PKG_MANAGER="dnf"
            PKG_INSTALL="dnf install -y"
            PKG_UPDATE="dnf check-update"
        else
            print_error "No supported package manager found (apt, yum, or dnf)"
            exit 1
        fi

        print_success "Package manager: $PKG_MANAGER"
    else
        print_error "Cannot detect OS. /etc/os-release not found."
        exit 1
    fi
}

# Check Python installation
check_python() {
    print_step "Checking Python installation..."

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
        echo "  Python version: $PYTHON_VERSION"

        # Check if version is 3.11 or higher
        MAJOR=$(echo $PYTHON_VERSION | cut -d '.' -f 1)
        MINOR=$(echo $PYTHON_VERSION | cut -d '.' -f 2)

        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
            print_success "Python 3.11+ detected"
        else
            print_warning "Python 3.11+ recommended (found $PYTHON_VERSION)"
        fi
    else
        print_error "Python 3 not found. Please install Python 3.11 or higher."
        exit 1
    fi

    # Check pip
    if command -v pip3 &> /dev/null; then
        print_success "pip3 available"
    else
        print_error "pip3 not found. Please install python3-pip."
        exit 1
    fi
}

# Check Node.js installation
check_nodejs() {
    print_step "Checking Node.js installation..."

    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version | cut -d 'v' -f 2)
        echo "  Node.js version: v$NODE_VERSION"

        # Check if version is 20 or higher
        MAJOR=$(echo $NODE_VERSION | cut -d '.' -f 1)

        if [ "$MAJOR" -ge 20 ]; then
            print_success "Node.js 20+ detected"
        else
            print_warning "Node.js 20+ recommended (found v$NODE_VERSION)"
        fi
    else
        print_warning "Node.js not found. Some features may not work."
    fi

    # Check npm
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        echo "  npm version: $NPM_VERSION"
        print_success "npm available"
    else
        print_warning "npm not found"
    fi
}

# Install Python dependencies
install_python_deps() {
    print_step "Installing Python dependencies..."

    if [ -f requirements.txt ]; then
        pip3 install --user -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Install Node.js dependencies (optional)
install_nodejs_deps() {
    if [ -f package.json ] && command -v npm &> /dev/null; then
        print_step "Installing Node.js dependencies..."
        npm install
        print_success "Node.js dependencies installed"
    else
        print_warning "Skipping Node.js dependencies (package.json not found or npm not available)"
    fi
}

# Setup environment file
setup_environment() {
    print_step "Setting up environment configuration..."

    if [ ! -f .env ]; then
        print_warning ".env file not found"
        echo "  Please create .env file with your configuration."
        echo "  See .env.example or ASTRA_DB_SETUP.md for details."
    else
        print_success ".env file exists"
    fi
}

# Create necessary directories
create_directories() {
    print_step "Creating necessary directories..."

    mkdir -p /tmp/one2lv-unified/snapshots
    mkdir -p /tmp/one2lv-unified/logs
    mkdir -p system/etc/apt

    print_success "Directories created"
}

# Verify installation
verify_installation() {
    print_step "Verifying installation..."

    # Check if astrapy is installed
    if python3 -c "import astrapy" 2>/dev/null; then
        print_success "astrapy installed"
    else
        print_error "astrapy not installed"
    fi

    # Check if OpenAI is installed
    if python3 -c "import openai" 2>/dev/null; then
        print_success "openai installed"
    else
        print_warning "openai not installed (optional)"
    fi

    # Check if PIL/Pillow is installed
    if python3 -c "from PIL import Image" 2>/dev/null; then
        print_success "Pillow installed"
    else
        print_error "Pillow not installed"
    fi
}

# Main installation flow
main() {
    echo ""
    check_permissions
    echo ""
    detect_os
    echo ""
    check_python
    echo ""
    check_nodejs
    echo ""
    create_directories
    echo ""
    install_python_deps
    echo ""
    install_nodejs_deps
    echo ""
    setup_environment
    echo ""
    verify_installation
    echo ""

    echo "=================================================="
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo "=================================================="
    echo ""
    echo "Next steps:"
    echo "  1. Configure .env file with your credentials"
    echo "  2. Run: python3 unified_os.py"
    echo "  3. In another terminal: cd One2lvOS && python3 -m http.server 8000"
    echo "  4. Open: http://localhost:8000"
    echo ""
    echo "Documentation:"
    echo "  - ASTRA_DB_SETUP.md - Astra DB configuration"
    echo "  - REPOSITORY_SETUP.md - Package repository info"
    echo "  - README.md - General overview"
    echo ""
    print_success "One2lvOS is ready to launch! 🌌🧲"
}

# Run main installation
main
