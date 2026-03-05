#!/usr/bin/env python3
"""Test all FAPI properties from Tornado capture to find the correct shutter count."""
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
        ep_out = ep_in = None
        for intf in cfg:
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
        self.ep_out, self.ep_in = ep_out, ep_in

    def _next_tx(self):
        self.tx_id += 1
        return self.tx_id

    def _write(self, data):
        self.ep_out.write(data, timeout=5000)

    def _read(self, max_len=8192):
        return bytes(self.ep_in.read(max_len, timeout=5000))

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

    def get_fapi_property(self, property_id):
        tx_id = self._next_tx()
        self._write(build_cmd(OP_FAPI_TX, tx_id, [0x00000000, 0x00000001]))

        fa_payload = b'FA_GetProperty\x00'
        fa_payload += struct.pack('<I', 0x00000002)
        fa_payload += struct.pack('<I', 0x00000002)
        fa_payload += struct.pack('<I', property_id)
        fa_payload += struct.pack('<I', 0x00000000)
        fa_payload += struct.pack('<I', 0x00000000)
        fa_payload += struct.pack('<I', 0x00000000)
        fa_payload += struct.pack('<I', 0x00000002)
        fa_payload += b'\x00' * 20

        self._write(build_data(OP_FAPI_TX, tx_id, fa_payload))
        self._read(64)

        tx_id2 = self._next_tx()
        self._write(build_cmd(OP_FAPI_RX, tx_id2, [0x00000000, 0x00000000, 0x00000001]))
        raw = self._read(8192)
        ctype, _, _, payload = parse_container(raw)
        if ctype == PTP_DATA:
            self._read(64)
        return payload

dev = usb.core.find(idVendor=CANON_VID)
if not dev:
    print("No camera found")
    sys.exit(1)

try:
    cfg = dev.get_active_configuration()
    for intf in cfg:
        n = intf.bInterfaceNumber
        try:
            if dev.is_kernel_driver_active(n):
                dev.detach_kernel_driver(n)
        except:
            pass
except:
    pass

dev.set_configuration()
ptp = CanonPTP(dev)

# All properties from Tornado capture
properties = [
    (0x00000002, "unknown 1"),
    (0x01000006, "unknown 2"),
    (0x01000000, "unknown 3"),
    (0x01000002, "unknown 4"),
    (0x02000001, "unknown 5"),
    (0x80030000, "maintenance"),
    (0x01000012, "unknown 7"),
    (0x02040005, "unknown 8"),
    (0x02040002, "unknown 9"),
    (0x02040003, "unknown 10"),
    (0x02000004, "unknown 11"),
    (0x0e070000, "first counter"),
    (0x0e070001, "second counter"),
]

try:
    ptp.open_session()
    ptp.set_host_info()

    print(f"Searching for shutter count 19,356 (0x4B9C)...\n")

    for prop_id, desc in properties:
        try:
            payload = ptp.get_fapi_property(prop_id)

            # Look for 19356 anywhere in the response
            target = 19356
            found_exact = False

            print(f"Property 0x{prop_id:08x} ({desc}):")
            print(f"  Length: {len(payload)} bytes")
            print(f"  Hex: {payload[:32].hex()}{'...' if len(payload) > 32 else ''}")

            # Check all offsets for UINT32 values
            interesting_values = []
            for offset in range(0, min(len(payload) - 3, 32)):
                val = struct.unpack_from('<I', payload, offset)[0]
                if val == target:
                    print(f"  ✓✓✓ FOUND {val:,} at offset {offset} ✓✓✓")
                    found_exact = True
                elif 10000 <= val <= 25000:
                    interesting_values.append((offset, val))

            if interesting_values and not found_exact:
                print(f"  Interesting values:")
                for offset, val in interesting_values[:3]:
                    print(f"    Offset {offset}: {val:,}")

            print()

        except Exception as e:
            print(f"Property 0x{prop_id:08x}: Error - {e}\n")

finally:
    ptp.close_session()
    usb.util.dispose_resources(dev)
