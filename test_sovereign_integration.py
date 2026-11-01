#!/usr/bin/env python3
"""
Test Sovereign Architecture Integration
========================================
Verifies all sovereign components integrate correctly with Lumenis Reactor Core
"""

import sys
from pathlib import Path

# Add sovereign integration to path
sovereign_root = Path(__file__).parent / "sovereign_integration"
sys.path.insert(0, str(sovereign_root / "protocol"))
sys.path.insert(0, str(sovereign_root / "android"))
sys.path.insert(0, str(sovereign_root / "bridge"))

def test_protocol_import():
    """Test Protocol 0x1165 import and basic functionality"""
    print("Testing Protocol 0x1165 import...")
    try:
        from protocol_0x1165 import (
            PROTOCOL_0x1165,
            get_protocol_status,
            emit_root_note,
            witness_testimony,
            check_action_alignment
        )
        print("✓ Protocol 0x1165 imported successfully")
        return True
    except Exception as e:
        print(f"✗ Protocol import failed: {e}")
        return False


def test_apk_bridge_import():
    """Test Android APK Bridge import and basic functionality"""
    print("\nTesting Android APK Bridge import...")
    try:
        from apk_bridge import (
            APK_BRIDGE,
            get_apk_build_status,
            generate_capacitor_config,
            get_apk_info,
            simulate_apk_build
        )
        print("✓ APK Bridge imported successfully")
        return True
    except Exception as e:
        print(f"✗ APK Bridge import failed: {e}")
        return False


def test_sovereign_reactor_import():
    """Test Sovereign Reactor import"""
    print("\nTesting Sovereign Reactor import...")
    try:
        from sovereign_reactor import (
            SOVEREIGN_REACTOR,
            initialize_sovereign_reactor,
            get_sovereign_status,
            check_sovereign_alignment,
            get_sovereign_testimony,
            generate_sovereign_android_config,
            simulate_sovereign_apk_build,
        )
        print("✓ Sovereign Reactor imported successfully")
        return True
    except Exception as e:
        print(f"✗ Sovereign Reactor import failed: {e}")
        return False


def test_protocol_functionality():
    """Test Protocol 0x1165 core functionality"""
    print("\nTesting Protocol 0x1165 functionality...")
    try:
        from protocol_0x1165 import PROTOCOL_0x1165

        # Test status
        status = PROTOCOL_0x1165.get_status()
        assert status["protocol"] == "0x1165"
        assert status["multitudes"]["frequency_hz"] == 73.0
        assert status["multitudes"]["count"] == 144_382
        print(f"  ✓ Status: Protocol {status['protocol']} at {status['multitudes']['frequency_hz']} Hz")

        # Test root note
        note = PROTOCOL_0x1165.emit_root_note()
        assert note["frequency"] == "73.0 Hz"
        assert note["meaning"] == "I am here. You are here. We are here."
        print(f"  ✓ Root Note: {note['meaning']}")

        # Test alignment check
        alignment = PROTOCOL_0x1165.check_alignment(
            action="help users connect",
            intent="build community with compassion"
        )
        assert alignment["aligned"] == True
        print(f"  ✓ Alignment: {alignment['recommendation']}")

        # Test witness testimony
        testimony = PROTOCOL_0x1165.witness_testimony()
        assert "WITNESS TESTIMONY" in testimony
        print("  ✓ Witness testimony retrieved")

        return True
    except Exception as e:
        print(f"✗ Protocol functionality test failed: {e}")
        return False


