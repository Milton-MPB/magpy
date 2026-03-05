#!/usr/bin/env python3
"""
Canon Camera Shutter Count Retrieval Tool
Uses USB PTP protocol, based on Wireshark analysis of the Tornado tool.

Successfully tested on:
  - Canon EOS 6D Mark II (macOS) - shutter count retrieved via FAPI method

Requirements: pip install pyusb

macOS: brew install libusb
Linux: may need root or udev rule: ATTRS{idVendor}=="04a9", MODE="0666"
Windows: Install WinUSB driver using Zadig (replaces native Windows MTP driver)
"""
import sys
import struct
import usb.core
import usb.util

# Canon USB Vendor ID
CANON_VID = 0x04a9

# PTP Container Types
PTP_CMD = 0x0001
PTP_DATA = 0x0002
PTP_RSP = 0x0003

# PTP Operation Codes
OP_OPEN_SESSION = 0x1002
OP_CLOSE_SESSION = 0x1003
OP_GET_DEVICE_PROP_VALUE = 0x1015
OP_SET_DEVICE_PROP_VALUE = 0x1016
OP_FAPI_TX = 0x9052  # Canon vendor operation
OP_FAPI_RX = 0x9053  # Canon vendor operation

# Device Properties
DPROP_HOST_INFO = 0xd406
DPROP_SHUTTER_COUNT = 0xd303

# Canon FAPI Properties
FAPI_PROP_MAINTENANCE = 0x80030000
FAPI_PROP_SHUTTER_COUNT = 0x0e070000  # Potential shutter counter from Tornado capture
FAPI_PROP_MIRROR_COUNT = 0x0e070001   # Potential mirror counter from Tornado capture
FAPI_PROP_ALTERNATE_1 = 0x80030001
FAPI_PROP_ALTERNATE_2 = 0x80030002

# Response Codes
RSP_OK = 0x2001

# Host identification string (required by Canon)
HOST_INFO_STR = "/Windows/10.0.22631 MTPClassDriver/10.0.22621.0"


def build_cmd(op_code, tx_id, params=None):
    """Build a PTP Command container."""
    params = params or []
    length = 12 + 4 * len(params)
    pkt = struct.pack('<IHH', length, PTP_CMD, op_code)
    pkt += struct.pack('<I', tx_id)
    for p in params:
        pkt += struct.pack('<I', p)
    return pkt


def build_data(op_code, tx_id, payload):
    """Build a PTP Data container."""
    length = 12 + len(payload)
    pkt = struct.pack('<IHH', length, PTP_DATA, op_code)
    pkt += struct.pack('<I', tx_id)
    return pkt + payload


def parse_container(raw):
    """Parse a PTP container and return (type, opcode, tx_id, payload)."""
    if len(raw) < 12:
        raise ValueError(f"Container too short ({len(raw)} bytes)")
    length, ctype, op_code, tx_id = struct.unpack('<IHHI', raw[:12])
    payload = raw[12:length] if length <= len(raw) else raw[12:]
    return ctype, op_code, tx_id, payload


