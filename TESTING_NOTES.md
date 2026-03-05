# Testing Notes - Canon Shutter Count Unified Reader

## Implementation Status

✅ **Core implementation complete**
✅ **All backends implemented** (WPD, EDSDK, PyUSB)
✅ **Unified interface complete**
✅ **Documentation complete**
⚠️ **Testing on actual hardware: PENDING**

## What Needs Testing

### Windows Testing

#### Test 1: WPD with Digic 8/X Camera (e.g., R5, R6, R7)

```bash
# Test WPD backend directly
python wpd_backend.py

# Expected: Property 0xD167 should work
# Should return mechanical + electronic counts
```

**What to verify:**
- [ ] Camera detected via WPD
- [ ] Property 0xD167 returns data
- [ ] Mechanical count extracted correctly
- [ ] Electronic count extracted correctly
- [ ] Camera remains visible in Windows Explorer
- [ ] No driver changes needed

#### Test 2: WPD with Digic 6+ Camera (e.g., 5D IV, 90D, 6D II)

```bash
# Test WPD backend directly
python wpd_backend.py

# Expected: Property 0xD167 fails, Monitor Mode 0x905F succeeds
```

**What to verify:**
- [ ] Camera detected via WPD
- [ ] Property 0xD167 returns "not available" (expected)
- [ ] Handshake sequence (0x9116, 0x9114) succeeds
- [ ] Monitor Mode 0x905F returns data
- [ ] Shutter count extracted from response
- [ ] Camera remains visible in Windows Explorer
- [ ] No driver changes needed

#### Test 3: EDSDK with Pre-Digic 6 Camera (e.g., 600D, 1100D)

```bash
# First compile helpers (see COMPILE_EDSDK_HELPERS.md)

# Test EDSDK backend directly
python edsdk_backend.py

# Expected: One of the SDK versions should work
```

**What to verify:**
- [ ] EDSDK helper executables found
- [ ] Helper runs without errors
- [ ] Shutter count returned
- [ ] Camera model and serial detected
- [ ] Camera remains visible in Windows Explorer
- [ ] No driver changes needed

#### Test 4: Unified Reader Windows

```bash
# Test with verbose output
python canon_shutter_unified.py -v

# Should try methods in order and succeed with first working method
```

**What to verify:**
- [ ] Correct method selected for camera
- [ ] Fallback cascade works if primary method fails
- [ ] Correct shutter count returned
- [ ] Source method reported correctly

### macOS/Linux Testing

#### Test 5: PyUSB on macOS

```bash
python read_shutter_count.py

# Should work without driver changes
```

**What to verify:**
- [ ] Camera detected via PyUSB
- [ ] MonReadAndGetData protocol works
- [ ] Mechanical and electronic counts extracted
- [ ] No driver changes needed

#### Test 6: PyUSB on Linux

```bash
sudo python read_shutter_count.py

# May need sudo for USB access
```

**What to verify:**
- [ ] Camera detected (may need sudo or udev rules)
- [ ] MonReadAndGetData protocol works
- [ ] Counts extracted correctly

### Cross-Platform Testing

#### Test 7: Unified Reader on All Platforms

```bash
# Windows
python canon_shutter_unified.py -v

# macOS
python canon_shutter_unified.py -v

# Linux
sudo python canon_shutter_unified.py -v
```

**What to verify:**
- [ ] Platform detection works correctly
- [ ] Windows uses WPD/EDSDK cascade
- [ ] macOS/Linux use PyUSB directly
- [ ] Consistent output format across platforms

## Known Implementation Issues to Watch For

### WPD Backend Potential Issues

1. **COM Interface Generation**
   - comtypes needs to generate PortableDeviceApi interfaces
   - May fail on first run, need to handle gracefully
   - Solution: Pre-generate or catch exception

2. **PROPERTYKEY Structure**
   - ctypes PROPERTYKEY definition may not match exactly
   - Test with actual WPD calls to verify

3. **Data Phase Handling**
   - WITH_DATA_TO_READ implementation is complex
   - May need adjustment based on actual WPD behavior

4. **Buffer Size**
   - Expected sizes (16 bytes for 0xD167, 512 for 0x905F) may vary
   - Needs testing to confirm

### EDSDK Backend Potential Issues

1. **Helper Compilation**
   - Helpers need to be compiled on Windows
   - DLL dependencies must be in same directory
   - Path issues on different Windows versions

2. **SDK Version Compatibility**
   - Camera may require specific SDK version
   - Cascade should handle this, but needs verification

3. **JSON Parsing**
   - Helper output format must match parser
   - Extra debug output could break JSON parsing

### Unified Reader Potential Issues

1. **Import Errors**
   - comtypes may not be available on non-Windows
   - Need to handle ImportError gracefully

2. **Method Priority**
   - Current order may not be optimal for all cameras
   - May need adjustment based on testing

## Testing Procedure

