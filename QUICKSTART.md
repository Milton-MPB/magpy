# Quick Start Guide - Canon Shutter Count Reader

## TL;DR - Just Want to Read Shutter Count?

### Windows Users (2016+ Cameras)

```bash
# Install dependencies
pip install comtypes pywin32 pyusb

# Run (camera must be connected and on)
python canon_shutter_unified.py
```

**That's it!** No driver changes, camera stays in Windows Explorer.

### Windows Users (2010-2015 Cameras)

You'll need EDSDK helpers. See [COMPILE_EDSDK_HELPERS.md](COMPILE_EDSDK_HELPERS.md) or use the existing PyUSB method (requires Zadig).

### macOS/Linux Users

```bash
# Install dependencies
pip install pyusb

# Run
python read_shutter_count.py

# Linux: May need sudo
sudo python read_shutter_count.py
```

## What Camera Do I Have?

### 2020-2024 Cameras (Digic 8/X)
**Models:** R5, R6, R6 Mark II/III, R7, R8, R10, 1D X Mark III, R3
**Method:** WPD Property 0xD167 ✅ Native Windows support
**Install:** `pip install comtypes pywin32 pyusb`

### 2016-2019 Cameras (Digic 6+)
**Models:** 5D Mark IV, 90D, 6D Mark II, 80D
**Method:** WPD Monitor Mode 0x905F ✅ Native Windows support
**Install:** `pip install comtypes pywin32 pyusb`

### 2010-2015 Cameras (Pre-Digic 6)
**Models:** 600D-700D, 1100D-1300D, 60D, 70D, 100D, 5D Mark II/III, 6D, 7D
**Method:** EDSDK (requires compilation) or PyUSB (requires Zadig)
**See:** [COMPILE_EDSDK_HELPERS.md](COMPILE_EDSDK_HELPERS.md)

## Common Issues

### "No module named 'comtypes'" (Windows)

```bash
pip install comtypes pywin32
```

### "No Canon camera found"

- Check: Camera is on
- Check: USB cable is connected
- Check: Camera is not in use (close EOS Utility, Lightroom, etc.)
- Try: Different USB port

### "WinUSB driver required" (Windows)

This means you have an older camera. Either:
- **Compile EDSDK helpers** (recommended) - See [COMPILE_EDSDK_HELPERS.md](COMPILE_EDSDK_HELPERS.md)
- **Install WinUSB via Zadig** (camera will disappear from Explorer)

### Permission Denied (Linux)

```bash
# Option 1: Run with sudo
sudo python canon_shutter_unified.py

# Option 2: Configure udev rules (permanent fix)
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="04a9", MODE="0666"' | sudo tee /etc/udev/rules.d/50-canon.rules
sudo udevadm control --reload-rules
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

## Full Documentation

- **Complete guide:** [README_UNIFIED.md](README_UNIFIED.md)
- **Windows setup:** [SETUP_WINDOWS.md](SETUP_WINDOWS.md)
- **Compile EDSDK helpers:** [COMPILE_EDSDK_HELPERS.md](COMPILE_EDSDK_HELPERS.md)
- **Implementation details:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

## One-Line Test

```bash
# Windows
python -c "from canon_shutter_unified import read_shutter_count_unified; r=read_shutter_count_unified(); print(f'Shutter: {r.total:,}' if r.success else f'Error: {r.error}')"

# macOS/Linux
python -c "from read_shutter_count import read_shutter_count; r=read_shutter_count(); print(f'Shutter: {r[\"total\"]:,}' if r else 'Error')"
```

## Help!

1. Run with verbose flag: `python canon_shutter_unified.py -v`
2. Check camera compatibility above
3. Read error messages carefully
4. See full documentation links above
