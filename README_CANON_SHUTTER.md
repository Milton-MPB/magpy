# Canon Shutter Count Tool

A Python tool to retrieve shutter count from Canon cameras via USB, based on reverse-engineering the Tornado tool using Wireshark analysis.

## Features

- Reads shutter count from Canon EOS cameras via USB PTP protocol
- Two retrieval methods:
  - **Method A**: Standard PTP property `0xd303` (TotalNumberOfShutter)
  - **Method B**: Canon FAPI maintenance block `0x80030000` (same method as Tornado)
- Automatic fallback if standard method fails
- Works with Canon EOS 6D Mark II (tested via Wireshark captures)
- Likely compatible with other Canon EOS models

## Requirements

### Python Dependencies

```bash
pip install pyusb
```

### Platform-Specific Setup

#### Linux

You may need root access OR create a udev rule:

```bash
# Create udev rule (recommended)
sudo tee /etc/udev/rules.d/50-canon.rules > /dev/null <<'EOF'
# Canon cameras
ATTRS{idVendor}=="04a9", MODE="0666", GROUP="plugdev"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then reconnect your camera.

#### macOS

Install libusb (required by PyUSB):

```bash
brew install libusb
```

No other setup required. The tool works without `sudo` on macOS.

#### Windows

✅ **Windows is now fully supported!** This script works on Windows using the WinUSB driver.

⚠️ **Important**: You must install the WinUSB driver using Zadig before running the script. This replaces Windows' native MTP driver temporarily, so your camera won't appear in Windows Explorer or Photos app while WinUSB is active. This change is **fully reversible** (see below).

**Step-by-Step Setup**:

1. **Install Python dependencies**:
   ```bash
   pip install pyusb
   ```

2. **Download Zadig**:
   - Get it from [https://zadig.akeo.ie/](https://zadig.akeo.ie/)
   - Zadig is a trusted USB driver installer tool for Windows

3. **Install WinUSB driver**:
   - Connect your Canon camera via USB and power it on
   - Run Zadig **as Administrator** (right-click → Run as Administrator)
   - In Zadig menu: **Options → List All Devices**
   - From the dropdown, select your Canon camera (e.g., "Canon Digital Camera")
   - In the driver selection box (right side with arrows), select **WinUSB**
   - Click **Replace Driver** (or **Install Driver** if no driver exists)
   - Wait for the installation to complete (may take 1-2 minutes)

4. **Run the script**:
   ```bash
   python read_shutter_count.py
   ```

   No `sudo` required on Windows!

**Reverting to Normal Camera Mode**:

To use your camera normally in Windows Explorer and Photos app again:

1. Open **Device Manager** (Windows key + X → Device Manager)
2. Expand **Universal Serial Bus devices**
3. Find your Canon camera (will show as WinUSB device)
4. Right-click → **Uninstall device**
5. Check "**Delete the driver software for this device**"
6. Click **Uninstall**
7. Unplug and replug the camera
8. Windows will automatically reinstall the native MTP driver

Your camera will now work normally in Windows again.

**What happens with WinUSB installed?**

| Feature | With Native Driver | With WinUSB Driver |
|---------|-------------------|-------------------|
| Windows Explorer access | ✓ Works | ✗ Camera hidden |
| Photos app import | ✓ Works | ✗ Camera hidden |
| This Python script | ✗ Fails | ✓ **Works** |
| Reversible | N/A | ✓ Yes (see above) |

## Usage

### Basic Usage

```bash
python3 canon_shutter_count.py
```

The tool will:
1. Detect connected Canon cameras
2. If multiple cameras found, prompt you to select one
3. Retrieve and display the shutter count

### Example Output

```
Found: Canon EOS 6D Mark II

==================================================
Camera:        Canon EOS 6D Mark II
Shutter Count: 3,902
Method used:   Canon FAPI (0x80030000)
==================================================
```

## How It Works

### Protocol Details

The tool uses the **USB PTP (Picture Transfer Protocol)** to communicate with Canon cameras:

1. **Session Setup**
   - Opens PTP session (opcode `0x1002`)
   - Identifies host via `SetDevicePropValue(0xd406)` with Windows MTP driver string

2. **Method A - Standard PTP**
   - Reads device property `0xd303` (TotalNumberOfShutter)
   - Simple and fast, but may not work on all models

3. **Method B - Canon FAPI** (used by Tornado)
   - Sends `FA_GetProperty` request via vendor opcode `0x9052` (FAPIMessageTX)
   - Requests maintenance property `0x80030000`
   - Retrieves response via vendor opcode `0x9053` (FAPIMessageRX)
   - Parses 13-byte response: shutter count is at bytes [4:8] as UINT32

### Key Technical Details

- **Canon USB VID**: `0x04a9`
- **PTP Bulk Endpoints**: OUT=`0x02`, IN=`0x81`
- **Host ID String**: `/Windows/10.0.22631 MTPClassDriver/10.0.22621.0`
- **FAPI Payload**: 63-byte structure with function name + parameters
- **Response Parsing**: UINT32 little-endian at offset 4 in maintenance block

## Troubleshooting

### "No Canon cameras detected"

**Check camera setup**:
- Ensure camera is powered on
- Check USB cable connection (use a good quality cable)
- **Check camera USB mode**: Most cameras need to be set to "PC Connect", "PTP", or "PC Remote" mode in camera menu settings (not just charging mode)
- Try a different USB port or cable

**Check system setup**:
- **macOS**: Install libusb: `brew install libusb`
- **Linux**: Add udev rule (see setup section above) or try with `sudo`
- **Windows**: Ensure WinUSB driver is installed via Zadig (Option B above)

**Verify camera is visible**:
- macOS/Linux: Run `system_profiler SPUSBDataType | grep -A 10 Canon` or `lsusb | grep Canon`
- Windows: Check Device Manager for your Canon camera

### "Could not locate PTP bulk endpoints"

- The camera may be in the wrong USB mode
- Try switching camera to different USB connection modes in settings
- Some cameras require specific modes like "PC Remote" or "PTP/MTP"
- On Windows: If using WinUSB driver, the camera should appear under "Universal Serial Bus devices" in Device Manager

### Permission Errors (Linux)

```bash
# Quick fix: run with sudo
sudo python3 canon_shutter_count.py

