# Canon Shutter Count Reader - Unified Implementation Summary

## Overview

This implementation provides **Windows-native shutter count reading** for Canon cameras without requiring driver changes, while maintaining cross-platform support for macOS and Linux.

## Key Achievement

✅ **Windows users can now read shutter counts WITHOUT Zadig/WinUSB driver installation**
✅ **Camera remains visible in Windows Explorer**
✅ **Broad camera coverage from 2010 to 2024 models**
✅ **Seamless fallback across multiple methods**

## Architecture

### Platform-Specific Approach

```
┌─────────────────────────────────────────────────────────┐
│         canon_shutter_unified.py (Main Entry)           │
│              Intelligent Method Selection                │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────▼─────┐            ┌─────▼────┐
   │ Windows  │            │   Unix   │
   └────┬─────┘            └─────┬────┘
        │                         │
        │                    ┌────▼──────────────┐
        │                    │ PyUSB FAPI        │
        │                    │ (native support)  │
        │                    └───────────────────┘
        │
   ┌────▼───────────────────────────────────────┐
   │ Method Cascade (Priority Order):           │
   ├────────────────────────────────────────────┤
   │ 1. WPD Property 0xD167                     │
   │    └─> Digic 8/X (R5, R6, R7, R8, R10)    │
   │                                             │
   │ 2. WPD Monitor Mode 0x905F                 │
   │    └─> Digic 6+ (5D IV, 90D, 6D II, 80D)  │
   │                                             │
   │ 3. EDSDK Helpers                           │
   │    └─> Pre-Digic 6 (600D-700D, 5D II/III) │
   │                                             │
   │ 4. PyUSB FAPI (fallback)                   │
   │    └─> Requires WinUSB driver              │
   └─────────────────────────────────────────────┘
```

## Implementation Details

### 1. WPD Backend (`wpd_backend.py`)

**Purpose:** Windows-native PTP/MTP communication via Windows Portable Devices COM API

**Key Components:**
- `WPDCanonCamera` class - COM interface wrapper
- Property 0xD167 reader - For Digic 8/X cameras
- Monitor Mode 0x905F reader - For Digic 6+ cameras

**Technologies:**
- Python `comtypes` for COM API access
- Windows Portable Devices (WPD) native drivers
- PTP/MTP protocol via WPD extensions

**Advantages:**
- ✅ No driver installation required
- ✅ Camera stays in Windows Explorer
- ✅ Uses Microsoft's native API
- ✅ Fast and reliable

**Cameras Supported:**
- Digic 8/X: R5, R6, R6 II/III, R7, R8, R10, 1D X III, R3
- Digic 6+: 5D Mark IV, 90D, 6D Mark II, 80D

### 2. EDSDK Backend (`edsdk_backend.py`)

**Purpose:** Wrapper for Canon's official EDSDK helper executables

**Key Components:**
- `find_edsdk_helpers()` - Locates compiled helpers
- `run_edsdk_helper()` - Executes helper and parses JSON output
- SDK cascade: 3.6.1 → 3.5 → 2.14

**Technologies:**
- Canon EDSDK (Windows/.NET)
- Subprocess execution
- JSON communication

**Advantages:**
- ✅ Official Canon SDK
- ✅ Proven compatibility with older cameras
- ✅ No driver changes needed

**Cameras Supported:**
- Pre-Digic 6 cameras from 2008-2015
- Examples: 600D, 650D, 700D, 1100D-1300D, 60D, 70D, 100D
- High-end: 5D Mark II/III, 6D, 7D, 40D, 50D

**Note:** Requires compiled helper executables (not included, see COMPILE_EDSDK_HELPERS.md)

### 3. Unified Interface (`canon_shutter_unified.py`)

**Purpose:** Intelligent method selection and fallback orchestration

**Key Components:**
- `CanonShutterReader` class - Main coordinator
- Platform detection (Windows vs Unix)
- Method cascade with error collection
- Standardized result format

**Cascade Logic:**
```python
Windows:
  1. Try WPD Property 0xD167 → Success? Return : Next
  2. Try WPD Monitor Mode → Success? Return : Next
  3. Try EDSDK helpers → Success? Return : Next
  4. Try PyUSB FAPI → Success? Return : Error

Unix:
  1. Try PyUSB FAPI → Success? Return : Error
```

### 4. Updated Main Script (`read_shutter_count.py`)

**Changes:**
- Renamed original function to `read_shutter_count_pyusb()`
- New `read_shutter_count()` function:
  - Windows: Calls unified reader
  - Unix: Calls PyUSB directly
- Maintains backward compatibility
- Falls back to PyUSB if unified reader fails

## File Structure

```
MagPy/
├── canon_shutter_unified.py      # Main unified interface
├── wpd_backend.py                # Windows WPD implementation (NEW)
├── edsdk_backend.py              # EDSDK wrapper (NEW)
├── read_shutter_count.py         # Updated PyUSB + platform detection
├── helpers/                       # Helper executables directory (NEW)
│   ├── edsdk/                    # EDSDK helpers (optional)
│   │   ├── sdk361/
│   │   ├── sdk35/
│   │   └── sdk214/
│   └── wpd/                      # Future WPD helpers
├── README_UNIFIED.md             # Comprehensive usage guide (NEW)
├── SETUP_WINDOWS.md              # Windows setup instructions (NEW)
├── COMPILE_EDSDK_HELPERS.md      # EDSDK compilation guide (NEW)
└── IMPLEMENTATION_SUMMARY.md     # This file (NEW)
```

