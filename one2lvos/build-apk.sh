#!/bin/bash
###############################################################################
# One2lvOS APK Build Script
# Builds the Android APK for One2lvOS mobile application
###############################################################################

set -e

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║       ONE2LVOS APK BUILD SYSTEM                                      ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Check prerequisites
echo -e "${CYAN}[1/6] Checking prerequisites...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js 14 or higher.${NC}"
    exit 1
fi

if ! command -v java &> /dev/null; then
    echo -e "${RED}❌ Java not found. Please install Java JDK 11 or higher.${NC}"
    exit 1
fi

if [ -z "$ANDROID_HOME" ]; then
    echo -e "${YELLOW}⚠️  ANDROID_HOME not set. Attempting to find Android SDK...${NC}"

    # Try common locations
    if [ -d "$HOME/Android/Sdk" ]; then
        export ANDROID_HOME="$HOME/Android/Sdk"
    elif [ -d "$HOME/Library/Android/sdk" ]; then
        export ANDROID_HOME="$HOME/Library/Android/sdk"
    else
        echo -e "${RED}❌ Android SDK not found. Please install Android Studio and set ANDROID_HOME.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Prerequisites OK${NC}"
echo -e "   Node: $(node --version)"
echo -e "   Java: $(java -version 2>&1 | head -n 1)"
echo -e "   Android SDK: $ANDROID_HOME"
echo ""

# Install npm dependencies
echo -e "${CYAN}[2/6] Installing npm dependencies...${NC}"
npm install
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Copy web assets
echo -e "${CYAN}[3/6] Syncing web assets to Android...${NC}"
npx cap sync android
echo -e "${GREEN}✅ Assets synced${NC}"
echo ""

# Clean previous builds
echo -e "${CYAN}[4/6] Cleaning previous builds...${NC}"
cd android
if [ -f "./gradlew" ]; then
    ./gradlew clean
else
    echo -e "${YELLOW}⚠️  Gradlew not found, skipping clean${NC}"
fi
cd ..
echo -e "${GREEN}✅ Clean complete${NC}"
echo ""

# Build APK
echo -e "${CYAN}[5/6] Building APK (Debug)...${NC}"
cd android
if [ -f "./gradlew" ]; then
    ./gradlew assembleDebug
    BUILD_SUCCESS=$?
else
    echo -e "${RED}❌ Gradle wrapper not found. Please run this from Android Studio first.${NC}"
    exit 1
fi
cd ..

if [ $BUILD_SUCCESS -eq 0 ]; then
    echo -e "${GREEN}✅ Build complete${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi
echo ""

# Locate APK
echo -e "${CYAN}[6/6] Locating APK...${NC}"
APK_PATH="android/app/build/outputs/apk/debug/app-debug.apk"

if [ -f "$APK_PATH" ]; then
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo -e "${GREEN}✅ APK built successfully!${NC}"
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                     BUILD SUCCESSFUL                                 ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${GREEN}📱 APK Location:${NC} $APK_PATH"
    echo -e "${GREEN}📦 Size:${NC} $APK_SIZE"
    echo ""
    echo -e "${CYAN}To install on device:${NC}"
    echo "   adb install $APK_PATH"
    echo ""
    echo -e "${CYAN}Or copy the APK to your device and install manually.${NC}"
    echo ""
else
    echo -e "${RED}❌ APK not found at expected location${NC}"
    echo "Expected: $APK_PATH"
    exit 1
fi

# Optional: Install to connected device
read -p "Install to connected Android device now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${CYAN}Installing to device...${NC}"
    adb install -r "$APK_PATH"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Installed successfully!${NC}"
    else
        echo -e "${YELLOW}⚠️  Installation failed. Make sure USB debugging is enabled.${NC}"
    fi
fi

echo ""
echo -e "${GREEN}🎉 Done!${NC}"
