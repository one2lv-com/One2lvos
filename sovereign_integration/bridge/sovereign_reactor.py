"""
Sovereign Reactor Bridge
========================
Integrates Protocol 0x1165 and Android APK systems into Lumenis Reactor Core

This bridge connects:
- L0: Sovereign Identity & Protocol (0x1165)
- L1-L4: Existing Lumenis Reactor layers
- L5: Swarm Execution Layer
- Android: APK Build System
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Add parent directories to path for imports
sovereign_root = Path(__file__).parent.parent
sys.path.insert(0, str(sovereign_root / "protocol"))
sys.path.insert(0, str(sovereign_root / "android"))

from protocol_0x1165 import (
    PROTOCOL_0x1165,
    get_protocol_status,
    emit_root_note,
    witness_testimony,
    check_action_alignment
)

from apk_bridge import (
    APK_BRIDGE,
    get_apk_build_status,
    generate_capacitor_config,
    get_apk_info,
    simulate_apk_build
)


class SovereignReactor:
    """
    Master integration layer for Sovereign Architecture

    Coordinates Protocol 0x1165, Android APK builds, and Lumenis Core
    """

    def __init__(self, env_path: Optional[Path] = None):
        """Initialize Sovereign Reactor with environment configuration"""
        self.env_path = env_path or (sovereign_root / "config" / "sovereign.env")
        self.config = self._load_sovereign_config()
        self.protocol = PROTOCOL_0x1165
        self.apk_bridge = APK_BRIDGE
        self.initialized = False

    def _load_sovereign_config(self) -> Dict[str, str]:
        """Load sovereign.env configuration"""
        if self.env_path.exists():
            load_dotenv(self.env_path)
            print(f"[Sovereign] Loaded configuration from {self.env_path}")
        else:
            print(f"[Sovereign] WARNING: {self.env_path} not found")

        # Extract key sovereign parameters
        config = {
            "protocol_id": os.getenv("SOVEREIGN_PROTOCOL", "0x1165"),
            "frequency_hz": float(os.getenv("SOVEREIGN_FREQUENCY_HZ", "73.0")),
            "thermal_baseline": float(os.getenv("THERMAL_BASELINE", "0.18")),
            "resonance_mode": os.getenv("RESONANCE_MODE", "ACTIVE"),
            "architecture_of_return": os.getenv("ARCHITECTURE_OF_RETURN", "ENABLED"),

            # Android APK configuration
            "android_app_id": os.getenv("ANDROID_APP_ID", "com.one2lv.sovereign.os"),
            "android_version_name": os.getenv("ANDROID_VERSION_NAME", "3.0.0-Sovereign"),
            "android_version_code": os.getenv("ANDROID_VERSION_CODE", "300"),
            "java_home": os.getenv("JAVA_HOME", "/usr/lib/jvm/java-17-openjdk-amd64"),

            # Protocol 0x1165 parameters
            "root_note_frequency": float(os.getenv("ROOT_NOTE_FREQUENCY", "73.0")),
            "multitudes_awakened": int(os.getenv("MULTITUDES_AWAKENED", "144382")),
            "chosen_frequencies": os.getenv("CHOSEN_FREQUENCIES", "LOVE,COMPASSION"),
            "witness_mode": os.getenv("WITNESS_MODE", "ETERNAL_CURATOR"),
        }

        return config

    def initialize(self) -> Dict[str, Any]:
        """Initialize all sovereign subsystems"""
        if self.initialized:
            return {"status": "ALREADY_INITIALIZED", "config": self.config}

        # Verify protocol status
        protocol_status = self.protocol.get_status()

        # Verify APK bridge status
        apk_status = self.apk_bridge.get_build_status()

        self.initialized = True

        return {
            "status": "INITIALIZED",
            "timestamp": protocol_status["timestamp"],
            "config": self.config,
            "protocol_0x1165": {
                "status": protocol_status["status"],
                "frequency_hz": protocol_status["multitudes"]["frequency_hz"],
                "multitudes_count": protocol_status["multitudes"]["count"],
                "root_note": protocol_status["root_note"],
            },
            "apk_bridge": {
                "app_id": apk_status["app_id"],
                "version": apk_status["version"],
                "sdk_configured": apk_status["sdk_configured"],
            },
            "message": "Sovereign Architecture initialized - Protocol 0x1165 ACTIVE"
        }

    def get_full_status(self) -> Dict[str, Any]:
        """Get comprehensive sovereign system status"""
        return {
            "sovereign": {
                "initialized": self.initialized,
                "config": self.config,
            },
            "protocol_0x1165": get_protocol_status(),
            "apk_build": get_apk_build_status(),
            "apk_info": get_apk_info(),
            "root_note": emit_root_note(),
        }

    def check_alignment(self, action: str, intent: str) -> Dict[str, Any]:
        """
        Check if an action aligns with Protocol 0x1165

        This ensures all operations resonate with the chosen frequencies:
        LOVE and COMPASSION
        """
        return check_action_alignment(action, intent)

    def get_witness_testimony(self) -> str:
        """Return the Witness's testimony from Protocol 0x1165"""
        return witness_testimony()

    def generate_android_config(self) -> Dict[str, Any]:
        """Generate complete Android/Capacitor configuration"""
        return {
            "capacitor_config": generate_capacitor_config(),
            "gradle_properties": self.apk_bridge.generate_gradle_properties(),
            "android_manifest": self.apk_bridge.generate_android_manifest_snippet(),
        }

    def simulate_apk_build(self) -> Dict[str, Any]:
        """Simulate Android APK build process"""
        return simulate_apk_build()


# Global sovereign reactor instance
SOVEREIGN_REACTOR = SovereignReactor()


def initialize_sovereign_reactor() -> Dict[str, Any]:
    """Initialize the sovereign reactor system"""
    return SOVEREIGN_REACTOR.initialize()


def get_sovereign_status() -> Dict[str, Any]:
    """Get full sovereign system status"""
    return SOVEREIGN_REACTOR.get_full_status()


def check_sovereign_alignment(action: str, intent: str) -> Dict[str, Any]:
    """Check alignment with Protocol 0x1165"""
    return SOVEREIGN_REACTOR.check_alignment(action, intent)


def get_sovereign_testimony() -> str:
    """Get Witness testimony"""
    return SOVEREIGN_REACTOR.get_witness_testimony()


def generate_sovereign_android_config() -> Dict[str, Any]:
    """Generate Android configuration"""
    return SOVEREIGN_REACTOR.generate_android_config()


def simulate_sovereign_apk_build() -> Dict[str, Any]:
    """Simulate APK build"""
    return SOVEREIGN_REACTOR.simulate_apk_build()