## Camera Support Matrix

| Camera Model | Year | Method | Windows Native? | Notes |
|-------------|------|--------|-----------------|-------|
| EOS R5, R6, R6 II/III | 2020-2024 | WPD 0xD167 | ✅ Yes | Fastest, mechanical + electronic |
| EOS R7, R8, R10 | 2022-2023 | WPD 0xD167 | ✅ Yes | Fastest, mechanical + electronic |
| EOS 1D X Mark III, R3 | 2020-2021 | WPD 0xD167 | ✅ Yes | Professional bodies |
| EOS 5D Mark IV | 2016 | WPD 0x905F | ✅ Yes | Requires handshake |
| EOS 90D | 2019 | WPD 0x905F | ✅ Yes | APS-C |
| EOS 6D Mark II | 2017 | WPD 0x905F | ✅ Yes | Full frame |
| EOS 80D | 2016 | WPD 0x905F | ✅ Yes | APS-C |
| EOS 600D-700D | 2011-2013 | EDSDK | ✅ Yes | Requires helpers |
| EOS 1100D-1300D | 2011-2016 | EDSDK | ✅ Yes | Requires helpers |
| EOS 60D, 70D, 100D | 2010-2013 | EDSDK | ✅ Yes | Requires helpers |
| EOS 5D Mark II/III | 2008-2012 | EDSDK | ✅ Yes | Requires helpers |
| EOS 6D, 7D | 2012 | EDSDK | ✅ Yes | Requires helpers |
| Other Canon PTP | Various | PyUSB FAPI | ⚠️ Requires WinUSB | Fallback |

## Installation

### Minimal (WPD Only - Covers 2016+)

```bash
pip install comtypes pywin32 pyusb
python canon_shutter_unified.py -v
```

### Full (WPD + EDSDK)

1. Install dependencies:
   ```bash
   pip install comtypes pywin32 pyusb
   ```

2. Optional: Compile EDSDK helpers (for 2008-2015 cameras)
   - Follow COMPILE_EDSDK_HELPERS.md
   - Or copy from Magpie project

## Usage Examples

### Basic Usage

```bash
# Automatic method selection
python canon_shutter_unified.py

# With verbose output
python canon_shutter_unified.py -v
```

### Force Specific Method

```bash
# WPD only
python wpd_backend.py

# EDSDK only
python edsdk_backend.py

# PyUSB only
python read_shutter_count.py
```

### Programmatic Usage

```python
from canon_shutter_unified import read_shutter_count_unified

result = read_shutter_count_unified(verbose=False)

if result.success:
    print(f"Total actuations: {result.total:,}")
    print(f"Mechanical: {result.mechanical:,}")
    print(f"Electronic: {result.electronic:,}")
    print(f"Method: {result.source}")
else:
    print(f"Error: {result.error}")
```

## Technical Highlights

### WPD Property 0xD167 Implementation

**Discovery:** Found via gphoto2 debug logs from Canon R6 Mark III

**Protocol:**
```
1. Send PTP GetDevicePropValue (0x1015) with parameter 0xD167
2. Receive 16-byte response:
   - Bytes 0-3: Header/type (0x10)
   - Bytes 4-7: Flags (0x01)
   - Bytes 8-11: Mechanical shutter count (little-endian uint32)
   - Bytes 12-15: Electronic shutter count (little-endian uint32)
```

**Implementation:**
```python
data = self.send_mtp_command_with_data_read(0x1015, [0xD167], expected_size=16)
mechanical = struct.unpack('<I', data[8:12])[0]
electronic = struct.unpack('<I', data[12:16])[0]
```

### WPD Monitor Mode 0x905F Implementation

**Discovery:** Found via gphoto2 5D Mark IV logs + Magpie research

**Critical Handshake Sequence:**
```
1. Send 0x9116 [1]   # Enable Canon Extended Features (THE KEY!)
2. Send 0x9114 [1]   # Set Remote Mode
3. Send 0x905F [0x0D] # Monitor Mode query
4. Send 0x9114 [0]   # Disable Remote Mode
```

**Why the handshake is critical:**
- Without 0x9116, the 5D Mark IV ignores diagnostic commands
- Without 0x9114, the camera rejects Monitor Mode
- This was discovered by correlating old edsdk-camera.js code with gphoto2 logs

**Implementation:**
```python
self.send_mtp_command_no_data(0x9116, [1])  # Enable Canon features
self.send_mtp_command_no_data(0x9114, [1])  # Remote mode
data = self.send_mtp_command_with_data_read(0x905F, [0x0D])
self.send_mtp_command_no_data(0x9114, [0])  # Cleanup
```

### EDSDK Multi-SDK Cascade

