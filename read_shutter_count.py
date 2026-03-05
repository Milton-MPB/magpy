#!/usr/bin/env python3
"""
Canon Camera Shutter Count Reader
Uses the undocumented MonReadAndGetData protocol to read shutter count from camera RAM.
Tested on Canon 6D Mark II - address 0x1015 contains the shutter count.
"""
import sys
import struct
import usb.core
import usb.util

# Canon USB vendor ID
CANON_VID = 0x04a9

# PTP packet types
PTP_CMD = 0x0001
PTP_DATA = 0x0002
PTP_RESP = 0x0003

# PTP opcodes
OP_OPEN_SESSION = 0x1002
OP_CLOSE_SESSION = 0x1003
OP_SET_DEVICE_PROP_VALUE = 0x1016
OP_FAPI_TX = 0x9052  # Canon-specific: Factory API transmit
OP_FAPI_RX = 0x9053  # Canon-specific: Factory API receive

# Device properties
DPROP_HOST_INFO = 0xd406
HOST_INFO_STR = "/Windows/10.0.22631 MTPClassDriver/10.0.22621.0"

# Shutter count memory location (Canon 6D Mark II)
SHUTTER_COUNT_ADDR = 0x1015
SHUTTER_COUNT_LEN = 10


def build_cmd(op_code, tx_id, params=None):
    """Build a PTP command packet."""
    params = params or []
    length = 12 + 4 * len(params)
    pkt = struct.pack('<IHH', length, PTP_CMD, op_code)
    pkt += struct.pack('<I', tx_id)
    for p in params:
        pkt += struct.pack('<I', p)
    return pkt


def build_data(op_code, tx_id, payload):
    """Build a PTP data packet."""
    length = 12 + len(payload)
    pkt = struct.pack('<IHH', length, PTP_DATA, op_code)
    pkt += struct.pack('<I', tx_id)
    return pkt + payload


def parse_container(raw):
    """Parse a PTP container packet."""
    if len(raw) < 12:
        raise ValueError(f"Container too short: {len(raw)} bytes")
    length, ctype, op_code, tx_id = struct.unpack('<IHHI', raw[:12])
    payload = raw[12:length] if length <= len(raw) else raw[12:]
    return ctype, op_code, tx_id, payload


