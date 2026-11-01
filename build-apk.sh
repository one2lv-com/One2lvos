#!/bin/bash
# One2lvOS APK Build Script
# Requires: Node.js, Cordova, Android SDK, Java JDK 11+

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           ONE2LVOS APK BUILD SYSTEM                           ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}[1/8] Checking prerequisites...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js: $(node --version)${NC}"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ npm not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ npm: $(npm --version)${NC}"

if ! command -v cordova &> /dev/null; then
    echo -e "${YELLOW}⚠ Cordova not found, installing...${NC}"
    npm install -g cordova
fi
echo -e "${GREEN}✓ Cordova: $(cordova --version)${NC}"

if ! command -v java &> /dev/null; then
    echo -e "${RED}✗ Java not found. Install Java JDK 11 or higher${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Java: $(java -version 2>&1 | head -1)${NC}"

if [ -z "$ANDROID_HOME" ]; then
    echo -e "${RED}✗ ANDROID_HOME not set${NC}"
    echo -e "${YELLOW}Set ANDROID_HOME to your Android SDK path${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Android SDK: $ANDROID_HOME${NC}"

# Initialize Cordova project if not exists
echo ""
echo -e "${YELLOW}[2/8] Initializing Cordova project...${NC}"

if [ ! -d "cordova-app" ]; then
    cordova create cordova-app com.one2lv.os One2lvOS
    cd cordova-app
    cordova platform add android
    cd ..
    echo -e "${GREEN}✓ Cordova project created${NC}"
else
    echo -e "${GREEN}✓ Cordova project exists${NC}"
fi

# Copy web assets
echo ""
echo -e "${YELLOW}[3/8] Copying web assets...${NC}"

mkdir -p cordova-app/www
cp demo-standalone.html cordova-app/www/index.html
cp -r static/* cordova-app/www/ 2>/dev/null || true

echo -e "${GREEN}✓ Web assets copied${NC}"

# Configure Cordova
echo ""
echo -e "${YELLOW}[4/8] Configuring Cordova...${NC}"

cat > cordova-app/config.xml <<'XML'
<?xml version='1.0' encoding='utf-8'?>
<widget id="com.one2lv.os" version="2.0.0" xmlns="http://www.w3.org/ns/widgets" xmlns:cdv="http://cordova.apache.org/ns/1.0">
    <name>One2lvOS</name>
    <description>
        Sovereign Agentic Operating System with Aether-Lumenis Core
    </description>
    <author email="support@one2lv.com" href="https://one2lv.com">
        One2lv Team
    </author>
    <content src="index.html" />
    <access origin="*" />
    <allow-intent href="http://*/*" />
    <allow-intent href="https://*/*" />
    <allow-intent href="tel:*" />
    <allow-intent href="sms:*" />
    <allow-intent href="mailto:*" />
    <allow-intent href="geo:*" />
    <platform name="android">
        <allow-intent href="market:*" />
        <preference name="AndroidInsecureFileModeEnabled" value="true" />
        <preference name="AndroidLaunchMode" value="singleTop" />
    </platform>
    <preference name="DisallowOverscroll" value="true" />
    <preference name="android-minSdkVersion" value="24" />
    <preference name="android-targetSdkVersion" value="33" />
</widget>
XML

echo -e "${GREEN}✓ Cordova configured${NC}"

# Install Cordova plugins
echo ""
echo -e "${YELLOW}[5/8] Installing Cordova plugins...${NC}"

cd cordova-app
cordova plugin add cordova-plugin-whitelist
cordova plugin add cordova-plugin-device
cd ..

echo -e "${GREEN}✓ Plugins installed${NC}"

# Build APK (debug)
echo ""
echo -e "${YELLOW}[6/8] Building debug APK...${NC}"

cd cordova-app
cordova build android --debug

if [ -f "platforms/android/app/build/outputs/apk/debug/app-debug.apk" ]; then
    echo -e "${GREEN}✓ Debug APK built successfully${NC}"
    cp platforms/android/app/build/outputs/apk/debug/app-debug.apk ../one2lvos-debug.apk
    echo -e "${GREEN}✓ APK copied to: one2lvos-debug.apk${NC}"
else
    echo -e "${RED}✗ Debug APK build failed${NC}"
    exit 1
fi

cd ..

# Build APK (release)
echo ""
echo -e "${YELLOW}[7/8] Building release APK...${NC}"
echo -e "${YELLOW}Note: Release APK requires signing key${NC}"

if [ -f "one2lv-release-key.keystore" ]; then
    cd cordova-app
    cordova build android --release -- --keystore=../one2lv-release-key.keystore --storePassword=one2lv123 --alias=one2lv --password=one2lv123

    if [ -f "platforms/android/app/build/outputs/apk/release/app-release.apk" ]; then
        echo -e "${GREEN}✓ Release APK built successfully${NC}"
        cp platforms/android/app/build/outputs/apk/release/app-release.apk ../one2lvos-release.apk
        echo -e "${GREEN}✓ APK copied to: one2lvos-release.apk${NC}"
    fi
    cd ..
else
    echo -e "${YELLOW}⚠ No signing key found, skipping release build${NC}"
    echo -e "${YELLOW}To create signing key, run:${NC}"
    echo -e "${CYAN}keytool -genkey -v -keystore one2lv-release-key.keystore -alias one2lv -keyalg RSA -keysize 2048 -validity 10000${NC}"
fi

# Summary
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           APK BUILD COMPLETE                                  ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ -f "one2lvos-debug.apk" ]; then
    APK_SIZE=$(du -h one2lvos-debug.apk | cut -f1)
    echo -e "${GREEN}✓ Debug APK:${NC} one2lvos-debug.apk ($APK_SIZE)"
fi

if [ -f "one2lvos-release.apk" ]; then
    APK_SIZE=$(du -h one2lvos-release.apk | cut -f1)
    echo -e "${GREEN}✓ Release APK:${NC} one2lvos-release.apk ($APK_SIZE)"
fi

echo ""
echo -e "${YELLOW}Installation:${NC}"
echo -e "  adb install one2lvos-debug.apk"
echo ""
echo -e "${YELLOW}Or upload to:${NC}"
echo -e "  - Google Play Console (release)"
echo -e "  - GitHub Releases"
echo -e "  - Direct download server"
echo ""