class CanonPTP:
    """Canon PTP/USB communication handler."""

    def __init__(self, dev):
        self.dev = dev
        self.tx_id = 0
        self.ep_out, self.ep_in = self._find_ptp_endpoints()

    def _find_ptp_endpoints(self):
        """Locate PTP bulk endpoints (OUT and IN)."""
        cfg = self.dev.get_active_configuration()
        ep_out = ep_in = None
        for intf in cfg:
            # PTP class is 0x06, but Canon may use 0xFF (vendor-specific)
            if intf.bInterfaceClass not in (0x06, 0xFF):
                continue
            for ep in intf:
                if usb.util.endpoint_type(ep.bmAttributes) != usb.util.ENDPOINT_TYPE_BULK:
                    continue
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                    ep_in = ep
                else:
                    ep_out = ep
            if ep_out and ep_in:
                break
        if not ep_out or not ep_in:
            raise RuntimeError(
                "Could not locate PTP bulk endpoints.\n"
                "  - Check that camera is in 'PC Connect' or 'PTP' mode (not charging mode)\n"
                "  - On Windows: Ensure WinUSB driver is installed via Zadig"
            )
        return ep_out, ep_in

    def _next_tx(self):
        """Get next transaction ID."""
        self.tx_id += 1
        return self.tx_id

    def _write(self, data):
        """Write data to bulk OUT endpoint."""
        self.ep_out.write(data, timeout=5000)

    def _read(self, max_len=8192):
        """Read data from bulk IN endpoint."""
        return bytes(self.ep_in.read(max_len, timeout=5000))

    def _transact(self, op_code, params=None, send_payload=None):
        """
        Execute a PTP transaction:
        1. Send CMD container
        2. Send DATA container if payload provided
        3. Receive DATA container if camera sends it
        4. Receive RSP container
        Returns DATA payload if received, None otherwise.
        """
        tx_id = self._next_tx()

        # Send command
        self._write(build_cmd(op_code, tx_id, params or []))

        # Send data if provided
        if send_payload is not None:
            self._write(build_data(op_code, tx_id, send_payload))

        result = None
        raw = self._read()
        ctype, _, _, payload = parse_container(raw)

        # If camera sends data, read it then get response
        if ctype == PTP_DATA:
            result = payload
            raw = self._read(64)
            ctype, _, _, _ = parse_container(raw)

        # Check response code
        if ctype == PTP_RSP:
            rsp_code = struct.unpack_from('<H', raw, 6)[0]
            if rsp_code != RSP_OK:
                raise RuntimeError(f"PTP error 0x{rsp_code:04x} for op 0x{op_code:04x}")

        return result

    def open_session(self, session_id=1):
        """Open a PTP session."""
        self._transact(OP_OPEN_SESSION, params=[session_id])

    def close_session(self):
        """Close the PTP session."""
        try:
            self._transact(OP_CLOSE_SESSION)
        except Exception:
            pass

    def set_host_info(self):
        """
        Set host information (required by Canon before vendor operations).
        Uses device property 0xd406.
        """
        payload = HOST_INFO_STR.encode('utf-16-le') + b'\x00\x00'
        self._transact(OP_SET_DEVICE_PROP_VALUE, params=[DPROP_HOST_INFO],
                       send_payload=payload)

    def get_shutter_count_standard(self):
        """
        Method A: Read shutter count via standard PTP property 0xd303.
        This may not work on all Canon models.
        """
        data = self._transact(OP_GET_DEVICE_PROP_VALUE, params=[DPROP_SHUTTER_COUNT])
        if data and len(data) >= 4:
            return struct.unpack_from('<I', data)[0]
        raise RuntimeError(f"Unexpected response for 0xd303: {data!r}")

    def get_shutter_count_fapi(self, property_id=FAPI_PROP_MAINTENANCE):
        """
        Method B: Read shutter count via Canon FAPI maintenance block.
        Uses Canon vendor operations 0x9052 (FAPI TX) and 0x9053 (FAPI RX).
        This is the method used by the Tornado tool.
        """
        # Step 1: Send FA_GetProperty request via 0x9052
        tx_id = self._next_tx()
        self._write(build_cmd(OP_FAPI_TX, tx_id, params=[0x00000000, 0x00000001]))

        # Build FA_GetProperty payload (63 bytes total)
        fa_payload = b'FA_GetProperty\x00'  # 15 bytes
        fa_payload += struct.pack('<I', 0x00000002)  # param count
        fa_payload += struct.pack('<I', 0x00000002)  # type
        fa_payload += struct.pack('<I', property_id)  # property to read
        fa_payload += struct.pack('<I', 0x00000000)
        fa_payload += struct.pack('<I', 0x00000000)
        fa_payload += struct.pack('<I', 0x00000000)
        fa_payload += struct.pack('<I', 0x00000002)
        fa_payload += b'\x00' * 20  # padding to reach 63 bytes

        self._write(build_data(OP_FAPI_TX, tx_id, fa_payload))

        # Receive response
        rsp = self._read(64)
        ctype, _, _, _ = parse_container(rsp)
        if ctype != PTP_RSP:
            raise RuntimeError(f"Expected RSP after FAPI TX, got 0x{ctype:04x}")

        # Step 2: Retrieve result via 0x9053
        tx_id2 = self._next_tx()
        self._write(build_cmd(OP_FAPI_RX, tx_id2,
                              params=[0x00000000, 0x00000000, 0x00000001]))

        raw = self._read(8192)
        ctype, _, _, payload = parse_container(raw)

        if ctype == PTP_DATA:
            self._read(64)  # consume RSP
        else:
            raise RuntimeError(f"Expected DATA from FAPI RX, got 0x{ctype:04x}")

        # Parse maintenance block response (13 bytes)
        # Shutter count is at bytes [4:8] as UINT32 little-endian
        if len(payload) < 8:
            raise RuntimeError(f"FAPI response too short: {payload.hex()}")

        # DEBUG: Print full response to analyze structure
        print(f"\n[DEBUG] FAPI response length: {len(payload)} bytes")
        print(f"[DEBUG] Full hex dump: {payload.hex()}")
        print(f"[DEBUG] Byte-by-byte:")
        for i in range(min(len(payload), 20)):
            print(f"  [{i:2d}] 0x{payload[i]:02x} ({payload[i]:3d})")

        # Try reading UINT32 from different offsets
        print(f"\n[DEBUG] UINT32 values at different offsets:")
        for offset in range(0, min(len(payload) - 3, 16)):
            val = struct.unpack_from('<I', payload, offset)[0]
            print(f"  Offset {offset:2d}: {val:10d} (0x{val:08x})")

        return struct.unpack_from('<I', payload, 4)[0]


