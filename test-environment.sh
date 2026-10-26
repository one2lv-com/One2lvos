#!/bin/bash
# Quick environment test for One2lvOS

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Testing One2lvOS Environment..."
echo ""

# Test 1: Python
if python3 -c "import fastapi, openai, uvicorn" 2>/dev/null; then
    echo -e "${GREEN}✓ Python dependencies OK${NC}"
else
    echo -e "${RED}✗ Python dependencies missing${NC}"
    exit 1
fi

# Test 2: Node.js
if node -e "console.log('OK')" 2>/dev/null; then
    echo -e "${GREEN}✓ Node.js runtime OK${NC}"
else
    echo -e "${RED}✗ Node.js not working${NC}"
    exit 1
fi

# Test 3: Configuration
if [ -f "$HOME/One2lvos/.env" ]; then
    echo -e "${GREEN}✓ Configuration file exists${NC}"
else
    echo -e "${YELLOW}⚠ .env missing (will be created on start)${NC}"
fi

# Test 4: Write permissions
TEST_FILE="$HOME/One2lvos/logs/.test"
mkdir -p "$HOME/One2lvos/logs"
if touch "$TEST_FILE" 2>/dev/null; then
    rm "$TEST_FILE"
    echo -e "${GREEN}✓ Write permissions OK${NC}"
else
    echo -e "${RED}✗ Cannot write to logs directory${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ All environment tests passed!${NC}"
echo -e "${YELLOW}Ready to start One2lvOS${NC}"
