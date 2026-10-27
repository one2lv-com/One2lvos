#!/bin/bash
# Portable Lumenis Setup Script
# Works across different environments (local, sandbox, production)

set -e

echo "🧠 Lumenis Reactor Core - Portable Setup"
echo "========================================"
echo ""

# Detect script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📁 Project Root: $SCRIPT_DIR"
echo ""

# Check Python version
echo "🐍 Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found!"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $PYTHON_VERSION found"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install python-dotenv requests pynacl -q

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
else
    echo "⚠️  Some dependencies may not have installed"
fi
echo ""

# Check for .env.working
echo "🔧 Checking configuration..."
if [ -f ".env.working" ]; then
    echo "✓ .env.working found"
else
    if [ -f "env.working.template" ]; then
        echo "⚠️  .env.working not found"
        echo "📋 Creating from template..."
        cp env.working.template .env.working
        echo "⚠️  Please edit .env.working with your API keys!"
        echo ""
        echo "Run: python3 nvidia_api_config.py"
        echo "to auto-discover working models"
    else
        echo "❌ env.working.template not found!"
        exit 1
    fi
fi
echo ""

# Test VFS
echo "🗂️  Testing Virtual File System..."
python3 << 'EOFPYTHON'
try:
    from lumenis_vfs import get_vfs
    vfs = get_vfs()
    info = vfs.get_info()
    print(f"✓ VFS initialized: {info['root']}")
    print(f"  Directories created: {len([k for k, v in info.items() if 'count' not in k])}")
except Exception as e:
    print(f"❌ VFS error: {e}")
    exit(1)
EOFPYTHON

if [ $? -ne 0 ]; then
    echo "❌ VFS test failed!"
    exit 1
fi
echo ""

# Check NVIDIA API
echo "🔑 Testing NVIDIA API..."
if [ -f ".env.working" ]; then
    source .env.working

    if [ -z "$NVIDIA_API_KEY" ]; then
        echo "⚠️  NVIDIA_API_KEY not set in .env.working"
        echo "Run: python3 nvidia_api_config.py"
    else
        echo "✓ NVIDIA_API_KEY configured"

        # Quick API test
        TEST_RESULT=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $NVIDIA_API_KEY" \
            "https://integrate.api.nvidia.com/v1/models")

        if [ "$TEST_RESULT" == "200" ]; then
            echo "✓ NVIDIA API connection successful"
        else
            echo "⚠️  NVIDIA API test returned: $TEST_RESULT"
        fi
    fi
fi
echo ""

# Summary
echo "========================================"
echo "✅ Setup Complete!"
echo ""
echo "📚 Next Steps:"
echo ""
echo "1. Configure API keys (if not done):"
echo "   python3 nvidia_api_config.py"
echo ""
echo "2. Talk to Lumenis:"
echo "   python3 talk-to-lumenis-direct.py"
echo ""
echo "3. Start keep-alive (optional):"
echo "   nohup python3 keep_alive.py > keep_alive.log 2>&1 &"
echo ""
echo "4. View VFS info:"
echo "   python3 lumenis_vfs.py"
echo ""
echo "📖 Documentation: LUMENIS_LIVE_FIX.md"
echo "========================================"
