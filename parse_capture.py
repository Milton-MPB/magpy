#!/usr/bin/env python3
"""Parse pcapng to extract PTP/USB command sequence."""
import struct

def read_pcapng(filename):
    """Read pcapng and extract USB bulk/interrupt packets."""
    with open(filename, 'rb') as f:
        data = f.read()

    packets = []
    offset = 0

    while offset < len(data):
        # Look for USB URB structures or PTP command/data markers
        # PTP command packets start with length + 0x0001 (CMD) or 0x0002 (DATA)

        # Search for PTP packet signatures
        if offset + 12 > len(data):
            break

        # Try to find PTP container headers (length, type, opcode, tx_id)
        try:
            length, ptype = struct.unpack_from('<IH', data, offset)

            # Valid PTP packet types: 1 (CMD), 2 (DATA), 3 (RESP)
            if ptype in (0x0001, 0x0002, 0x0003) and 12 <= length <= 8192:
                opcode, tx_id = struct.unpack_from('<HI', data, offset + 6)
                payload = data[offset+12:offset+length]

                ptype_name = {0x0001: 'CMD', 0x0002: 'DATA', 0x0003: 'RESP'}.get(ptype, 'UNK')

                packets.append({
                    'offset': offset,
                    'length': length,
                    'type': ptype,
                    'type_name': ptype_name,
                    'opcode': opcode,
                    'tx_id': tx_id,
                    'payload': payload,
                    'raw': data[offset:offset+length]
                })

        except:
            pass

        offset += 1

    return packets

def analyze_packets(packets):
    """Analyze PTP packets and show command flow."""
    print("="*80)
    print("PTP COMMAND SEQUENCE FROM CAPTURE")
    print("="*80)

    for i, pkt in enumerate(packets):
        print(f"\n[{i+1}] Offset: 0x{pkt['offset']:06x}")
        print(f"    Type: {pkt['type_name']} (0x{pkt['type']:04x})")
        print(f"    Opcode: 0x{pkt['opcode']:04x}")
        print(f"    TX ID: {pkt['tx_id']}")
        print(f"    Length: {pkt['length']} bytes")

        # Decode specific opcodes
        if pkt['opcode'] == 0x9052:  # FAPI_TX
            print(f"    → FAPI_TX (Canon command)")
            # Try to find command string
            payload = pkt['payload']
            if len(payload) > 0:
                # Look for null-terminated string
                null_idx = payload.find(b'\x00')
                if null_idx > 0:
                    cmd_name = payload[:null_idx].decode('ascii', errors='ignore')
                    print(f"       Command: '{cmd_name}'")

                    if cmd_name == "MonReadAndGetData" and len(payload) >= 50:
                        # Parse address and length
                        try:
                            # Structure varies, look for the address/length params
                            for offset in range(20, min(len(payload)-8, 60)):
                                addr = struct.unpack_from('<I', payload, offset)[0]
                                if 0x1000 <= addr <= 0x3000:  # Likely memory address
                                    length = struct.unpack_from('<I', payload, offset+16)[0]
                                    if 1 <= length <= 100:
                                        print(f"       → Address: 0x{addr:04x}, Length: {length}")
                                        break
                        except:
                            pass

        elif pkt['opcode'] == 0x9053:  # FAPI_RX
            print(f"    → FAPI_RX (Canon response read)")

        elif pkt['opcode'] == 0x2001:  # OK response
            print(f"    ← OK Response")

        elif pkt['opcode'] == 0x1002:
            print(f"    → OpenSession")

        elif pkt['opcode'] == 0x1003:
            print(f"    → CloseSession")

        elif pkt['opcode'] == 0x1016:
            print(f"    → SetDevicePropValue")

        # Show hex dump of first 64 bytes
        if len(pkt['payload']) > 0:
            hex_dump = pkt['payload'][:64].hex()
            print(f"    Payload preview: {hex_dump[:128]}{'...' if len(hex_dump) > 128 else ''}")

if __name__ == '__main__':
    import sys

    filename = "/Users/tom.m/Downloads/6D Scan (1).pcapng"
    print(f"Parsing: {filename}\n")

    packets = read_pcapng(filename)
    print(f"Found {len(packets)} potential PTP packets\n")

    analyze_packets(packets)

    # Also save raw packet data for inspection
    print("\n" + "="*80)
    print("SAVING PACKET DETAILS")
    print("="*80)

    with open("/Users/tom.m/Documents/MagPy/capture_packets.txt", "w") as f:
        for i, pkt in enumerate(packets):
            f.write(f"\n{'='*60}\n")
            f.write(f"Packet {i+1}\n")
            f.write(f"Offset: 0x{pkt['offset']:06x}\n")
            f.write(f"Type: {pkt['type_name']} Opcode: 0x{pkt['opcode']:04x} TX: {pkt['tx_id']}\n")
            f.write(f"Raw hex:\n{pkt['raw'].hex()}\n")

    print(f"Detailed packet dump saved to: /Users/tom.m/Documents/MagPy/capture_packets.txt")
