# MagPy - Canon Camera Shutter Count Reader

Cross-platform Canon camera shutter count reader with **Windows-native support** (no driver changes required).

## 🎯 Quick Start

### Windows (2016+ Cameras)

```bash
pip install comtypes pywin32 pyusb
python canon_shutter_unified.py
```

**No driver changes needed!** Camera stays visible in Windows Explorer.

### macOS/Linux

```bash
pip install pyusb
python read_shutter_count.py
```

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 2 minutes
- **[README_UNIFIED.md](README_UNIFIED.md)** - Complete feature guide
- **[SETUP_WINDOWS.md](SETUP_WINDOWS.md)** - Windows installation guide
- **[COMPILE_EDSDK_HELPERS.md](COMPILE_EDSDK_HELPERS.md)** - EDSDK compilation (older cameras)
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Technical deep dive
- **[TESTING_NOTES.md](TESTING_NOTES.md)** - Testing guide and status

## ✨ Features

### Windows: Native Support (No Driver Changes!)

✅ **WPD Backend** - Works with Windows native drivers
✅ **EDSDK Backend** - Official Canon SDK support
✅ **Camera stays in Explorer** - No device disappearance
✅ **Broad coverage** - 2010-2024 camera models

### Cross-Platform

✅ **macOS** - Native USB access, no drivers needed
✅ **Linux** - Works with standard USB permissions
✅ **Fallback** - PyUSB available on all platforms

## 🎥 Supported Cameras

| Generation | Years | Windows Method | Examples |
|-----------|-------|---------------|----------|
| **Digic 8/X** | 2020+ | WPD Property 0xD167 | R5, R6, R6 II/III, R7, R8, R10, 1D X III, R3 |
| **Digic 6+** | 2016-2019 | WPD Monitor Mode 0x905F | 5D Mark IV, 90D, 6D Mark II, 80D |
| **Pre-Digic 6** | 2010-2015 | EDSDK (requires compilation) | 600D-700D, 1100D-1300D, 5D II/III, 6D, 7D |

See [README_UNIFIED.md](README_UNIFIED.md) for complete compatibility list.

## 🏗️ Architecture

### Method Cascade (Windows)

```
1. Try WPD Property 0xD167 → Digic 8/X cameras
2. Try WPD Monitor Mode 0x905F → Digic 6+ cameras
3. Try EDSDK helpers → Pre-Digic 6 cameras
4. Fall back to PyUSB → Requires WinUSB driver
```

### Project Structure

```
MagPy/
├── canon_shutter_unified.py    # Main unified interface ⭐
├── wpd_backend.py              # Windows WPD implementation
├── edsdk_backend.py            # EDSDK wrapper
├── read_shutter_count.py       # Original PyUSB implementation
├── helpers/                     # Helper executables
│   └── edsdk/                  # EDSDK helpers (optional)
└── docs/                       # All documentation files
```

## 🚀 Usage

### Basic Usage

```bash
# Automatic method selection
python canon_shutter_unified.py

# With verbose output (recommended)
python canon_shutter_unified.py -v
```

### Force Specific Method

```bash
# Windows WPD only (2016+ cameras)
python wpd_backend.py

# EDSDK only (2010-2015 cameras, requires helpers)
python edsdk_backend.py

# PyUSB only (all platforms, requires WinUSB on Windows)
python read_shutter_count.py
```

### Programmatic Usage

```python
from canon_shutter_unified import read_shutter_count_unified

result = read_shutter_count_unified(verbose=False)

if result.success:
    print(f"Total: {result.total:,}")
    print(f"Mechanical: {result.mechanical:,}")
    print(f"Electronic: {result.electronic:,}")
    print(f"Method: {result.source}")
else:
    print(f"Error: {result.error}")
```

## 📦 Installation

### Python Dependencies

```bash
# Windows (full support)
pip install comtypes pywin32 pyusb

# macOS/Linux
pip install pyusb
```

### Optional: EDSDK Helpers (for 2010-2015 cameras)