### 1. Windows with Modern Camera (R6, R7, etc.)

```bash
# Step 1: Install dependencies
pip install comtypes pywin32 pyusb

# Step 2: Test WPD directly
python wpd_backend.py
# Expected: Should succeed with Property 0xD167

# Step 3: Test unified
python canon_shutter_unified.py -v
# Expected: Should use WPD Property 0xD167

# Step 4: Verify camera still in Explorer
# Open Windows Explorer
# Navigate to "This PC"
# Camera should still be visible
```

### 2. Windows with Digic 6+ Camera (5D IV, 6D II, etc.)

```bash
# Same as above, but:
# Expected: Should succeed with Monitor Mode 0x905F
```

### 3. Windows with Old Camera (600D, 1100D, etc.)

```bash
# Step 1: Compile EDSDK helpers
# See COMPILE_EDSDK_HELPERS.md

# Step 2: Test EDSDK directly
python edsdk_backend.py
# Expected: Should succeed with one of the SDK versions

# Step 3: Test unified
python canon_shutter_unified.py -v
# Expected: Should try WPD (fail), then EDSDK (succeed)
```

### 4. macOS/Linux

```bash
# Step 1: Install pyusb
pip install pyusb

# Step 2: Test PyUSB directly
python read_shutter_count.py
# Expected: Should succeed

# Step 3: Test unified
python canon_shutter_unified.py -v
# Expected: Should use PyUSB method
```

## Debugging Tips

### Enable Verbose Logging

All scripts support verbose output:
```bash
python wpd_backend.py  # WPD already verbose
python canon_shutter_unified.py -v  # Unified with verbose
```

### Test Individual Components

```bash
# Test WPD camera detection only
python -c "from wpd_backend import WPDCanonCamera; cam = WPDCanonCamera(); print('Found:', cam.find_canon_camera())"

# Test EDSDK helper detection
python -c "from edsdk_backend import find_edsdk_helpers; print(find_edsdk_helpers())"

# Test PyUSB camera detection
python -c "import usb.core; print('Found:', usb.core.find(idVendor=0x04a9))"
```

### Check COM Interface Generation (Windows)

```python
# Verify comtypes can generate WPD interfaces
import comtypes.client
try:
    comtypes.client.GetModule(('{1F001332-1A57-4934-BE31-AFFC99F4EE0A}', 1, 0))
    print("WPD interfaces generated successfully")
except Exception as e:
    print(f"Error generating WPD interfaces: {e}")
```

## Expected Results by Camera

| Camera | Windows Method | macOS/Linux Method | Notes |
|--------|---------------|-------------------|-------|
| R5, R6, R7, R8 | WPD 0xD167 | PyUSB FAPI | Mechanical + electronic |
| R6 II, R6 III | WPD 0xD167 | PyUSB FAPI | Mechanical + electronic |
| 5D IV, 90D | WPD 0x905F | PyUSB FAPI | Total only |
| 6D II, 80D | WPD 0x905F | PyUSB FAPI | Total only |
| 600D-700D | EDSDK | PyUSB FAPI | Need helpers |
| 1100D-1300D | EDSDK | PyUSB FAPI | Need helpers |
| 5D II/III, 6D | EDSDK | PyUSB FAPI | Need helpers |

## Reporting Test Results

When reporting test results, include:

1. **Camera model and firmware version**
2. **Platform (Windows version, macOS version, Linux distro)**
3. **Python version**
4. **Installed packages** (`pip list | grep -E "(comtypes|pywin32|pyusb)"`)
5. **Command run** (with -v flag)
6. **Full output** (including any errors)
7. **Success/failure** (did shutter count match expected value?)

## Next Steps After Testing

Once testing is complete:

1. **Fix any bugs discovered**
2. **Update compatibility matrix** based on real results
3. **Optimize method priority** if needed
4. **Add more error handling** for edge cases
5. **Consider adding camera database** for known working methods
6. **Package for distribution** (PyPI, installer, etc.)

## Implementation Quality

The implementation is based on:
- ✅ **Proven code from Magpie project** (WPD and EDSDK)
- ✅ **Documented PTP protocols**
- ✅ **Research from gphoto2 logs**
- ✅ **Careful code review and error handling**

However, **no code is perfect without testing**. The WPD implementation in particular is based on COM API documentation and Magpie's C++ code, but needs real hardware validation.

## Conclusion

The implementation is **functionally complete** but **requires hardware testing** to validate:
- WPD COM API calls work correctly
- Property 0xD167 response parsing is correct
- Monitor Mode 0x905F handshake and parsing works
- EDSDK helpers integrate correctly
- Unified cascade logic works as designed

**Confidence level:**
- PyUSB backend: **High** (already proven working)
- EDSDK backend: **Medium-High** (wrapper for proven helpers)
- WPD backend: **Medium** (new implementation, needs validation)
- Unified interface: **High** (orchestration logic is straightforward)
