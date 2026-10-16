#!/bin/bash
# O2PNG Demo Script

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${MAGENTA}"
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║       O2PNG - One2lvOS PNG Steganography Demo                       ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

cd "$(dirname "$0")"

# Demo 1: Encode JSON data
echo -e "${CYAN}📝 Demo 1: Encoding JSON data to PNG${NC}"
echo ""

cat > demo_data.json << 'EOF'
{
  "one2lvos": {
    "version": "2.0.0",
    "status": "operational",
    "reactor_core": "online"
  },
  "dns_gateway": {
    "domains": 9,
    "suffix": ".one2lv.local",
    "status": "active"
  },
  "timestamp": "2026-10-16T05:30:00Z"
}
EOF

echo "Created demo_data.json:"
cat demo_data.json
echo ""

echo -e "${YELLOW}Encoding to PNG with visual pattern...${NC}"
./o2png encode --input demo_data.json --output demo_encoded.png --visual --width 1024 --height 64
echo ""

# Demo 2: View PNG info
echo -e "${CYAN}📊 Demo 2: PNG Information${NC}"
./o2png info --input demo_encoded.png
echo ""

# Demo 3: Decode PNG
echo -e "${CYAN}🔓 Demo 3: Decoding PNG${NC}"
./o2png decode --input demo_encoded.png --output demo_decoded.json
echo ""

echo -e "${GREEN}Decoded content:${NC}"
cat demo_decoded.json | python3 -m json.tool
echo ""

# Demo 4: Encode a file
echo -e "${CYAN}📦 Demo 4: Encoding a file${NC}"
echo "This is a secret document from One2lvOS" > secret_doc.txt
echo "DNS Gateway is operational" >> secret_doc.txt
echo "All systems nominal" >> secret_doc.txt

echo "Created secret_doc.txt:"
cat secret_doc.txt
echo ""

echo -e "${YELLOW}Encoding file to PNG...${NC}"
./o2png encode-file --input secret_doc.txt --output secret_doc.png
echo ""

# Demo 5: Decode file
echo -e "${CYAN}📂 Demo 5: Decoding file from PNG${NC}"
mkdir -p extracted
./o2png decode-file --input secret_doc.png --output-dir extracted
echo ""

echo -e "${GREEN}Extracted file content:${NC}"
cat extracted/secret_doc.txt
echo ""

# Demo 6: Capture system state
echo -e "${CYAN}💾 Demo 6: Capturing system state${NC}"

if curl -s http://localhost:8100/health > /dev/null 2>&1; then
    echo -e "${GREEN}Reactor core is online, capturing state...${NC}"
    curl -s http://localhost:8100/dns/list | python3 -m json.tool > system_snapshot.json
    echo "DNS state captured to system_snapshot.json"
    echo ""

    echo -e "${YELLOW}Encoding system state to PNG...${NC}"
    ./o2png encode --input system_snapshot.json --output system_backup_$(date +%Y%m%d_%H%M%S).png --visual
    echo ""
else
    echo -e "${YELLOW}⚠️  Reactor core not running, skipping live capture${NC}"
    echo ""
fi

# Summary
echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                        DEMO COMPLETE                                 ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}✅ Generated Files:${NC}"
ls -lh *.png *.json 2>/dev/null | tail -10
echo ""

echo -e "${CYAN}🔍 To inspect any PNG:${NC}"
echo "   ./o2png info --input <file.png>"
echo ""

echo -e "${CYAN}🔓 To decode any PNG:${NC}"
echo "   ./o2png decode --input <file.png>"
echo ""

echo -e "${YELLOW}💡 Tip: PNG files look like normal images but contain hidden data!${NC}"
echo ""