See [COMPILE_EDSDK_HELPERS.md](COMPILE_EDSDK_HELPERS.md) for compilation instructions.

## 🔧 Troubleshooting

### "No Canon camera found"

- ✅ Camera is powered on
- ✅ USB cable is connected
- ✅ Camera is not in use (close EOS Utility, Lightroom, etc.)
- ✅ Try different USB port

### "comtypes not found" (Windows)

```bash
pip install comtypes pywin32
```

### "Permission denied" (Linux)

```bash
# Run with sudo
sudo python canon_shutter_unified.py

# Or configure udev rules
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="04a9", MODE="0666"' | sudo tee /etc/udev/rules.d/50-canon.rules
```

See [SETUP_WINDOWS.md](SETUP_WINDOWS.md) for complete troubleshooting guide.

## 🎯 Example Output

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

## 🏆 Implementation Status

✅ **Core implementation complete**
✅ **All backends implemented** (WPD, EDSDK, PyUSB)
✅ **Unified interface complete**
✅ **Documentation complete**
⚠️ **Hardware testing pending** (see [TESTING_NOTES.md](TESTING_NOTES.md))

The implementation is based on proven code from the [Magpie project](https://github.com) and extensive PTP protocol research, but needs validation on actual hardware.

## 🔬 Technical Details

### WPD Backend
- Uses Windows Portable Devices COM API
- Property 0xD167 for Digic 8/X cameras
- Monitor Mode 0x905F with handshake for Digic 6+
- Native Windows drivers (no driver changes)

### EDSDK Backend
- Wraps Canon's official EDSDK
- Supports SDK 3.6.1, 3.5, 2.14
- Memory scraping via EdsSendCommandEx
- Requires compiled helper executables

### PyUSB Backend
- Raw USB PTP communication
- Uses Canon's undocumented MonReadAndGetData protocol
- Reads camera RAM at address 0x1015
- Cross-platform (Windows/macOS/Linux)

See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for complete technical details.

## 📝 Credits

- **WPD research:** Magpie project (wpd-ptp-helper)
- **EDSDK helpers:** Magpie project (shutter-helper-sdk361)
- **PyUSB FAPI:** Original MagPy implementation
- **Property 0xD167:** Discovered via gphoto2 R6 Mark III logs
- **Monitor Mode 0x905F:** Discovered via gphoto2 5D Mark IV logs

## ⚖️ License

Same as MagPy project.

## ⚠️ Safety Warning

- **WPD and EDSDK methods are safe** - Use official/documented APIs
- **PyUSB FAPI method is experimental** - Uses undocumented factory protocol
- **Use at your own risk**

## 🤝 Contributing

Contributions welcome! Especially:

1. **Hardware testing** - Test with different camera models
2. **Bug reports** - Report compatibility issues
3. **Documentation** - Improve guides and examples
4. **Code improvements** - Optimize or fix bugs

See [TESTING_NOTES.md](TESTING_NOTES.md) for testing procedures.

## 📞 Support

1. Check [QUICKSTART.md](QUICKSTART.md) for common issues
2. Read [README_UNIFIED.md](README_UNIFIED.md) for detailed troubleshooting
3. Run with `-v` flag for verbose output
4. File an issue with camera model and error messages

## 🗺️ Roadmap

### Phase 1 (Complete)
- [x] WPD backend implementation
- [x] EDSDK backend wrapper
- [x] Unified interface
- [x] Comprehensive documentation

### Phase 2 (Pending)
- [ ] Hardware testing on Windows
- [ ] Bug fixes based on testing
- [ ] Optimize method priority
- [ ] Add camera model database

### Phase 3 (Future)
- [ ] GUI for Windows users
- [ ] Standalone executable (no Python needed)
- [ ] Support for additional camera brands (Nikon, Sony)
- [ ] Additional diagnostics (battery, firmware, etc.)

---

**Ready to read your camera's shutter count?** → Start with [QUICKSTART.md](QUICKSTART.md)