# Better fix: add udev rule (see setup section above)
```

### "PTP error 0x2005" (Operation Not Supported)

This is **normal** for some cameras when using Method A (property 0xd303). The script will automatically fall back to Method B (Canon FAPI), which works on most Canon EOS models.

If Method B also fails:
- Try restarting the camera
- Check if camera firmware is up to date
- The camera may use a different Canon proprietary method

### Windows-Specific Issues

**"ERROR: No Canon camera found"**:
- Make sure WinUSB driver is installed via Zadig (see Windows Setup section)
- Check Device Manager to confirm camera is recognized
- Try a different USB cable or port
- Ensure camera is powered on and in the correct USB mode

**"USB Error: [Errno 13] Access denied"** or **"[Errno 5] Input/Output Error"**:
- This usually means WinUSB driver is not installed
- Follow the Zadig installation steps in the Windows Setup section above
- Make sure you ran Zadig as Administrator
- Ensure no other applications are using the camera

**Camera works in Windows Explorer but not with script**:
- You're using Windows' native MTP driver
- Install WinUSB driver via Zadig (see Windows Setup section)
- **Note**: This will make the camera stop working in Windows Explorer until you revert the driver (which is easy - see "Reverting to Normal Camera Mode" above)

## Tested Cameras

### Confirmed Working

- ✅ **Canon EOS 6D Mark II** (USB PID: 0x32ca)
  - Tested on macOS with shutter count retrieval: **SUCCESS**
  - Method A (0xd303): ✗ Not supported (PTP error 0x2005)
  - Method B (Canon FAPI 0x80030000): ✓ **Works perfectly**
  - Script automatically falls back to working method

### Likely Compatible

Based on protocol similarity, likely works with:
- Canon EOS R series (R, R5, R6, R7, etc.)
- Canon EOS 5D series (5D Mark III, IV)
- Canon EOS 6D series
- Canon EOS 7D series
- Canon EOS Rebel/T series (newer models)
- Canon EOS M series

*If you test on other models, please report your results!*

## Technical Notes

### FAPI Protocol

Canon's **FAPI (Functional API)** is a proprietary RPC mechanism over PTP:
- Uses string-based function names (`FA_GetProperty`, `FA_SetProperty`)
- Binary parameter encoding (type + property ID + padding)
- Vendor opcodes `0x9052` (TX) and `0x9053` (RX)

### PTP Container Format

```
Offset  Size  Field
0       4     Length (total bytes)
4       2     Container Type (0x0001=CMD, 0x0002=DATA, 0x0003=RSP)
6       2     Operation Code
8       4     Transaction ID
12+     N     Parameters (CMD) or Payload (DATA)
```

### FA_GetProperty Payload Structure (63 bytes)

```
Offset  Size  Field
0       15    "FA_GetProperty\x00"
15      4     Param count (0x00000002)
19      4     Type field (0x00000002)
23      4     Property ID (e.g., 0x80030000)
27      36    Padding and additional parameters
```

### Maintenance Block Response (13 bytes)

```
Offset  Size  Field
0       1     Status byte
1       3     Padding/unknown
4       4     Shutter count (UINT32 LE) ← KEY FIELD
8       4     Unknown counter
12      1     Flags byte
```

## Reverse Engineering Source

This tool was created by analyzing Wireshark USB captures of the **Tornado ShutterCount** tool:
- Full packet captures with hex dumps
- Identified PTP container structures
- Decoded Canon FAPI protocol
- Recreated exact request/response sequences

## License

This tool is provided for educational and personal use. Use responsibly.

## Acknowledgments

- Tornado ShutterCount tool (reverse-engineered via Wireshark)
- PyUSB library
- Canon PTP/FAPI protocol documentation (community sources)
