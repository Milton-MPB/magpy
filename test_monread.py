#!/usr/bin/env python3
"""Test MonReadAndGetData to read shutter count from camera RAM."""
import sys
import struct
import usb.core
import usb.util

CANON_VID = 0x04a9
PTP_CMD = 0x0001
PTP_DATA = 0x0002
OP_OPEN_SESSION = 0x1002
OP_CLOSE_SESSION = 0x1003
OP_SET_DEVICE_PROP_VALUE = 0x1016
OP_FAPI_TX = 0x9052
OP_FAPI_RX = 0x9053
DPROP_HOST_INFO = 0xd406
HOST_INFO_STR = "/Windows/10.0.22631 MTPClassDriver/10.0.22621.0"

def build_cmd(op_code, tx_id, params=None):
    params = params or []
    length = 12 + 4 * len(params)
    pkt = struct.pack('<IHH', length, PTP_CMD, op_code)
    pkt += struct.pack('<I', tx_id)
    for p in params:
        pkt += struct.pack('<I', p)
    return pkt

def build_data(op_code, tx_id, payload):
    length = 12 + len(payload)
    pkt = struct.pack('<IHH', length, PTP_DATA, op_code)
    pkt += struct.pack('<I', tx_id)
    return pkt + payload

def parse_container(raw):
    if len(raw) < 12:
        raise ValueError(f"Container too short")
    length, ctype, op_code, tx_id = struct.unpack('<IHHI', raw[:12])
    payload = raw[12:length] if length <= len(raw) else raw[12:]
    return ctype, op_code, tx_id, payload

class CanonPTP:
    def __init__(self, dev):
        self.dev = dev
        self.tx_id = 0
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
        print(f"Endpoints: OUT={ep_out.bEndpointAddress if ep_out else None}, "
              f"IN={ep_in.bEndpointAddress if ep_in else None}, "
              f"INT={ep_int.bEndpointAddress if ep_int else None}")

    def _next_tx(self):
        self.tx_id += 1
        return self.tx_id

    def _write(self, data):
        self.ep_out.write(data, timeout=5000)

    def _read(self, max_len=8192):
        return bytes(self.ep_in.read(max_len, timeout=5000))

    def _drain_interrupt(self, label=""):
        """Drain interrupt endpoint - Canon sends events here that must be acknowledged."""
        if not self.ep_int:
            print(f"  [INT drain {label}: no interrupt endpoint]")
            return
        count = 0
        try:
            while count < 10:  # Max 10 reads to prevent infinite loop
                data = bytes(self.ep_int.read(64, timeout=50))
                print(f"  [INT drain {label}: {len(data)} bytes: {data.hex()}]")
                count += 1
        except usb.core.USBTimeoutError:
            if count == 0:
                print(f"  [INT drain {label}: no data (timeout)]")
            else:
                print(f"  [INT drain {label}: done, read {count} packets]")

    def open_session(self):
        tx_id = self._next_tx()
        self._write(build_cmd(OP_OPEN_SESSION, tx_id, [1]))
        self._read()

    def close_session(self):
        try:
            tx_id = self._next_tx()
            self._write(build_cmd(OP_CLOSE_SESSION, tx_id))
            self._read()
        except:
            pass

    def set_host_info(self):
        payload = HOST_INFO_STR.encode('utf-16-le') + b'\x00\x00'
        tx_id = self._next_tx()
        self._write(build_cmd(OP_SET_DEVICE_PROP_VALUE, tx_id, [DPROP_HOST_INFO]))
        self._write(build_data(OP_SET_DEVICE_PROP_VALUE, tx_id, payload))
        self._read()

    def mon_open(self):
        """Open Canon monitor (developer mode)."""
        tx_id = self._next_tx()
        self._write(build_cmd(OP_FAPI_TX, tx_id, [0x00000000, 0x00000000]))

        # Build MonOpen payload
        payload = b'MonOpen\x00'
        payload += struct.pack('<I', 0x00000001)  # param count
        payload += struct.pack('<I', 0x00000002)  # type
        payload += b'\x00' * 44  # padding to match capture

        self._write(build_data(OP_FAPI_TX, tx_id, payload))
        self._drain_interrupt("after MonOpen")
        self._read(64)

    def mon_close(self):
        """Close Canon monitor."""
        tx_id = self._next_tx()
        self._write(build_cmd(OP_FAPI_TX, tx_id, [0x00000000, 0x00000000]))

        payload = b'MonClose\x00'
        payload += struct.pack('<I', 0x00000001)
        payload += struct.pack('<I', 0x00000002)
        payload += b'\x00' * 43

        self._write(build_data(OP_FAPI_TX, tx_id, payload))
        self._drain_interrupt("after MonClose")
        self._read(64)

    def mon_read_and_get_data(self, address, length):
        """Read camera RAM at specified address.

        Protocol sequence:
        → CMD  0x9052  (MonReadAndGetData, txid=N)
        → DATA 0x9052  (struct with address+size, txid=N)
        ← RESP 0x2001  OK  (txid=N)
        → CMD  0x9053  (txid=N+1)
        ← DATA 0x9053  (actual memory data, txid=N+1)
        ← RESP 0x2001  OK  (txid=N+1)
        """
        print(f"\n→ Sending MonReadAndGetData command (addr=0x{address:04x}, len={length})")

        # Phase 1: Send MonReadAndGetData command
        tx_id = self._next_tx()
        cmd = build_cmd(OP_FAPI_TX, tx_id, [0x00000000, 0x00000001])
        print(f"  CMD 0x9052, tx_id={tx_id}, len={len(cmd)}")
        self._write(cmd)

        # Build MonReadAndGetData payload
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

        data_pkt = build_data(OP_FAPI_TX, tx_id, payload)
        print(f"  DATA 0x9052, tx_id={tx_id}, len={len(data_pkt)}")
        self._write(data_pkt)

        # Try draining interrupt BEFORE reading response
        self._drain_interrupt("after DATA send")

        # Read response (should be 0x2001 OK)
        print(f"\n← Reading response to MonReadAndGetData...")
        try:
            resp = self._read(64)
            ctype, op_code, resp_tx, _ = parse_container(resp)
            print(f"  Got response: type=0x{ctype:04x}, op=0x{op_code:04x}, tx={resp_tx}")
        except usb.core.USBTimeoutError as e:
            print(f"  TIMEOUT waiting for response!")
            # Try reading interrupt one more time
            self._drain_interrupt("during timeout")
            raise

        # Phase 2: Retrieve the data with FAPI_RX
        print(f"\n→ Sending FAPI_RX to retrieve data")
        tx_id2 = self._next_tx()
        rx_cmd = build_cmd(OP_FAPI_RX, tx_id2, [0x00000000, 0x00000000, 0x00000001])
        print(f"  CMD 0x9053, tx_id={tx_id2}, len={len(rx_cmd)}")
        self._write(rx_cmd)

        # Drain interrupt again
        self._drain_interrupt("after FAPI_RX cmd")

        # Read the data response
        print(f"\n← Reading data from FAPI_RX...")
        raw = self._read(8192)
        ctype, op_code, resp_tx, response = parse_container(raw)
        print(f"  Got data: type=0x{ctype:04x}, op=0x{op_code:04x}, tx={resp_tx}, payload={len(response)} bytes")

        # If it's a data packet, read the final OK response
        if ctype == PTP_DATA:
            final_resp = self._read(64)
            ctype_f, op_f, tx_f, _ = parse_container(final_resp)
            print(f"  Final OK: type=0x{ctype_f:04x}, op=0x{op_f:04x}, tx={tx_f}")

        return response

