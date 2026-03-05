# Windows Setup Guide for Canon Shutter Count Reader

This guide helps you set up the Canon Shutter Count Reader on Windows with full native support (no driver changes needed).

## Quick Start (WPD Only - Recommended)

**For cameras from 2016 onwards (Digic 6+, Digic 8, Digic X):**

```bash
# 1. Install Python dependencies
pip install comtypes pywin32 pyusb

# 2. Run the unified reader
python canon_shutter_unified.py -v
```

That's it! WPD will work with Windows native drivers.

## Full Setup (WPD + EDSDK + PyUSB)

**For complete coverage including older cameras (2010-2015):**

### Step 1: Install Python Dependencies

```bash
pip install comtypes pywin32 pyusb
```

### Step 2: Setup EDSDK Helpers (Optional - for pre-2016 cameras)

**Option A: Copy from Magpie Project**

If you have the Magpie project with compiled helpers:

```bash
# Copy helpers directory
xcopy /E /I "C:\path\to\Magpie\helpers\shutter-helper-sdk361" "helpers\edsdk\sdk361"
xcopy /E /I "C:\path\to\Magpie\helpers\shutter-helper-sdk35" "helpers\edsdk\sdk35"
xcopy /E /I "C:\path\to\Magpie\helpers\shutter-helper-32" "helpers\edsdk\sdk214"
```

**Option B: Compile Yourself**

See COMPILE_EDSDK_HELPERS.md for detailed instructions.

### Step 3: Test Your Setup

```bash
# Test with verbose output
python canon_shutter_unified.py -v
```

## What Gets Installed

### Python Packages

- **comtypes** (Windows only) - COM API for WPD access
- **pywin32** (Windows only) - Windows API bindings
- **pyusb** (all platforms) - USB library for fallback

### EDSDK Helpers (Optional)

- **SDK 3.6.1** - Jul 2017, supports 6D Mark II, 200D, etc.
- **SDK 3.5** - Sep 2016, supports 80D, 5D Mark IV, etc.
- **SDK 2.14** - Feb 2014, supports 70D, 100D, 700D, 1200D, etc.

Each helper includes:
- `shutter-helper-sdkXXX.exe` - Compiled executable
- `EDSDK.dll` - Canon SDK library
- `EdsImage.dll` - Image processing library
- `Mlib.dll` - Canon utility library (SDK 3.6.1 only)
- `Ucs32P.dll` - Canon utility library (SDK 3.6.1 only)

## Testing

### Test WPD Backend Only

```bash
python wpd_backend.py
```

**Expected output (success):**
```
============================================================
SHUTTER COUNT (via WPD)
============================================================
Mechanical actuations: 15,234
Electronic actuations: 8,451
TOTAL ACTUATIONS:      23,685
Method: WPD Property 0xD167
============================================================
```

**Expected output (camera not supported):**
```
ERROR: Camera doesn't support WPD methods (may be too old for WPD, try EDSDK)
```

### Test EDSDK Backend Only

```bash
python edsdk_backend.py
```

**Expected output (no helpers):**
```
No EDSDK helpers found in helpers/edsdk/

To use EDSDK backend:
1. Copy helper source from Magpie project
2. Compile on Windows
3. Place executables in helpers/edsdk/
```

**Expected output (success):**
```
Found EDSDK helpers: ['sdk361', 'sdk35', 'sdk214']

============================================================
SHUTTER COUNT (via EDSDK)
============================================================
Camera Model: Canon EOS 600D
Serial Number: 123456789
Total actuations: 45,123
Method: EDSDK shutter-helper-sdk361
============================================================
```

### Test Unified Reader

```bash
python canon_shutter_unified.py -v
```

**Expected output:**
```
Canon Camera Shutter Count Reader (Unified)
============================================================
[CanonShutterReader] Trying WPD Property 0xD167 (Digic 8/X cameras)...
[CanonShutterReader] ✓ Success via WPD Property 0xD167

============================================================
SHUTTER COUNT
============================================================
Mechanical actuations: 15,234
Electronic actuations: 8,451
TOTAL ACTUATIONS:      23,685
Method used: WPD Property 0xD167
============================================================

✓ Success!
```

## Troubleshooting

