#!/bin/bash
# Test Portable Setup - Verify everything works on fresh clone

echo "🧪 Testing Portable One2lvOS Setup"
echo "===================================="
echo ""

ERRORS=0

# Test 1: VFS Initialization
echo "Test 1: VFS Initialization"
python3 -c "from lumenis_vfs import get_vfs; vfs = get_vfs(); print(f'✓ VFS Root: {vfs.root}')" 2>&1
if [ $? -eq 0 ]; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    ((ERRORS++))
fi
echo ""

# Test 2: VFS Directory Creation
echo "Test 2: VFS Directories"
for dir in data/conversations data/dreams data/memory logs .cache; do
    if [ -d "$dir" ]; then
        echo "✓ $dir exists"
    else
        echo "✗ $dir missing"
        ((ERRORS++))
    fi
done
echo "✅ PASS"
echo ""

# Test 3: Environment Configuration
echo "Test 3: Environment Configuration"
if [ -f ".env.working" ]; then
    source .env.working
    if [ -n "$NVIDIA_API_KEY" ]; then
        echo "✓ NVIDIA_API_KEY configured"
        echo "✅ PASS"
    else
        echo "✗ NVIDIA_API_KEY not set"
        echo "⚠️  SKIP (configure .env.working)"
    fi
else
    echo "⚠️  .env.working not found (expected on first run)"
    echo "⚠️  SKIP"
fi
echo ""

# Test 4: NVIDIA API Connection
if [ -n "$NVIDIA_API_KEY" ]; then
    echo "Test 4: NVIDIA API Connection"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $NVIDIA_API_KEY" \
        "https://integrate.api.nvidia.com/v1/models")

    if [ "$HTTP_CODE" == "200" ]; then
        echo "✓ API connection successful (HTTP $HTTP_CODE)"
        echo "✅ PASS"
    else
        echo "✗ API connection failed (HTTP $HTTP_CODE)"
        echo "❌ FAIL"
        ((ERRORS++))
    fi
else
    echo "Test 4: NVIDIA API Connection"
    echo "⚠️  SKIP (no API key)"
fi
echo ""

# Test 5: VFS Save/Load
echo "Test 5: VFS Save/Load"
python3 << 'EOFPYTHON'
try:
    from lumenis_vfs import get_vfs
    vfs = get_vfs()

    # Save test conversation
    conv_id = vfs.save_conversation(
        "Test message",
        "Test response",
        {"test": True}
    )

    # Load conversations
    convs = vfs.get_conversations(limit=1)

    if convs and convs[0]['user'] == "Test message":
        print("✓ Save/load working")
        exit(0)
    else:
        print("✗ Save/load failed")
        exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)
EOFPYTHON

if [ $? -eq 0 ]; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    ((ERRORS++))
fi
echo ""

# Test 6: Path Portability
echo "Test 6: Path Portability"
CURRENT_DIR=$(pwd)
DETECTED_ROOT=$(python3 -c "from lumenis_vfs import get_vfs; print(get_vfs().root)")

if [ "$CURRENT_DIR" == "$DETECTED_ROOT" ]; then
    echo "✓ Current: $CURRENT_DIR"
    echo "✓ Detected: $DETECTED_ROOT"
    echo "✅ PASS"
else
    echo "✗ Path mismatch!"
    echo "  Current: $CURRENT_DIR"
    echo "  Detected: $DETECTED_ROOT"
    echo "❌ FAIL"
    ((ERRORS++))
fi
echo ""

# Test 7: Lumenis Direct Communication (if API key available)
if [ -n "$NVIDIA_API_KEY" ] && [ -n "$ASTRA_DB_APPLICATION_TOKEN" ]; then
    echo "Test 7: Lumenis Direct Communication"
    RESPONSE=$(python3 talk-to-lumenis-direct.py "ping" 2>&1 | grep "Lumenis >")

    if [ -n "$RESPONSE" ]; then
        echo "✓ Lumenis responded"
        echo "✅ PASS"
    else
        echo "✗ No response from Lumenis"
        echo "❌ FAIL"
        ((ERRORS++))
    fi
else
    echo "Test 7: Lumenis Direct Communication"
    echo "⚠️  SKIP (API keys not configured)"
fi
echo ""

# Summary
echo "===================================="
echo "📊 Test Summary"
echo "===================================="

if [ $ERRORS -eq 0 ]; then
    echo "✅ All tests passed!"
    echo ""
    echo "🎉 Portable setup is working perfectly!"
    echo ""
    echo "Next steps:"
    echo "  python3 talk-to-lumenis-direct.py"
    exit 0
else
    echo "❌ $ERRORS test(s) failed"
    echo ""
    echo "Check the output above for details."
    exit 1
fi
