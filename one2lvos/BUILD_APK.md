# Building One2lvOS APK

This guide explains how to build the One2lvOS Android APK.

## Prerequisites

You need the following installed on your system:

1. **Node.js** (v14 or higher)
2. **Java JDK** (v11 or higher)
3. **Android Studio** with Android SDK
4. **Gradle** (usually comes with Android Studio)

### Android Studio Setup

1. Download and install Android Studio from: https://developer.android.com/studio
2. Open Android Studio and go to: Tools > SDK Manager
3. Install the following:
   - Android SDK Platform 33 (or latest)
   - Android SDK Build-Tools
   - Android SDK Command-line Tools
   - Android Emulator (optional, for testing)

4. Set environment variables:
   ```bash
   export ANDROID_HOME=$HOME/Android/Sdk
   export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
   ```

## Build Steps

### Option 1: Using Android Studio (Recommended)

1. Open the project:
   ```bash
   cd /path/to/one2lvos
   ```

2. Open Android Studio and select: **Open an Existing Project**

3. Navigate to: `one2lvos/android` and open it

4. Wait for Gradle sync to complete

5. Build the APK:
   - Go to: **Build > Build Bundle(s) / APK(s) > Build APK(s)**
   - Or use the terminal:
     ```bash
     cd android
     ./gradlew assembleDebug
     ```

6. Find your APK at:
   ```
   android/app/build/outputs/apk/debug/app-debug.apk
   ```

### Option 2: Command Line Build

1. Ensure the server is running or update API URLs in `www/index.html`:
   ```javascript
   const API_URL = 'https://your-server-url';
   const WS_URL = 'wss://your-server-url';
   ```

2. Sync Capacitor (copies web assets to Android):
   ```bash
   npx cap sync android
   ```

3. Build the APK:
   ```bash
   cd android
   ./gradlew assembleDebug
   ```

4. For release build (signed APK):
   ```bash
   ./gradlew assembleRelease
   ```

### Option 3: Using Build Script

Run the provided build script:
```bash
chmod +x build-apk.sh
./build-apk.sh
```

## Build Outputs

- **Debug APK**: `android/app/build/outputs/apk/debug/app-debug.apk`
- **Release APK**: `android/app/build/outputs/apk/release/app-release.apk`

## Installing on Android Device

### Via USB (ADB)

1. Enable Developer Options and USB Debugging on your Android device

2. Connect device via USB

3. Install the APK:
   ```bash
   adb install android/app/build/outputs/apk/debug/app-debug.apk
   ```

### Via File Transfer

1. Copy the APK file to your device
2. Open it on your device
3. Allow installation from unknown sources if prompted
4. Install the app

## Configuration

### Update Server URLs

Before building for production, update the API endpoints in `www/index.html`:

```javascript
// Line ~20-21
const API_URL = 'https://your-production-server.com';
const WS_URL = 'wss://your-production-server.com';
```

### App Icon and Splash Screen

To customize the app icon:

1. Create icons in these sizes:
   - 36x36, 48x48, 72x72, 96x96, 144x144, 192x192

2. Place them in:
   ```
   android/app/src/main/res/mipmap-*/ic_launcher.png
   ```

3. Run:
   ```bash
   npx cap sync android
   ```

## Troubleshooting

### Gradle Build Failed

1. Check Java version:
   ```bash
   java -version
   # Should be 11 or higher
   ```

2. Clean and rebuild:
   ```bash
   cd android
   ./gradlew clean
   ./gradlew assembleDebug
   ```

### SDK Not Found

Set ANDROID_HOME:
```bash
export ANDROID_HOME=$HOME/Library/Android/sdk  # macOS
export ANDROID_HOME=$HOME/Android/Sdk          # Linux
export ANDROID_HOME=C:\Users\YourName\AppData\Local\Android\Sdk  # Windows
```

### Cannot Connect to Server

Make sure:
1. The One2lvOS server is running
2. Your Android device can reach the server IP
3. Update API_URL in `www/index.html` to your server's IP:
   ```javascript
   const API_URL = 'http://192.168.1.100:8080';
   ```

## Release Build (Production)

For a signed release APK:

1. Generate a keystore:
   ```bash
   keytool -genkey -v -keystore one2lvos.keystore -alias one2lvos -keyalg RSA -keysize 2048 -validity 10000
   ```

2. Create `android/key.properties`:
   ```properties
   storePassword=your-store-password
   keyPassword=your-key-password
   keyAlias=one2lvos
   storeFile=../one2lvos.keystore
   ```

3. Update `android/app/build.gradle` to use the keystore

4. Build release:
   ```bash
   cd android
   ./gradlew assembleRelease
   ```

## Next Steps

- Install the APK on your device
- Start the One2lvOS server
- Open the app and connect

## Support

For issues, check:
- Capacitor docs: https://capacitorjs.com
- Android docs: https://developer.android.com
- One2lvOS repo: https://github.com/one2lv-com/One2lvos
