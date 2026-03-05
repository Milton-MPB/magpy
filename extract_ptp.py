#!/usr/bin/env python3
"""Extract clean PTP packet sequence from pcapng."""
import struct

def find_all_ptp_packets(data):
    """Find all valid PTP packets in the data."""
    packets = []
    offset = 0

    while offset < len(data) - 12:
        try:
            length, ptype, opcode, tx_id = struct.unpack_from('<IHHI', data, offset)

            # Valid PTP packet
            if ptype in (0x0001, 0x0002, 0x0003) and 12 <= length <= 8192:
                # Additional validation: make sure we have enough data
                if offset + length <= len(data):
                    packet_data = data[offset:offset+length]
                    payload = packet_data[12:]

                    # Skip if it looks like garbage (all zeros or invalid)
                    if length > 12 and not all(b == 0 for b in payload[:min(20, len(payload))]):
                        packets.append({
                            'offset': offset,
                            'length': length,
                            'type': ptype,
                            'opcode': opcode,
                            'tx_id': tx_id,
                            'data': packet_data,
                            'payload': payload
                        })
                        offset += length
                        continue
        except:
            pass

        offset += 1

    return packets

with open("/Users/tom.m/Downloads/6D Scan (1).pcapng", 'rb') as f:
    data = f.read()

all_packets = find_all_ptp_packets(data)
print(f"Found {len(all_packets)} valid PTP packets\n")

# Find the MonOpen packet
mon_open_idx = None
for i, pkt in enumerate(all_packets):
    if b'MonOpen' in pkt['payload']:
        mon_open_idx = i
        break

if mon_open_idx is None:
    print("MonOpen not found!")
    exit(1)

print("="*80)
print(f"PTP SEQUENCE STARTING FROM MonOpen (packet #{mon_open_idx+1})")
print("="*80)

# Show 20 packets starting from MonOpen
for i in range(mon_open_idx, min(mon_open_idx + 25, len(all_packets))):
    pkt = all_packets[i]
    type_name = {1: 'CMD', 2: 'DATA', 3: 'RESP'}.get(pkt['type'], '???')

    marker = ""
    desc = ""

    if b'MonOpen' in pkt['payload']:
        marker = "★"
        desc = "MonOpen"
    elif b'MonClose' in pkt['payload']:
        marker = "★"
        desc = "MonClose"
    elif b'MonReadAndGetData' in pkt['payload']:
        marker = "★"
        # Parse address
        try:
            addr = struct.unpack_from('<I', pkt['payload'], 38)[0]
            length = struct.unpack_from('<I', pkt['payload'], 70)[0]
            desc = f"MonReadAndGetData(0x{addr:04x}, {length})"
        except:
            desc = "MonReadAndGetData"
    elif pkt['opcode'] == 0x2001:
        desc = "OK Response"
        # Check for extra params
        if len(pkt['payload']) > 0:
            desc += f" + {len(pkt['payload'])} bytes: {pkt['payload'].hex()}"
    elif pkt['opcode'] == 0x9052 and pkt['type'] == 1:
        desc = "FAPI_TX cmd"
    elif pkt['opcode'] == 0x9053 and pkt['type'] == 1:
        desc = "FAPI_RX cmd"
    elif pkt['opcode'] == 0x9053 and pkt['type'] == 2:
        desc = f"FAPI_RX data ({len(pkt['payload'])} bytes)"
        if len(pkt['payload']) == 10:
            # This is the shutter count!
            try:
                mechanical = struct.unpack_from('<I', pkt['payload'], 0)[0]
                electronic = struct.unpack_from('<I', pkt['payload'], 6)[0]
                desc += f" → Mech:{mechanical:,} + Elec:{electronic:,} = {mechanical+electronic:,}"
            except:
                pass

    print(f"{marker:1s} [{i-mon_open_idx+1:2d}] TX={pkt['tx_id']:3d} | {type_name:4s} 0x{pkt['opcode']:04x} | {desc}")

    # Show hex for small packets
    if len(pkt['data']) <= 24 or (pkt['opcode'] == 0x9053 and pkt['type'] == 2 and len(pkt['payload']) <= 32):
        print(f"        {pkt['data'].hex()}")
