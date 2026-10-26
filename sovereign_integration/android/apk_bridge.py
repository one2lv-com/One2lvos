"""
Android APK Bridge for Lumenis Reactor
======================================
Integrates Android APK build system with Lumenis Reactor Core

Based on: one2lv_apk.sh
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class APKConfig:
    """Android APK build configuration"""
    app_id: str = "com.one2lv.sovereign.os"
    version_name: str = "3.0.0-Sovereign"
    version_code: int = 300
    java_home: str = "/usr/lib/jvm/java-17-openjdk-amd64"
    gradle_version: str = "8.14.3"
    build_variant: str = "debug"  # or "release"


class AndroidAPKBridge:
    """
    Bridge between Lumenis Reactor and Android APK build system
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path("/home/one2lv/one2lvos/One2lvos/one2lv-os-android")
        self.android_dir = self.project_root / "android"
        self.config = APKConfig()

    def get_build_status(self) -> Dict[str, Any]:
        """Get current build environment status"""
        java_version = "Unknown"
        gradle_version = "Unknown"
        sdk_configured = False

        try:
            # Check Java version
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            java_version = result.stderr.split('\n')[0] if result.stderr else "Unknown"
        except Exception:
            pass

        try:
            # Check if Android directory exists
            sdk_configured = (self.android_dir / "local.properties").exists()
        except Exception:
            pass

        return {
            "project_root": str(self.project_root),
            "android_dir": str(self.android_dir),
            "java_home": self.config.java_home,
            "java_version": java_version,
            "gradle_version": self.config.gradle_version,
            "sdk_configured": sdk_configured,
            "app_id": self.config.app_id,
            "version": f"{self.config.version_name} ({self.config.version_code})",
            "build_variant": self.config.build_variant,
        }

    def generate_capacitor_config(self) -> Dict[str, Any]:
        """Generate Capacitor configuration for One2lvOS"""
        return {
            "appId": self.config.app_id,
            "appName": "One2lvOS Sovereign v3.0",
            "webDir": "public",
            "bundledWebRuntime": False,
            "server": {
                "androidScheme": "https",
                "allowNavigation": ["localhost", "127.0.0.1", "*.one2lv.com"]
            },
            "plugins": {
                "O2PNGBridge": {
                    "frequencyHz": 73.0,
                    "protocolVersion": "1.0"
                },
                "LumenisReactor": {
                    "enabled": True,
                    "thermalBaseline": 0.18,
                    "resonance": 73.0
                }
            },
            "android": {
                "buildOptions": {
                    "keystorePath": "one2lv-release.keystore",
                    "keystoreAlias": "one2lv"
                }
            }
        }

    def generate_gradle_properties(self) -> str:
        """Generate gradle.properties content"""
        return f"""# One2lvOS Android Gradle Configuration
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
org.gradle.java.home={self.config.java_home}
android.useAndroidX=true
android.enableJetifier=false

# One2lvOS Sovereign Build
one2lv.appId={self.config.app_id}
one2lv.versionName={self.config.version_name}
one2lv.versionCode={self.config.version_code}
one2lv.frequencyHz=73.0
one2lv.protocol=0x1165
"""

    def generate_android_manifest_snippet(self) -> str:
        """Generate AndroidManifest.xml snippet"""
        return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{self.config.app_id}"
    android:versionCode="{self.config.version_code}"
    android:versionName="{self.config.version_name}">

    <uses-sdk android:minSdkVersion="24" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.HIGH_SAMPLING_RATE_SENSORS" />
    <uses-permission android:name="android.permission.CAMERA" />

    <application
        android:allowBackup="true"
        android:label="One2lvOS Sovereign v3.0"
        android:usesCleartextTraffic="true"
        android:theme="@style/AppTheme.NoActionBar">

        <!-- Main Activity -->
        <activity
            android:name="{self.config.app_id}.MainActivity"
            android:exported="true"
            android:configChanges="orientation|keyboardHidden|screenSize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <!-- One2lvOS Metadata -->
        <meta-data
            android:name="one2lv.frequency"
            android:value="73.0" />
        <meta-data
            android:name="one2lv.protocol"
            android:value="0x1165" />
        <meta-data
            android:name="one2lv.architecture"
            android:value="RETURN" />
    </application>
</manifest>
"""

    def get_apk_info(self) -> Dict[str, Any]:
        """Get information about built APK"""
        apk_path = self.android_dir / "app" / "build" / "outputs" / "apk" / self.config.build_variant / f"app-{self.config.build_variant}.apk"

        info = {
            "apk_path": str(apk_path),
            "exists": apk_path.exists(),
            "app_id": self.config.app_id,
            "version_name": self.config.version_name,
            "version_code": self.config.version_code,
            "build_variant": self.config.build_variant,
        }

        if apk_path.exists():
            info["size_bytes"] = apk_path.stat().st_size
            info["size_mb"] = round(apk_path.stat().st_size / (1024 * 1024), 2)

        return info

    def simulate_build(self) -> Dict[str, Any]:
        """
        Simulate APK build process
        (Actual build would require Android SDK and full environment)
        """
        return {
            "status": "SIMULATED",
            "message": "APK build simulation - actual build requires Android SDK",
            "steps": [
                "Pin JDK 17",
                "Configure Android SDK",
                "Sync Capacitor assets",
                "Run ./gradlew assembleDebug",
                "Sign APK (if release)",
                "Generate checksums"
            ],
            "config": {
                "java_home": self.config.java_home,
                "gradle_version": self.config.gradle_version,
                "app_id": self.config.app_id,
                "version": f"{self.config.version_name} ({self.config.version_code})",
            },
            "output": f"one2lvos-v3.0-{self.config.build_variant}.apk",
        }


# Global instance
APK_BRIDGE = AndroidAPKBridge()


def get_apk_build_status() -> Dict[str, Any]:
    """Get APK build status"""
    return APK_BRIDGE.get_build_status()


def generate_capacitor_config() -> Dict[str, Any]:
    """Generate Capacitor configuration"""
    return APK_BRIDGE.generate_capacitor_config()


def get_apk_info() -> Dict[str, Any]:
    """Get APK information"""
    return APK_BRIDGE.get_apk_info()


def simulate_apk_build() -> Dict[str, Any]:
    """Simulate APK build"""
    return APK_BRIDGE.simulate_build()
