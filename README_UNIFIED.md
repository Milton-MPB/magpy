# Canon Shutter Count Reader - Unified Multi-Method Approach

This project provides **Windows-native shutter count reading** for Canon cameras without requiring driver changes, alongside cross-platform support for macOS and Linux.

## Features

### Windows: Native Support (No Driver Changes!)

✅ **Works with Windows native drivers** - No Zadig, no WinUSB installation required
✅ **Camera stays visible in Windows Explorer** - No device disappearance
✅ **Multi-method cascade** - Automatically tries the best method for your camera
✅ **Broad camera coverage** - From 2010 to 2024 models

### macOS/Linux: Native USB Access

✅ **Works out of the box** - No driver changes needed
✅ **Uses PyUSB** - Standard USB library access

## Supported Cameras

### Method 1: WPD Property 0xD167 (Digic 8/X, 2020+)
✅ Canon EOS R5, R6, R6 Mark II, R6 Mark III
✅ Canon EOS R7, R8, R10
✅ Canon EOS 1D X Mark III
✅ Canon EOS R3

**How it works:** Reads native Canon property via Windows Portable Devices API
**Advantages:** Fastest, returns mechanical + electronic counts separately
**Windows only:** Yes (uses WPD COM API)

### Method 2: WPD Monitor Mode 0x905F (Digic 6+, 2016-2019)
✅ Canon EOS 5D Mark IV
✅ Canon EOS 90D
✅ Canon EOS 6D Mark II
✅ Canon EOS 80D

**How it works:** Uses Canon's diagnostic Monitor Mode via WPD
**Advantages:** Native Windows, no driver changes
**Windows only:** Yes (uses WPD COM API)

### Method 3: EDSDK (Pre-Digic 6, 2010-2015)
✅ Canon EOS 600D, 650D, 700D, 1100D, 1200D, 1300D
✅ Canon EOS 60D, 70D, 100D
✅ Canon EOS 5D Mark II, 5D Mark III
✅ Canon EOS 6D, 7D
✅ Canon EOS 40D, 50D, 450D, 500D, 550D

**How it works:** Uses Canon's official EDSDK with memory scraping
**Advantages:** Official SDK, proven compatibility
**Windows only:** Yes (EDSDK is Windows/.NET only)
**Note:** Requires compiled helper executables (not included)

### Method 4: PyUSB FAPI (Fallback, All platforms)
✅ Canon EOS 6D Mark II (tested)
✅ Many other Canon cameras with FAPI support

**How it works:** Raw USB PTP using undocumented MonReadAndGetData protocol
**Advantages:** Cross-platform (Windows/macOS/Linux)
**Disadvantages on Windows:** Requires WinUSB driver via Zadig (camera disappears from Explorer)

## Installation

### Python Requirements

```bash
# Core requirement (all platforms)
pip install pyusb

# Windows only (for WPD support)
pip install comtypes pywin32
```

### Windows: WPD Support (Recommended)

**No additional setup required!** The WPD backend uses native Windows drivers.

Just run:
```bash
python canon_shutter_unified.py
```

The script will automatically:
1. Try WPD Property 0xD167 (newest cameras)
2. Try WPD Monitor Mode 0x905F (Digic 6+ cameras)
3. Try EDSDK helpers if available (older cameras)
4. Fall back to PyUSB if needed (requires WinUSB)

### Windows: EDSDK Support (Optional, for older cameras)

**For cameras from 2010-2015 (pre-Digic 6):**

1. Copy EDSDK helpers from Magpie project:
   ```bash
   # From Magpie/helpers/ to MagPy/helpers/edsdk/
   # You need: shutter-helper-sdk361.exe, shutter-helper-sdk35.exe, etc.
   # Plus their DLLs: EDSDK.dll, EdsImage.dll, Mlib.dll, Ucs32P.dll
   ```

2. Or compile them yourself:
   ```bash
   cd helpers/edsdk
   # Follow build instructions in Magpie/helpers/BUILD_INSTRUCTIONS.md
   ```

**Note:** EDSDK support is optional. WPD already covers most cameras from 2016+.

### macOS/Linux: USB Access

**No additional setup required!** Just install PyUSB:
```bash
pip install pyusb
```

On Linux, you may need to run with `sudo` or configure udev rules for camera access.

## Usage

### Unified Reader (Recommended)

**Tries all methods automatically:**
```bash
python canon_shutter_unified.py
```

**With verbose output:**
```bash
python canon_shutter_unified.py -v
```

### Direct Methods

**WPD only (Windows):**
```bash
python wpd_backend.py
```

**EDSDK only (Windows, older cameras):**
```bash
python edsdk_backend.py
```

**PyUSB only (all platforms):**
```bash
python read_shutter_count.py
```

## Method Selection Logic

The unified reader automatically selects the best method:

```
Windows:
  1. Try WPD Property 0xD167
     ├─ Success → Return result (Digic 8/X cameras)
     └─ Fail → Try next method

  2. Try WPD Monitor Mode 0x905F
     ├─ Success → Return result (Digic 6+ cameras)
     └─ Fail → Try next method

  3. Try EDSDK helpers
     ├─ Success → Return result (pre-Digic 6 cameras)
     └─ Fail → Try next method

  4. Try PyUSB FAPI
     ├─ Success → Return result (fallback)
     └─ Fail → Report error

macOS/Linux:
  1. Try PyUSB FAPI
     ├─ Success → Return result
     └─ Fail → Report error
```

## Example Output