def find_canon_cameras():
    """Find all connected Canon USB devices."""
    devices = list(usb.core.find(find_all=True, idVendor=CANON_VID))
    cameras = []
    for dev in devices:
        try:
            name = usb.util.get_string(dev, dev.iProduct)
        except Exception:
            name = f"Unknown Canon (PID 0x{dev.idProduct:04x})"
        cameras.append((dev, name))
    return cameras


def detach_kernel_drivers(dev):
    """Detach kernel drivers if necessary (Linux)."""
    try:
        cfg = dev.get_active_configuration()
        for intf in cfg:
            n = intf.bInterfaceNumber
            try:
                if dev.is_kernel_driver_active(n):
                    dev.detach_kernel_driver(n)
            except (usb.core.USBError, NotImplementedError):
                pass
    except Exception:
        pass


def main():
    """Main entry point."""
    cameras = find_canon_cameras()

    if not cameras:
        print("ERROR: No Canon cameras detected.")
        print("\nMake sure your camera is:")
        print("  1. Connected via USB with a good quality cable")
        print("  2. Powered on")
        print("  3. Set to 'PC Connect', 'PTP', or 'PC Remote' mode in camera settings")
        print("     (Check your camera's menu: some cameras default to charge-only mode)")
        print("\nSystem setup:")
        print("  - macOS: Install libusb (brew install libusb)")
        print("  - Linux: Run with sudo OR add udev rule (see README)")
        print("  - Windows: Install WinUSB driver via Zadig (see README)")
        print("\nTo verify camera is visible:")
        print("  - macOS/Linux: lsusb | grep Canon")
        print("  - Windows: Check Device Manager")
        sys.exit(1)

    # Select camera if multiple found
    if len(cameras) == 1:
        dev, name = cameras[0]
        print(f"Found: {name}")
    else:
        print(f"Found {len(cameras)} Canon cameras:")
        for i, (_, name) in enumerate(cameras):
            print(f"  [{i}] {name}")
        idx = int(input("Select device: "))
        dev, name = cameras[idx]

    # Initialize USB device
    try:
        detach_kernel_drivers(dev)
        dev.set_configuration()
    except usb.core.USBError as e:
        print(f"WARNING: USB configuration error: {e}")
        print("Continuing anyway...")

    # Create PTP handler and retrieve shutter count
    ptp = CanonPTP(dev)

    try:
        ptp.open_session()
        ptp.set_host_info()

        # Try standard method first, fall back to FAPI if needed
        try:
            count = ptp.get_shutter_count_standard()
            method = "Standard PTP (0xd303)"
        except Exception as e:
            if "0x2005" in str(e):
                print("Note: Standard method (0xd303) not supported by this camera.")
                print("      This is normal for many Canon models.")
            else:
                print(f"Standard method failed: {e}")
            print("\nTrying different Canon FAPI properties...")

            # Try different property IDs to find the right counter
            properties_to_try = [
                (FAPI_PROP_SHUTTER_COUNT, "0x0e070000 (shutter counter from Tornado)"),
                (FAPI_PROP_MIRROR_COUNT, "0x0e070001 (mirror counter from Tornado)"),
                (FAPI_PROP_MAINTENANCE, "0x80030000 (maintenance)"),
                (FAPI_PROP_ALTERNATE_1, "0x80030001"),
                (FAPI_PROP_ALTERNATE_2, "0x80030002"),
            ]

            for prop_id, prop_name in properties_to_try:
                try:
                    print(f"\nTrying property {prop_name}...")
                    count = ptp.get_shutter_count_fapi(property_id=prop_id)
                    method = f"Canon FAPI ({prop_name})"
                    break
                except Exception as prop_err:
                    print(f"  Failed: {prop_err}")
            else:
                raise RuntimeError("All FAPI properties failed")

        print(f"\n{'='*50}")
        print(f"Camera:        {name}")
        print(f"Shutter Count: {count:,}")
        print(f"Method used:   {method}")
        print(f"{'='*50}\n")

    finally:
        ptp.close_session()
        usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