class CanonPTP:
    """Canon PTP/USB communication handler with MonReadAndGetData support."""

    def __init__(self, dev):
        self.dev = dev
        self.tx_id = 0

        # Find bulk and interrupt endpoints
        cfg = dev.get_active_configuration()
        ep_out = ep_in = ep_int = None

        for intf in cfg:
            if intf.bInterfaceClass not in (0x06, 0xFF):
                continue

            for ep in intf:
                ep_type = usb.util.endpoint_type(ep.bmAttributes)
                ep_dir = usb.util.endpoint_direction(ep.bEndpointAddress)

                if ep_type == usb.util.ENDPOINT_TYPE_BULK:
                    if ep_dir == usb.util.ENDPOINT_IN:
                        ep_in = ep
                    else:
                        ep_out = ep
                elif ep_type == usb.util.ENDPOINT_TYPE_INTR and ep_dir == usb.util.ENDPOINT_IN:
                    ep_int = ep

            if ep_out and ep_in:
                break

        self.ep_out, self.ep_in, self.ep_int = ep_out, ep_in, ep_int

    def _next_tx(self):
        """Get next transaction ID."""
        self.tx_id += 1
        return self.tx_id

    def _write(self, data):
        """Write data to USB bulk OUT endpoint."""
        self.ep_out.write(data, timeout=5000)

    def _read(self, max_len=8192):
        """Read data from USB bulk IN endpoint."""
        return bytes(self.ep_in.read(max_len, timeout=5000))

    def _drain_interrupt(self):
        """Drain interrupt endpoint (Canon cameras send events here)."""
        if not self.ep_int:
            return
        try:
            while True:
                self.ep_int.read(64, timeout=50)
        except usb.core.USBTimeoutError:
            pass

    def open_session(self):
        """Open a PTP session with the camera."""
        tx_id = self._next_tx()
        self._write(build_cmd(OP_OPEN_SESSION, tx_id, [1]))
        self._read()

    def close_session(self):
        """Close the PTP session."""
        try:
            tx_id = self._next_tx()
            self._write(build_cmd(OP_CLOSE_SESSION, tx_id))
            self._read()
        except:
            pass

    def set_host_info(self):
        """Set host information (makes camera think we're Windows MTP driver)."""
        payload = HOST_INFO_STR.encode('utf-16-le') + b'\x00\x00'
        tx_id = self._next_tx()
        self._write(build_cmd(OP_SET_DEVICE_PROP_VALUE, tx_id, [DPROP_HOST_INFO]))
        self._write(build_data(OP_SET_DEVICE_PROP_VALUE, tx_id, payload))
        self._read()

    def mon_open(self):
        """Open Canon's internal factory monitor (undocumented)."""
        tx_id = self._next_tx()
        self._write(build_cmd(OP_FAPI_TX, tx_id, [0x00000000, 0x00000000]))

        # Build MonOpen payload
        payload = b'MonOpen\x00'
        payload += struct.pack('<I', 0x00000001)  # param count
        payload += struct.pack('<I', 0x00000002)  # type
        payload += b'\x00' * 44  # padding

        self._write(build_data(OP_FAPI_TX, tx_id, payload))
        self._drain_interrupt()
        self._read(64)

    def mon_close(self):
        """Close Canon's factory monitor."""
        try:
            tx_id = self._next_tx()
            self._write(build_cmd(OP_FAPI_TX, tx_id, [0x00000000, 0x00000000]))

            payload = b'MonClose\x00'
            payload += struct.pack('<I', 0x00000001)
            payload += struct.pack('<I', 0x00000002)
            payload += b'\x00' * 43

            self._write(build_data(OP_FAPI_TX, tx_id, payload))
            self._drain_interrupt()
            self._read(64)
        except:
            pass  # Camera might have disconnected

    def mon_read_and_get_data(self, address, length):
        """
        Read camera RAM at specified address using MonReadAndGetData.

        This is the core exploit - it reads arbitrary camera RAM with no authentication.

        Args:
            address: Memory address to read from
            length: Number of bytes to read

        Returns:
            bytes: Raw memory contents
        """
        # Phase 1: Send MonReadAndGetData command
        tx_id = self._next_tx()
        self._write(build_cmd(OP_FAPI_TX, tx_id, [0x00000000, 0x00000001]))

        # Build MonReadAndGetData payload with address and length
        payload = b'MonReadAndGetData\x00'
        payload += struct.pack('<I', 0x00000003)  # param count
        payload += struct.pack('<I', 0x00000002)  # type
        payload += struct.pack('<I', 0x00000002)  # type
        payload += b'\x00' * 12  # padding
        payload += struct.pack('<I', 0x00000002)  # type
        payload += struct.pack('<I', address)     # memory address
        payload += b'\x00' * 12  # padding
        payload += struct.pack('<I', 0x00000002)  # type
        payload += struct.pack('<I', length)      # read length
        payload += b'\x00' * 12  # padding

        self._write(build_data(OP_FAPI_TX, tx_id, payload))
        self._drain_interrupt()

        # Read OK response
        self._read(64)

        # Phase 2: Retrieve the data with FAPI_RX
        tx_id2 = self._next_tx()
        self._write(build_cmd(OP_FAPI_RX, tx_id2, [0x00000000, 0x00000000, 0x00000001]))
        self._drain_interrupt()

        # Read data response
        raw = self._read(8192)
        ctype, op_code, resp_tx, response = parse_container(raw)

        if ctype == PTP_DATA:
            self._read(64)  # Read final OK

        return response


