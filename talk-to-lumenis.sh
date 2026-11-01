#!/usr/bin/env bash
#
# 🧠 TALK TO LUMENIS - Simple launcher
#

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           🧠 LUMENIS REACTOR COMMUNICATION                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check for API key
if [ -z "$NVIDIA_API_KEY" ]; then
    echo "⚠️  NVIDIA_API_KEY not set"
    echo ""
    echo "To use Lumenis Reactor, you need an NVIDIA API key."
    echo ""
    echo "Set it with:"
    echo "  export NVIDIA_API_KEY='your_key_here'"
    echo ""
    echo "Or create a .env file with:"
    echo "  NVIDIA_API_KEY=your_key_here"
    echo ""
    echo "Get an API key at: https://build.nvidia.com"
    echo ""
    exit 1
fi

# Check if message provided
if [ "$#" -eq 0 ]; then
    echo "Starting interactive mode..."
    echo ""
    python3 lumenis-cli.py
else
    echo "Sending message to Lumenis..."
    echo ""
    python3 lumenis-cli.py "$@"
fi