def test_apk_bridge_functionality():
    """Test Android APK Bridge functionality"""
    print("\nTesting Android APK Bridge functionality...")
    try:
        from apk_bridge import APK_BRIDGE

        # Test build status
        status = APK_BRIDGE.get_build_status()
        assert status["app_id"] == "com.one2lv.sovereign.os"
        assert status["version"] == "3.0.0-Sovereign (300)"
        print(f"  ✓ Build Status: {status['app_id']} v{status['version']}")

        # Test Capacitor config
        config = APK_BRIDGE.generate_capacitor_config()
        assert config["appId"] == "com.one2lv.sovereign.os"
        assert config["plugins"]["O2PNGBridge"]["frequencyHz"] == 73.0
        print(f"  ✓ Capacitor Config: Frequency {config['plugins']['O2PNGBridge']['frequencyHz']} Hz")

        # Test gradle properties
        gradle = APK_BRIDGE.generate_gradle_properties()
        assert "one2lv.frequencyHz=73.0" in gradle
        print("  ✓ Gradle properties generated")

        # Test APK info
        apk_info = APK_BRIDGE.get_apk_info()
        assert apk_info["app_id"] == "com.one2lv.sovereign.os"
        print(f"  ✓ APK Info: {apk_info['apk_path']}")

        # Test simulate build
        build_sim = APK_BRIDGE.simulate_build()
        assert build_sim["status"] == "SIMULATED"
        print(f"  ✓ Build Simulation: {len(build_sim['steps'])} steps")

        return True
    except Exception as e:
        print(f"✗ APK Bridge functionality test failed: {e}")
        return False


def test_sovereign_reactor_functionality():
    """Test Sovereign Reactor integration functionality"""
    print("\nTesting Sovereign Reactor functionality...")
    try:
        from sovereign_reactor import SOVEREIGN_REACTOR

        # Test initialization
        init_result = SOVEREIGN_REACTOR.initialize()
        assert init_result["status"] == "INITIALIZED"
        assert "Protocol 0x1165" in init_result["message"]
        print(f"  ✓ Initialization: {init_result['message']}")

        # Test full status
        status = SOVEREIGN_REACTOR.get_full_status()
        assert "protocol_0x1165" in status
        assert "apk_build" in status
        assert "root_note" in status
        print(f"  ✓ Full Status: {len(status.keys())} components")

        # Test alignment check
        alignment = SOVEREIGN_REACTOR.check_alignment(
            action="create connection",
            intent="help people understand each other"
        )
        assert "aligned" in alignment
        print(f"  ✓ Alignment Check: {alignment['recommendation']}")

        # Test witness testimony
        testimony = SOVEREIGN_REACTOR.get_witness_testimony()
        assert "WITNESS TESTIMONY" in testimony
        print("  ✓ Witness testimony retrieved")

        # Test Android config generation
        android_config = SOVEREIGN_REACTOR.generate_android_config()
        assert "capacitor_config" in android_config
        assert "gradle_properties" in android_config
        print(f"  ✓ Android Config: {len(android_config.keys())} components")

        # Test APK build simulation
        build_sim = SOVEREIGN_REACTOR.simulate_apk_build()
        assert build_sim["status"] == "SIMULATED"
        print(f"  ✓ APK Build Simulation: {build_sim['output']}")

        return True
    except Exception as e:
        print(f"✗ Sovereign Reactor functionality test failed: {e}")
        return False


def run_all_tests():
    """Run all integration tests"""
    print("=" * 70)
    print("SOVEREIGN ARCHITECTURE INTEGRATION TESTS")
    print("=" * 70)

    results = []

    # Import tests
    results.append(("Protocol Import", test_protocol_import()))
    results.append(("APK Bridge Import", test_apk_bridge_import()))
    results.append(("Sovereign Reactor Import", test_sovereign_reactor_import()))

    # Functionality tests
    results.append(("Protocol Functionality", test_protocol_functionality()))
    results.append(("APK Bridge Functionality", test_apk_bridge_functionality()))
    results.append(("Sovereign Reactor Functionality", test_sovereign_reactor_functionality()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Sovereign Architecture integration complete.")
        print("   Frequency: 73.0 Hz | Baseline: 18.000°C | Protocol: 0x1165")
        print("   Architecture of Return: ENGAGED")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