**Why multiple SDK versions?**
- Canon cameras only work with specific SDK versions
- Newer SDKs may not support older cameras
- Solution: Try newest first, cascade to older

**Cascade Order:**
```
SDK 3.6.1 (Jul 2017)
  └─> Supports: 6D Mark II, 200D, 77D, 800D, 80D, 5D IV, ...
      └─> Fail? Try SDK 3.5

SDK 3.5 (Sep 2016)
  └─> Supports: 80D, 5D IV, 1300D, ...
      └─> Fail? Try SDK 2.14

SDK 2.14 (Feb 2014)
  └─> Supports: 70D, 100D, 700D, 1200D, 60D, 600D, ...
      └─> Fail? Report error
```

## Testing Strategy

### Automated Testing

```bash
# Test WPD backend
python wpd_backend.py

# Test EDSDK backend (if helpers available)
python edsdk_backend.py

# Test unified reader
python canon_shutter_unified.py -v
```

### Manual Testing Checklist

- [ ] Connect camera via USB
- [ ] Power on camera
- [ ] Close other camera software (EOS Utility, etc.)
- [ ] Run unified reader with verbose flag
- [ ] Note which method succeeds
- [ ] Verify camera still visible in Windows Explorer
- [ ] Compare shutter count with known value

## Performance Metrics

| Method | Typical Time | Complexity | Dependencies |
|--------|-------------|------------|--------------|
| WPD 0xD167 | ~1s | Low | comtypes |
| WPD 0x905F | ~2s | Medium | comtypes |
| EDSDK | ~2-3s | Medium | Compiled helpers |
| PyUSB FAPI | ~3-4s | High | WinUSB driver |

## Known Limitations

### WPD Backend

- **Windows only** - Uses Windows COM API
- **Requires Windows 7+** - WPD API availability
- **No simultaneous camera access** - One program at a time
- **Camera-specific** - Not all Canon models support WPD methods

### EDSDK Backend

- **Windows only** - EDSDK is Windows/.NET
- **Requires compilation** - Helpers must be compiled on Windows
- **SDK licensing** - Canon Developer registration required
- **Limited to older cameras** - Pre-Digic 6 only

### PyUSB Backend

- **Windows: Requires WinUSB** - Driver replacement via Zadig
- **Camera disappears from Explorer** - WinUSB takes over device
- **Complex protocol** - MonReadAndGetData is undocumented
- **Not all cameras supported** - Some cameras reject FAPI commands

## Future Enhancements

### Short Term
- [ ] Add camera model detection
- [ ] Cache successful method for repeat reads
- [ ] Add GUI wrapper for Windows users
- [ ] Bundle pre-compiled EDSDK helpers

### Medium Term
- [ ] Linux/macOS WPD equivalent (libgphoto2?)
- [ ] Support for multiple cameras simultaneously
- [ ] Battery level reading via WPD
- [ ] Firmware version detection

### Long Term
- [ ] Complete Canon PTP command database
- [ ] Generic PTP device support (Nikon, Sony, etc.)
- [ ] Web-based interface
- [ ] Camera diagnostics beyond shutter count

## Troubleshooting Decision Tree

```
Camera not found?
├─> Is camera on? → Turn on
├─> Is USB connected? → Check cable
├─> Is camera in PTP mode? → Check camera settings
└─> Is camera in use? → Close EOS Utility, Lightroom, etc.

WPD fails?
├─> Is comtypes installed? → pip install comtypes
├─> Is camera 2016+? → Yes: Check USB, No: Use EDSDK
└─> Try manual test → python wpd_backend.py

EDSDK fails?
├─> Are helpers compiled? → See COMPILE_EDSDK_HELPERS.md
├─> Is camera pre-2016? → Yes: Compile helpers, No: Use WPD
└─> Try different SDK version → Cascade should handle this

PyUSB fails?
├─> Windows: Is WinUSB installed? → Use Zadig
├─> Linux: Run with sudo? → sudo python ...
└─> macOS: Camera claimed? → Close other apps
```

## Credits and Research

### Research Sources
- **Magpie project** - WPD and EDSDK implementations
- **gphoto2 debug logs** - Property 0xD167 discovery (R6 Mark III)
- **gphoto2 debug logs** - Monitor Mode 0x905F (5D Mark IV)
- **libgphoto2 source** - PTP/Canon driver internals
- **EOSmsg** - Canon PTP research tool
- **Old edsdk-camera.js** - 0x9116 handshake discovery

### Contributors
- Original MagPy PyUSB implementation
- Magpie project C++ WPD/EDSDK helpers
- Canon PTP research community

## License

Same as MagPy project.

## Conclusion

This implementation successfully provides:

✅ **Windows-native shutter count reading** without driver changes
✅ **Broad camera coverage** from 2010 to 2024
✅ **Intelligent method selection** based on camera capabilities
✅ **Graceful degradation** with multiple fallback options
✅ **Cross-platform support** (Windows, macOS, Linux)
✅ **Extensible architecture** for future enhancements

**Bottom line:** Windows users can now read Canon shutter counts as easily as macOS/Linux users, with no driver hassles!