### "No module named 'comtypes'"

**Solution:**
```bash
pip install comtypes
```

### "No module named 'win32com'"

**Solution:**
```bash
pip install pywin32
```

### "No Canon camera found via WPD"

**Checklist:**
- [ ] Camera is connected via USB
- [ ] Camera is powered on
- [ ] Camera is not being used by another program (EOS Utility, Lightroom, etc.)
- [ ] USB cable is working (try a different cable/port)
- [ ] Camera is in PTP/MTP mode (not mass storage)

### "WPD not available: No module named 'PortableDeviceApi'"

**This happens when comtypes hasn't generated the WPD bindings yet.**

**Solution:**
```python
# Run this once to generate bindings
import comtypes.client
comtypes.client.GetModule(('{1F001332-1A57-4934-BE31-AFFC99F4EE0A}', 1, 0))
```

Or just run the script - it will generate bindings on first use.

### "All EDSDK helpers failed"

**If you see this but your camera is newer (2016+):**
- This is normal! EDSDK doesn't support newer cameras.
- WPD should work instead.
- Check WPD error messages above this error.

**If you have an older camera (2010-2015):**
- EDSDK helpers need to be compiled.
- Follow COMPILE_EDSDK_HELPERS.md.

### "PyUSB: WinUSB driver required"

**This is the fallback when all native methods fail.**

**Do you really need PyUSB?**
- Most cameras from 2016+ → Use WPD (no driver needed)
- Most cameras from 2010-2015 → Use EDSDK (compile helpers)
- Only use PyUSB if both fail

**To install WinUSB (not recommended):**
1. Download Zadig: https://zadig.akeo.ie/
2. Run as Administrator
3. Options → List All Devices
4. Select "Canon Digital Camera"
5. Replace driver with WinUSB
6. Reconnect camera

**Warning:** Camera will disappear from Windows Explorer!

### Python Script Won't Run

**Error: "python: command not found"**

**Solutions:**
```bash
# Try py instead of python
py canon_shutter_unified.py -v

# Or use full path
C:\Python39\python.exe canon_shutter_unified.py -v

# Or add Python to PATH
# Windows Settings → System → About → Advanced system settings
# → Environment Variables → Path → Add Python directory
```

## Camera Compatibility by Method

| Camera Generation | Years | Best Method | Fallback |
|------------------|-------|-------------|----------|
| Digic 8/X (R5, R6, R7, R8, R10, 1D X III, R3) | 2020+ | WPD 0xD167 | PyUSB |
| Digic 6+ (5D IV, 90D, 6D II, 80D) | 2016-2019 | WPD 0x905F | PyUSB |
| Pre-Digic 6 (600D-700D, 1100D-1300D, 5D II/III, 6D, 7D) | 2010-2015 | EDSDK | PyUSB |
| Very old (40D, 50D, 450D-550D) | 2008-2010 | EDSDK SDK 2.14 | - |

## Performance Notes

- **WPD Property 0xD167:** ~1 second (fastest)
- **WPD Monitor Mode 0x905F:** ~2 seconds (handshake overhead)
- **EDSDK:** ~2-3 seconds (SDK initialization)
- **PyUSB FAPI:** ~3-4 seconds (complex protocol)

## Next Steps

1. **Test your camera** - Run unified reader and note which method succeeds
2. **Optional: Compile EDSDK helpers** - If you have older cameras
3. **Report compatibility** - Help expand the compatibility list!

## Advanced Configuration

### Force Specific Method

**Use WPD only:**
```bash
python wpd_backend.py
```

**Use EDSDK only:**
```bash
python edsdk_backend.py
```

**Use PyUSB only:**
```bash
python read_shutter_count.py
```

### Integration in Your Scripts

```python
from canon_shutter_unified import read_shutter_count_unified

result = read_shutter_count_unified(verbose=False)

if result.success:
    print(f"Shutter count: {result.total}")
    print(f"Method: {result.source}")
else:
    print(f"Error: {result.error}")
```

## Support

If you encounter issues:

1. Run with `-v` flag for verbose output
2. Test each backend individually
3. Check camera compatibility list
4. Verify Python packages are installed
5. Report issue with camera model and full error output
