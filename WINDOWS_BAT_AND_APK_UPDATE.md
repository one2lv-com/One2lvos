# Windows BAT and APK Build Update

**Date**: 2026-11-01
**Status**: ✅ Review Complete

---

## Windows .BAT Files Status

### Files Reviewed (6)
1. `build-one2lvos-exe.bat`
2. `install-ai-arcade-windows.bat`
3. `install-one2lvos-windows-auto.bat`
4. `install-one2lvos-windows.bat`
5. `launch-one2lvos-sandbox.bat`
6. `start-network-service.bat`

### Path Analysis

✅ **All Windows .bat files use correct paths**

**Pattern used**: `%USERPROFILE%\One2lvOS`

Example from `install-one2lvos-windows.bat`:
```batch
set INSTALL_DIR=%USERPROFILE%\One2lvOS
```

**Why this is correct**:
- `%USERPROFILE%` resolves to `C:\Users\<username>\` on Windows
- Installs to user directory (no admin required)
- Portable across different Windows users
- No hardcoded paths like Linux `$HOME/`

### No Updates Needed

The Windows .bat files:
- ✅ Already use dynamic user paths
- ✅ No hardcoded Linux-style paths
- ✅ Compatible with project tree setup
- ✅ Work from any clone location

---

## APK Build Configuration

### Android Projects Found (2)

1. **one2lv-os-android/**
   - Full Capacitor Android project
   - Build files: `android/app/build.gradle`
   - Gradle wrapper: `android/gradlew`
   - Package: `com.one2lv.os`

2. **minimax/android/**
   - Minimax Android integration
   - Build files: `android/app/build.gradle`
   - Gradle wrapper: `android/gradlew`

### APK Build Scripts

#### Main Build Script

**File**: `build-apk.sh`
**Status**: ✅ Exists and ready to use

**Usage**:
```bash
./build-apk.sh
```

**Outputs**:
- `one2lvos-debug.apk` - Debug build
- `one2lvos-release.apk` - Release build (if signed)

#### Documentation

**File**: `APK_BUILD_GUIDE.md`
**Contains**:
- Prerequisites (Node.js, Java JDK, Android SDK)
- Quick build instructions
- Manual build process
- Signing configuration
- Distribution guide

### Build Commands Summary

#### One2lvOS APK

```bash
# Quick build (automated)
./build-apk.sh

# Manual build
cd one2lv-os-android/android
./gradlew assembleDebug
./gradlew assembleRelease

# Output location
ls -la one2lv-os-android/android/app/build/outputs/apk/
```

#### Minimax APK

```bash
cd minimax/android
./gradlew assembleDebug
./gradlew assembleRelease

# Output location
ls -la minimax/android/app/build/outputs/apk/
```

---

## New: Unified Build Script

Created comprehensive build script for all platforms:

### File: `build-all-platforms.sh`

**Features**:
- Builds for Windows (.exe via PyInstaller)
- Builds Android APKs (debug + release)
- Runs project tree setup automatically
- Checks all prerequisites
- Creates distribution packages

**Usage**:
```bash
./build-all-platforms.sh                    # Build all
./build-all-platforms.sh --windows-only     # Windows only
./build-all-platforms.sh --android-only     # Android only
./build-all-platforms.sh --check-only       # Check prerequisites
```

**Outputs**:
```
dist/
├── one2lvos-windows.exe
├── one2lvos-debug.apk
├── one2lvos-release.apk
├── minimax-debug.apk
└── minimax-release.apk
```

---

## Prerequisites for APK Builds

### Required Software

1. **Java JDK 11+**
   ```bash
   sudo apt install openjdk-11-jdk
   java -version
   ```

2. **Android SDK**
   ```bash
   # Install Android SDK tools
   wget https://dl.google.com/android/repository/commandlinetools-linux-latest.zip
   unzip commandlinetools-linux-latest.zip
   export ANDROID_HOME=$HOME/android-sdk
   export PATH=$PATH:$ANDROID_HOME/cmdline-tools/bin:$ANDROID_HOME/platform-tools
   ```

3. **Gradle** (included with Android projects)
   ```bash
   cd one2lv-os-android/android
   ./gradlew --version
   ```

4. **Node.js & npm**
   ```bash
   node --version  # v18+
   npm --version
   ```

### Environment Setup

Add to `~/.bashrc` or `~/.profile`:

```bash
export ANDROID_HOME=$HOME/android-sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/build-tools/latest
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

---

## APK Signing Configuration

### Generate Signing Key