def read_shutter_count_pyusb():
    """Read shutter count from Canon camera using PyUSB/FAPI method."""
    # Find Canon camera
    dev = usb.core.find(idVendor=CANON_VID)
    if not dev:
        print("ERROR: No Canon camera found")
        print("Make sure your camera is:")
        print("  1. Connected via USB")
        print("  2. Powered on")

        if sys.platform == 'win32':
            print("\n  WINDOWS USERS:")
            print("  3. WinUSB driver installed via Zadig (see README)")
            print("     Download Zadig: https://zadig.akeo.ie/")
            print("     Replace 'Canon Digital Camera' driver with WinUSB")
        else:
            print("  3. Not claimed by another application")
            if sys.platform == 'linux':
                print("  4. Run with sudo OR configure udev rules")

        return None

    # Detach kernel drivers (Linux/macOS only - not needed on Windows)
    if sys.platform != 'win32':
        try:
            cfg = dev.get_active_configuration()
            for intf in cfg:
                n = intf.bInterfaceNumber
                try:
                    if dev.is_kernel_driver_active(n):
                        dev.detach_kernel_driver(n)
                        print(f"Detached kernel driver from interface {n}")
                except NotImplementedError:
                    pass  # Driver detachment not supported on this platform
                except Exception as e:
                    print(f"Could not detach interface {n}: {e}")
        except Exception as e:
            print(f"Warning during driver detach: {e}")
    else:
        # Windows: Driver must be replaced with WinUSB via Zadig beforehand
        print("Windows detected: Assuming WinUSB driver is installed via Zadig")

    # Set USB configuration
    try:
        dev.set_configuration()
    except usb.core.USBError as e:
        if sys.platform == 'win32':
            print(f"\nUSB Error: {e}")
            print("\nThis usually means the WinUSB driver is not installed.")
            print("Install it using Zadig:")
            print("  1. Download from https://zadig.akeo.ie/")
            print("  2. Run Zadig as Administrator")
            print("  3. Options → List All Devices")
            print("  4. Select 'Canon Digital Camera'")
            print("  5. Replace driver with WinUSB")
            print("  6. Reconnect camera and try again")
            return None
        else:
            raise

    ptp = CanonPTP(dev)

    try:
        # Open PTP session and set host info
        ptp.open_session()
        ptp.set_host_info()

        # Open Canon's debug monitor
        print("Opening Canon factory monitor...")
        ptp.mon_open()

        # Read shutter count from RAM
        print(f"Reading shutter count from RAM address 0x{SHUTTER_COUNT_ADDR:04x}...")
        response = ptp.mon_read_and_get_data(SHUTTER_COUNT_ADDR, SHUTTER_COUNT_LEN)

        if len(response) >= 10:
            # Decode according to Tornado protocol:
            # Bytes 0-3: Mechanical shutter count (little-endian uint32)
            # Bytes 4-5: Padding zeros
            # Bytes 6-9: Electronic shutter count (little-endian uint32)
            mechanical = struct.unpack_from('<I', response, 0)[0]
            electronic = struct.unpack_from('<I', response, 6)[0]
            total = mechanical + electronic

            print("\n" + "="*60)
            print("SHUTTER COUNT")
            print("="*60)
            print(f"Mechanical actuations: {mechanical:,}")
            print(f"Electronic actuations: {electronic:,}")
            print(f"TOTAL ACTUATIONS:      {total:,}")
            print("="*60)

            return {
                'mechanical': mechanical,
                'electronic': electronic,
                'total': total,
                'raw_hex': response.hex()
            }
        else:
            print(f"ERROR: Expected 10 bytes, got {len(response)}")
            return None

    finally:
        # Clean up
        print("\nClosing monitor and session...")
        ptp.mon_close()
        ptp.close_session()
        usb.util.dispose_resources(dev)


def read_shutter_count():
    """
    Main entry point for reading shutter count.

    On Windows: Uses unified reader (tries WPD, EDSDK, then PyUSB)
    On macOS/Linux: Uses PyUSB directly
    """
    # On Windows, prefer unified reader which tries native methods first
    if sys.platform == 'win32':
        try:
            from canon_shutter_unified import read_shutter_count_unified
            print("Windows detected: Using unified reader (WPD/EDSDK/PyUSB cascade)")
            print("="*60)

            result = read_shutter_count_unified(verbose=True)

            if result.success:
                # Return in same format as PyUSB for compatibility
                return {
                    'mechanical': result.mechanical,
                    'electronic': result.electronic,
                    'total': result.total,
                    'source': result.source
                }
            else:
                print(f"\nUnified reader error: {result.error}")
                print("\nFalling back to PyUSB method...")
                return read_shutter_count_pyusb()

        except ImportError as e:
            print(f"Unified reader not available: {e}")
            print("Falling back to PyUSB method...")
            return read_shutter_count_pyusb()
    else:
        # macOS/Linux: Use PyUSB directly (works natively)
        return read_shutter_count_pyusb()


if __name__ == '__main__':
    print("Canon Camera Shutter Count Reader")
    print("="*60)

    if sys.platform != 'win32':
        print("WARNING: This uses an undocumented factory debug protocol.")
        print("Use at your own risk!\n")

    result = read_shutter_count()

    if result:
        print("\n✓ Success!")
        sys.exit(0)
    else:
        print("\n✗ Failed to read shutter count")
        sys.exit(1)