```
Canon Camera Shutter Count Reader (Unified)
============================================================
[CanonShutterReader] Trying WPD Property 0xD167 (Digic 8/X cameras)...
[CanonShutterReader] ✓ Success via WPD Property 0xD167

============================================================
SHUTTER COUNT
============================================================
Camera Model: Canon EOS R6
Serial Number: 123456789
Mechanical actuations: 15,234
Electronic actuations: 8,451
TOTAL ACTUATIONS:      23,685
Method used: WPD Property 0xD167
============================================================

✓ Success!
```

## Troubleshooting

### Windows: "No Canon camera found via WPD"

**Check:**
- Camera is connected via USB
- Camera is powered on
- Camera is not being used by another application (EOS Utility, etc.)
- Try a different USB cable or port

**Why WPD might fail:**
- Very old cameras (pre-2016) may not support WPD methods → Use EDSDK or PyUSB
- Camera is in mass storage mode → Switch to PTP/MTP mode

### Windows: "comtypes not found"

**Solution:**
```bash
pip install comtypes pywin32
```

### Windows: "All EDSDK helpers failed"

**This is normal if:**
- You don't have EDSDK helpers compiled
- Your camera is newer than 2015 (use WPD instead)

**To fix:**
- For older cameras: Compile EDSDK helpers (see Installation section)
- For newer cameras: WPD should work (check WPD error messages)

### macOS/Linux: "Permission denied"

**Solutions:**
```bash
# Option 1: Run with sudo
sudo python canon_shutter_unified.py

# Option 2: Configure udev rules (Linux)
# Create /etc/udev/rules.d/50-canon.rules:
# SUBSYSTEM=="usb", ATTR{idVendor}=="04a9", MODE="0666"
```

### "PyUSB: WinUSB driver required" (Windows)

**This means:**
- WPD and EDSDK failed (camera too new for EDSDK, doesn't support WPD)
- PyUSB fallback activated but needs WinUSB driver

**To install WinUSB (not recommended, breaks Windows Explorer access):**
1. Download Zadig: https://zadig.akeo.ie/
2. Run as Administrator
3. Options → List All Devices
4. Select "Canon Digital Camera"
5. Replace driver with WinUSB
6. Reconnect camera

**Warning:** Camera will disappear from Windows Explorer!

## Technical Details

### WPD Implementation

**What is WPD?**
Windows Portable Devices (WPD) is Microsoft's native API for communicating with cameras, phones, and media players. It's built into Windows and uses the standard PTP/MTP drivers.

**Advantages:**
- ✅ No driver installation required
- ✅ Camera remains accessible to Windows Explorer
- ✅ Uses native Windows COM API
- ✅ Supports modern Canon cameras

**Property 0xD167 Method:**
```python
# Send PTP GetDevicePropValue (0x1015) for property 0xD167
# Response: 16 bytes
#   Bytes 8-11: Mechanical shutter count
#   Bytes 12-15: Electronic shutter count
```

**Monitor Mode 0x905F Method:**
```python
# Handshake sequence (critical for 5D Mark IV):
1. Send 0x9116 [1]  # Enable Canon Extended Features
2. Send 0x9114 [1]  # Set Remote Mode
3. Send 0x905F [0x0D]  # Monitor Mode query
4. Send 0x9114 [0]  # Disable Remote Mode

# Response: Variable-length buffer with shutter count
```

### EDSDK Implementation

Uses Canon's official EDSDK with undocumented commands:

**Method 1:** Property 0xD167 via EDSDK (Digic 8/X)
**Method 2:** Property 0x0022 (standard fallback)
**Method 3:** EdsSendCommandEx(0x9153) memory scraping (older cameras)

**Cascade:** Tries SDK 3.6.1 → SDK 3.5 → SDK 2.14

### PyUSB Implementation

Uses raw PTP/USB with Canon's undocumented FAPI protocol:

**MonReadAndGetData:**
```python
# Read camera RAM at address 0x1015
# Response: 10 bytes
#   Bytes 0-3: Mechanical shutter count
#   Bytes 6-9: Electronic shutter count
```

**Requirement:** On Windows, requires WinUSB driver replacement via Zadig.

## Project Structure

```
MagPy/
├── canon_shutter_unified.py    # Main unified interface
├── wpd_backend.py              # Windows WPD implementation
├── edsdk_backend.py            # Windows EDSDK wrapper
├── read_shutter_count.py       # PyUSB implementation
├── helpers/
│   ├── edsdk/                  # EDSDK helpers (optional)
│   │   ├── shutter-helper-sdk361.exe
│   │   ├── shutter-helper-sdk35.exe
│   │   ├── EDSDK.dll
│   │   └── ...
│   └── wpd/                    # WPD helpers (future)
└── README_UNIFIED.md           # This file
```

## Credits

- **WPD research:** Magpie project (wpd-ptp-helper)
- **EDSDK helpers:** Magpie project (shutter-helper-sdk361)
- **PyUSB FAPI:** Original MagPy implementation
- **Property 0xD167:** Discovered via gphoto2 R6 Mark III logs
- **Monitor Mode 0x905F:** Discovered via gphoto2 5D Mark IV logs

## License

Same as MagPy project.

## Safety Warning

**EDSDK and WPD methods are safe** - they use official or documented APIs.

**PyUSB FAPI method uses an undocumented factory debug protocol.** Use at your own risk.

## Support

For issues or questions:
1. Check camera compatibility list above
2. Run with `-v` flag for verbose output
3. Try each method individually to identify which fails
4. File an issue with camera model and error messages