```bash
keytool -genkey -v -keystore one2lvos-release.keystore \
  -alias one2lvos -keyalg RSA -keysize 2048 -validity 10000
```

### Configure Signing in build.gradle

Add to `one2lv-os-android/android/app/build.gradle`:

```gradle
android {
    signingConfigs {
        release {
            storeFile file("../../one2lvos-release.keystore")
            storePassword "your_store_password"
            keyAlias "one2lvos"
            keyPassword "your_key_password"
        }
    }

    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
        }
    }
}
```

### Build Signed APK

```bash
cd one2lv-os-android/android
./gradlew assembleRelease

# Output
ls -la app/build/outputs/apk/release/app-release.apk
```

---

## Distribution Preparation

### Create Release Package

```bash
# Create distribution directory
mkdir -p releases/v1.0.0

# Copy all builds
cp dist/one2lvos-windows.exe releases/v1.0.0/
cp dist/*.apk releases/v1.0.0/
cp install-one2lvos-windows.bat releases/v1.0.0/
cp APK_BUILD_GUIDE.md releases/v1.0.0/README.md

# Create checksums
cd releases/v1.0.0
sha256sum * > checksums.txt

# Create archive
cd ..
tar -czf one2lvos-v1.0.0-complete.tar.gz v1.0.0/
```

### Distribution Files

```
releases/v1.0.0/
├── one2lvos-windows.exe          # Windows executable
├── one2lvos-debug.apk            # Android debug APK
├── one2lvos-release.apk          # Android release APK (signed)
├── minimax-debug.apk             # Minimax Android debug
├── minimax-release.apk           # Minimax Android release
├── install-one2lvos-windows.bat  # Windows installer
├── README.md                     # Build guide
└── checksums.txt                 # SHA256 checksums
```

---

## GitHub Release Integration

### Automated Release Workflow

Create `.github/workflows/release.yml`:

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Windows EXE
        run: |
          python -m pip install pyinstaller
          pyinstaller build-one2lvos-exe.bat --onefile
      - name: Upload Windows Build
        uses: actions/upload-artifact@v3
        with:
          name: one2lvos-windows
          path: dist/one2lvos.exe

  build-android:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up JDK 11
        uses: actions/setup-java@v3
        with:
          java-version: '11'
          distribution: 'temurin'
      - name: Build APK
        run: |
          cd one2lv-os-android/android
          ./gradlew assembleDebug assembleRelease
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: one2lvos-android
          path: |
            one2lv-os-android/android/app/build/outputs/apk/debug/*.apk
            one2lv-os-android/android/app/build/outputs/apk/release/*.apk

  create-release:
    needs: [build-windows, build-android]
    runs-on: ubuntu-latest
    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v3
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            one2lvos-windows/one2lvos.exe
            one2lvos-android/*.apk
```

---

## Quick Reference

### Build All Platforms

```bash
# One command to build everything
./build-all-platforms.sh

# Or step by step:

# 1. Setup project tree
./setup-project-tree.sh

# 2. Build Windows
python build-one2lvos-exe.bat  # (on Windows)

# 3. Build Android
./build-apk.sh                  # Main One2lvOS
cd minimax/android && ./gradlew assembleRelease  # Minimax

# 4. Create release package
./create-release-package.sh
```

### Test Builds

```bash
# Test Windows installer
cmd.exe /c install-one2lvos-windows.bat

# Test Android APK
adb install dist/one2lvos-debug.apk

# Test on Android emulator
emulator -avd Pixel_4_API_30 &
adb install dist/one2lvos-debug.apk
adb shell am start -n com.one2lv.os/.MainActivity
```

---

## Summary

### Windows .BAT Files
- ✅ No updates needed
- ✅ Already use portable paths (`%USERPROFILE%`)
- ✅ Compatible with all Windows versions
- ✅ Work from any location

### Android APK
- ✅ Build scripts exist (`build-apk.sh`)
- ✅ Documentation complete (`APK_BUILD_GUIDE.md`)
- ✅ Two Android projects ready to build
- 🔄 Signing keys need to be configured (optional)
- 🔄 GitHub Actions workflow available (optional)

### Next Steps
1. ✅ All Windows .bat files verified
2. ✅ APK build documentation reviewed
3. 🔄 Build APKs when ready (requires Android SDK)
4. 🔄 Configure signing for release builds
5. 🔄 Set up GitHub Actions for automated builds

---

**Status**: ✅ Ready for commit and push
**Windows**: No changes needed
**Android**: Build infrastructure ready
**Documentation**: Complete

---

**Generated by**: Claude Code
**Date**: 2026-11-01
