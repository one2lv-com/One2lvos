#!/bin/bash
# Clear any existing builds
echo "Starting ARIA APK Build with Progress Tracking..."
# Portable path (item 18): run from the folder this script is in (or ARIA_BUILD_DIR).
cd "${ARIA_BUILD_DIR:-$(dirname "$(readlink -f "$0")")}" || exit 1

# Run buildozer in the background and redirect output to a log
buildozer -v android debug > build_output.log 2>&1 &
BUILD_PID=$!

# Run the monitor script in the foreground
python3 monitor_build.py

# If monitor exits (success or failure), wait for the build process to finish
wait $BUILD_PID