dev = usb.core.find(idVendor=CANON_VID)
if not dev:
    print("ERROR: No camera found")
    print("Make sure your camera is:")
    print("  1. Connected via USB")
    print("  2. Powered on")

    if sys.platform == 'win32':
        print("\n  WINDOWS USERS:")
        print("  3. WinUSB driver installed via Zadig")
        print("     Download Zadig: https://zadig.akeo.ie/")
        print("     Replace 'Canon Digital Camera' driver with WinUSB")
    else:
        print("  3. Not claimed by another application")
        if sys.platform == 'linux':
            print("  4. Run with sudo OR configure udev rules")

    sys.exit(1)

# Reset and detach kernel drivers (Linux/macOS only)
try:
    dev.reset()
except:
    pass

if sys.platform != 'win32':
    try:
        cfg = dev.get_active_configuration()
        for intf in cfg:
            n = intf.bInterfaceNumber
            try:
                if dev.is_kernel_driver_active(n):
                    print(f"Detaching kernel driver from interface {n}")
                    dev.detach_kernel_driver(n)
            except NotImplementedError:
                pass  # Driver detachment not supported on this platform
            except Exception as e:
                print(f"Could not detach interface {n}: {e}")
    except Exception as e:
        print(f"Error during detach: {e}")
else:
    print("Windows detected: Assuming WinUSB driver is installed via Zadig")

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
        sys.exit(1)
    else:
        raise

ptp = CanonPTP(dev)

# Memory addresses from Tornado capture
memory_reads = [
    (0x1015, 10, "read #1"),
    (0x2480, 17, "read #2"),
    (0x100b, 10, "read #3"),
    (0x2492, 14, "read #4"),
    (0x1180, 8, "read #5"),
    (0x103e, 1, "read #6"),
    (0x1040, 1, "read #7"),
]

try:
    ptp.open_session()
    ptp.set_host_info()

    print("Opening Canon monitor...")
    ptp.mon_open()

    print("\n" + "="*60)
    print("READING SHUTTER COUNT FROM CAMERA RAM")
    print("="*60)

    # The Tornado protocol: read 10 bytes from 0x1015
    SHUTTER_ADDR = 0x1015
    SHUTTER_LEN = 10

    response = ptp.mon_read_and_get_data(SHUTTER_ADDR, SHUTTER_LEN)

    print(f"\nRaw data from address 0x{SHUTTER_ADDR:04x} ({SHUTTER_LEN} bytes):")
    print(f"Hex: {response.hex()}")

    if len(response) >= 10:
        # Parse according to Tornado's protocol:
        # Bytes 0-3: Mechanical shutter count (little-endian uint32)
        # Bytes 4-5: Padding zeros
        # Bytes 6-9: Electronic shutter count (little-endian uint32)

        mechanical = struct.unpack_from('<I', response, 0)[0]
        electronic = struct.unpack_from('<I', response, 6)[0]
        total = mechanical + electronic

        print("\n" + "="*60)
        print("SHUTTER COUNT DECODED")
        print("="*60)
        print(f"Mechanical shutter: {mechanical:,}")
        print(f"Electronic shutter: {electronic:,}")
        print(f"TOTAL ACTUATIONS:   {total:,}")
        print("="*60)
    else:
        print(f"ERROR: Expected 10 bytes, got {len(response)}")

    print("\n\nOther memory reads for analysis:\n")

    for addr, length, desc in memory_reads[1:]:  # Skip first one (0x1015) since we just did it
        try:
            response = ptp.mon_read_and_get_data(addr, length)
            print(f"{desc} - Address 0x{addr:04x}, Length {length}:")
            print(f"  Hex: {response.hex()}")
            print()
        except Exception as e:
            print(f"{desc}: Error - {e}\n")

    print("Closing Canon monitor...")
    ptp.mon_close()

finally:
    ptp.close_session()
    usb.util.dispose_resources(dev)
