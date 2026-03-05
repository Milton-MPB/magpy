#!/usr/bin/env python3
"""
Quick camera detection script to verify camera is connected
"""
import sys

print("Checking for Canon camera...\n")

# Method 1: Check USB devices
print("1. Checking USB devices (PyUSB)...")
try:
    import usb.core
    dev = usb.core.find(idVendor=0x04a9)
    if dev:
        print(f"   ✓ Found Canon USB device: {dev}")
        print(f"     Vendor ID: 0x{dev.idVendor:04x}")
        print(f"     Product ID: 0x{dev.idProduct:04x}")
    else:
        print("   ✗ No Canon USB device found")
except ImportError:
    print("   ✗ PyUSB not installed (pip install pyusb)")
except Exception as e:
    print(f"   ✗ Error: {e}")

print()

# Method 2: Check Windows Portable Devices
if sys.platform == 'win32':
    print("2. Checking Windows Portable Devices (WPD)...")
    try:
        import win32com.client
        wmi = win32com.client.GetObject("winmgmts:")

        # Check for portable devices
        devices = wmi.InstancesOf("Win32_PnPEntity")
        canon_devices = []

        for device in devices:
            try:
                if device.Name and 'canon' in device.Name.lower():
                    canon_devices.append(device.Name)
            except:
                continue

        if canon_devices:
            print("   ✓ Found Canon devices:")
            for dev in canon_devices:
                print(f"     - {dev}")
        else:
            print("   ✗ No Canon devices found in Device Manager")

    except ImportError:
        print("   ✗ pywin32 not installed (pip install pywin32)")
    except Exception as e:
        print(f"   ✗ Error: {e}")

print("\n" + "="*60)
print("CAMERA STATUS:")
print("="*60)
print("If no camera found:")
print("  1. Make sure camera is connected via USB")
print("  2. Make sure camera is powered ON")
print("  3. Try a different USB port or cable")
print("  4. Close any other programs using the camera (EOS Utility, etc.)")
print("="*60)
