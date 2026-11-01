# One2lvOS APK Build Guide

## Overview

This guide explains how to build the One2lvOS Android APK from the web interface.

---

## Prerequisites

### Required Software

1. **Node.js** (v18+)
   ```bash
   # Check version
   node --version
   npm --version
   ```

2. **Java JDK** (11 or higher)
   ```bash
   # Check version
   java -version
   javac -version
   ```

3. **Android SDK** (API Level 24+)
   ```bash
   # Set environment variable
   export ANDROID_HOME=/path/to/android-sdk
   export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
   ```

4. **Cordova**
   ```bash
   npm install -g cordova
   ```

5. **Gradle** (usually included with Android SDK)
   ```bash
   gradle --version
   ```

---

## Quick Build (Automated)

### Option 1: Using Build Script

```bash
cd /path/to/One2lvos
chmod +x build-apk.sh
./build-apk.sh
```

This will:
1. Check all prerequisites
2. Initialize Cordova project
3. Copy web assets
4. Configure Android platform
5. Build debug APK
6. Build release APK (if signing key exists)

**Output**: `one2lvos-debug.apk` and/or `one2lvos-release.apk`

---

## Manual Build Process

### Step 1: Install Cordova

```bash
npm install -g cordova
```

### Step 2: Create Cordova Project

```bash
cordova create cordova-app com.one2lv.os One2lvOS
cd cordova-app
```

### Step 3: Add Android Platform

```bash
cordova platform add android
```

### Step 4: Copy Web Assets

```bash
# Copy the standalone demo as the main app
cp ../demo-standalone.html www/index.html

# Or copy the full system
cp -r ../static/* www/
cp ../demo-standalone.html www/index.html
```

### Step 5: Configure (config.xml)

Edit `config.xml`:

```xml
<?xml version='1.0' encoding='utf-8'?>
<widget id="com.one2lv.os" version="2.0.0" xmlns="http://www.w3.org/ns/widgets">
    <name>One2lvOS</name>
    <description>
        Sovereign Agentic Operating System with Aether-Lumenis Core
    </description>
    <author email="support@one2lv.com" href="https://one2lv.com">
        One2lv Team
    </author>
    <content src="index.html" />
    <access origin="*" />
    <platform name="android">
        <preference name="AndroidLaunchMode" value="singleTop" />
    </platform>
    <preference name="android-minSdkVersion" value="24" />
    <preference name="android-targetSdkVersion" value="33" />
</widget>
```

### Step 6: Install Plugins

```bash
cordova plugin add cordova-plugin-whitelist
cordova plugin add cordova-plugin-device
```

### Step 7: Build Debug APK

```bash
cordova build android --debug
```

**Output**: `platforms/android/app/build/outputs/apk/debug/app-debug.apk`

### Step 8: Build Release APK (Optional)

First, create a signing key:

```bash
keytool -genkey -v -keystore one2lv-release-key.keystore \
  -alias one2lv \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

Then build:

```bash
cordova build android --release -- \
  --keystore=../one2lv-release-key.keystore \
  --storePassword=YOUR_PASSWORD \
  --alias=one2lv \
  --password=YOUR_PASSWORD
```

**Output**: `platforms/android/app/build/outputs/apk/release/app-release.apk`

---

## Alternative: Capacitor (Modern Approach)

### Option 2: Using Capacitor

```bash
# Install Capacitor
npm install @capacitor/core @capacitor/cli
npm install @capacitor/android

# Initialize
npx cap init "One2lvOS" "com.one2lv.os"

# Add Android platform
npx cap add android

# Copy web assets
npx cap copy

# Open in Android Studio
npx cap open android

# Build in Android Studio
# Build → Generate Signed Bundle / APK → APK
```

---

## Environment Setup (Ubuntu/Debian)

### Install Java JDK

```bash
sudo apt update
sudo apt install openjdk-11-jdk
java -version
```

### Install Android SDK

```bash
# Download Android command-line tools
wget https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip

# Extract
unzip commandlinetools-linux-9477386_latest.zip -d ~/android-sdk

# Set environment variables
export ANDROID_HOME=~/android-sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools

# Accept licenses
sdkmanager --licenses

# Install required packages
sdkmanager "platform-tools" "platforms;android-33" "build-tools;33.0.0"
```

### Install Gradle

```bash
sudo apt install gradle
```

---

## Troubleshooting

### Issue: ANDROID_HOME not set

**Solution**:
```bash
export ANDROID_HOME=/path/to/android-sdk
echo 'export ANDROID_HOME=/path/to/android-sdk' >> ~/.bashrc
```

### Issue: Java version mismatch

**Solution**:
```bash
# Check available versions
update-alternatives --list java

# Switch version
sudo update-alternatives --config java
```

### Issue: Gradle build fails

**Solution**:
```bash
cd platforms/android
./gradlew clean
cd ../..
cordova build android --debug
```

### Issue: Out of memory

**Solution**:
```bash
export GRADLE_OPTS="-Xmx4096m -XX:MaxPermSize=512m"
```

---

## Testing the APK

### Install on Device

```bash
# Via ADB
adb devices
adb install one2lvos-debug.apk

# Or via Android Studio
# Drag and drop APK onto emulator
```

### Verify Installation

```bash
adb shell pm list packages | grep one2lv
```

---

## Distribution

### Google Play Store

1. Build release APK with signing key
2. Go to [Google Play Console](https://play.google.com/console)
3. Create new app
4. Upload APK
5. Fill out store listing
6. Submit for review

### Direct Download

1. Upload to web server:
   ```bash
   scp one2lvos-release.apk user@server:/var/www/downloads/
   ```

2. Create download page:
   ```html
   <a href="/downloads/one2lvos-release.apk">Download One2lvOS APK</a>
   ```

### GitHub Releases

```bash
# Create release
gh release create v2.0.0 one2lvos-release.apk \
  --title "One2lvOS v2.0 - Aether-Lumenis" \
  --notes "Complete sovereign OS with Aether-Lumenis core"
```

---

## APK Optimization

### Reduce APK Size

```bash
# Enable ProGuard (in build.gradle)
android {
    buildTypes {
        release {
            minifyEnabled true
            shrinkResources true
        }
    }
}
```

### Enable App Signing

In `build.json`:
```json
{
  "android": {
    "release": {
      "keystore": "one2lv-release-key.keystore",
      "storePassword": "password",
      "alias": "one2lv",
      "password": "password"
    }
  }
}
```

---

## Current Environment Status

**⚠️ This sandbox environment does NOT have Android build tools installed.**

To build the APK, you need:
- A local machine with Android development environment
- Or a CI/CD system with Android SDK (GitHub Actions, GitLab CI)
- Or a cloud build service (Bitrise, Codemagic, App Center)

---

## Alternative: GitHub Actions Build

Create `.github/workflows/build-apk.yml`:

```yaml
name: Build APK

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          distribution: 'temurin'
          java-version: '11'

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install Cordova
        run: npm install -g cordova

      - name: Build APK
        run: |
          chmod +x build-apk.sh
          ./build-apk.sh

      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: one2lvos-apk
          path: one2lvos-debug.apk
```

---

## Summary

| Method | Difficulty | Build Time | Best For |
|--------|------------|------------|----------|
| Automated Script | Easy | 5-10 min | Quick builds |
| Manual Cordova | Medium | 10-20 min | Custom config |
| Capacitor + Android Studio | Medium | 15-30 min | Full control |
| GitHub Actions | Easy | 10-15 min | CI/CD |

**Recommended**: Use automated script for quick builds, GitHub Actions for automated releases.

---

## Next Steps

1. Set up Android development environment on your local machine
2. Run `./build-apk.sh` to generate APK
3. Test on Android device or emulator
4. Upload to GitHub Releases or Google Play Store

---

🌷 **One2lvOS APK Build System**
*Ready for Android deployment*
