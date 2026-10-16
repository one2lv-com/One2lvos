# One2lvOS Mobile APK

Welcome to the One2lvOS Mobile Application!

## Quick Start

### For Users (APK Installation)

If you have a pre-built APK:

1. Transfer `app-debug.apk` to your Android device
2. Enable "Install from Unknown Sources" in Settings
3. Tap the APK file to install
4. Open One2lvOS app
5. Make sure your One2lvOS server is running and accessible

### For Developers (Building from Source)

To build your own APK:

```bash
# 1. Install dependencies
npm install

# 2. Run the build script
./build-apk.sh

# 3. Find your APK at:
# android/app/build/outputs/apk/debug/app-debug.apk
```

See `BUILD_APK.md` for detailed build instructions.

## What's Inside

This mobile app provides full access to One2lvOS features:

- **AI Chat** - Interact with the AI assistant
- **AI Coach** - Get personalized gaming coaching
- **Game Management** - Start games, view stats, check leaderboards
- **System Monitor** - View system status and manage settings

## Features

### AI Chat Interface
Real-time chat with One2lvOS AI system via WebSocket and REST API.

### AI Gaming Coach
Get personalized tips and coaching for improving your gameplay.

### Game Integration
- Start and manage games
- View leaderboards
- Track your stats and progress

### System Dashboard
- View system status
- Monitor mesh network
- Configure settings
- Test connections

## Configuration

Before using the app, you may need to update the server URLs:

Edit `www/index.html` lines 20-21:

```javascript
const API_URL = 'http://YOUR_SERVER_IP:8080';
const WS_URL = 'ws://YOUR_SERVER_IP:8080';
```

Replace `YOUR_SERVER_IP` with your actual server IP address.

## Requirements

### Server Requirements
- One2lvOS server running on an accessible network
- Server must be reachable from your mobile device
- Default port: 8080

### Mobile Requirements
- Android 5.0 (API 21) or higher
- Internet connection to reach the server
- ~10MB storage space

## Network Setup

### Same WiFi Network (Easiest)
1. Connect both server and mobile device to the same WiFi
2. Find your server's local IP: `ifconfig` (Linux/Mac) or `ipconfig` (Windows)
3. Update the app's API_URL to: `http://192.168.1.XXX:8080`

### Public Server
1. Deploy One2lvOS to a public server
2. Use domain or public IP
3. Update API_URL to: `https://yourdomain.com`
4. Enable HTTPS for secure connections

### Local Development
For testing on localhost:
1. Use Android Emulator
2. Update API_URL to: `http://10.0.2.2:8080`
3. Or use `adb reverse`: `adb reverse tcp:8080 tcp:8080`

## Troubleshooting

### App Won't Connect
- Check server is running: `curl http://localhost:8080/health`
- Verify firewall allows port 8080
- Ensure mobile device can reach server IP
- Try server IP instead of localhost

### Build Errors
- Install Android Studio and SDK
- Set ANDROID_HOME environment variable
- Run `./gradlew clean` in android directory
- See BUILD_APK.md for detailed troubleshooting

### Installation Blocked
- Enable "Unknown Sources" in Android Settings
- On Android 8+: Settings > Apps > Special Access > Install Unknown Apps
- Select your file manager and enable

## Development

### Project Structure
```
one2lvos/
├── www/                    # Web assets (mobile UI)
│   └── index.html         # Main app interface
├── android/               # Android native project
│   └── app/
│       └── build/
│           └── outputs/
│               └── apk/   # Built APK files
├── capacitor.config.json  # Capacitor configuration
├── build-apk.sh          # Build automation script
└── BUILD_APK.md          # Detailed build guide
```

### Making Changes

1. Edit `www/index.html` for UI changes
2. Sync changes: `npx cap sync android`
3. Rebuild: `./build-apk.sh`

### Adding Capacitor Plugins

```bash
npm install @capacitor/plugin-name
npx cap sync android
```

## API Endpoints

The app connects to these One2lvOS endpoints:

- `GET /health` - Health check
- `POST /api/chat` - General AI chat
- `POST /api/coach/chat` - AI coach chat
- `GET /api/system/status` - System status
- `POST /api/game/start` - Start game
- `GET /api/leaderboard` - View leaderboard
- `WS /` - WebSocket connection

See One2lvOS API documentation for complete endpoint list.

## Building for Production

For a signed release APK:

```bash
# Generate keystore
keytool -genkey -v -keystore one2lvos.keystore \
  -alias one2lvos -keyalg RSA -keysize 2048 -validity 10000

# Build release
cd android
./gradlew assembleRelease
```

See BUILD_APK.md section "Release Build (Production)" for details.

## License

Same as One2lvOS main project.

## Support

- Issues: https://github.com/one2lv-com/One2lvos/issues
- Discord: https://discord.com/invite/dBfFAcefs2
- Docs: https://github.com/one2lv-com/One2lvos

## Version

Mobile App: v1.0.0
One2lvOS: v5.0.0
Capacitor: Latest
