#!/usr/bin/env python3
"""
============================================================================
O2PNG SIMPLE - One2lvOS PNG Steganography (Simplified LSB)
============================================================================
Simple and reliable LSB steganography for One2lvOS
"""

import os
import json
import struct
import base64
from datetime import datetime
from PIL import Image

SIGNATURE = b"O2LV"
RED = '\033[0;31m'
GREEN = '\033[0;32m'
CYAN = '\033[0;36m'
MAGENTA = '\033[0;35m'
NC = '\033[0m'


def encode_to_png(data_dict, output_path, width=1024, height=64):
    """Encode JSON data to PNG using simple LSB"""
    # Add metadata
    full_data = {
        "o2png_version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "data": data_dict
    }

    # Serialize
    json_bytes = json.dumps(full_data, indent=2).encode('utf-8')
    payload = SIGNATURE + struct.pack('<I', len(json_bytes)) + json_bytes

    # Check capacity
    capacity = width * height
    if len(payload) > capacity:
        print(f"{RED}❌ Data too large: {len(payload)} bytes > {capacity} capacity{NC}")
        return False

    # Create image
    img = Image.new('RGB', (width, height), color=(13, 2, 32))
    pixels = img.load()

    # Encode: one byte per pixel in LSB of red channel
    idx = 0
    for y in range(height):
        for x in range(width):
            if idx < len(payload):
                r, g, b = pixels[x, y]
                # Store byte in LSB of red channel
                r = (r & 0xFE) | ((payload[idx] >> 7) & 1)
                g = (g & 0xFE) | ((payload[idx] >> 6) & 1)
                b = (b & 0xFE) | ((payload[idx] >> 5) & 1)

                pixels[x, y] = (r, g, b)

                # Continue with next pixel for remaining bits
                if x + 1 < width:
                    r2, g2, b2 = pixels[x + 1, y]
                    r2 = (r2 & 0xFE) | ((payload[idx] >> 4) & 1)
                    g2 = (g2 & 0xFE) | ((payload[idx] >> 3) & 1)
                    b2 = (b2 & 0xFE) | ((payload[idx] >> 2) & 1)
                    pixels[x + 1, y] = (r2, g2, b2)

                if x + 2 < width:
                    r3, g3, b3 = pixels[x + 2, y]
                    r3 = (r3 & 0xFE) | ((payload[idx] >> 1) & 1)
                    g3 = (g3 & 0xFE) | (payload[idx] & 1)
                    pixels[x + 2, y] = (r3, g3, b3)

                idx += 1

    img.save(output_path, 'PNG')
    print(f"{GREEN}✅ Encoded {len(payload)} bytes to {output_path}{NC}")
    print(f"   Capacity used: {(len(payload)/capacity)*100:.2f}%")
    return True


def decode_from_png(input_path):
    """Decode JSON data from PNG using simple LSB"""
    img = Image.open(input_path)
    pixels = img.load()
    width, height = img.size

    # Decode signature (4 bytes)
    sig_bytes = bytearray()
    for i in range(4):
        x_base = i * 3
        y = 0
        byte_val = 0

        for bit_idx in range(8):
            x = x_base + (bit_idx // 3)
            if x >= width:
                break
            r, g, b = pixels[x, y]
            channel = [r, g, b][bit_idx % 3]
            byte_val = (byte_val << 1) | (channel & 1)

        sig_bytes.append(byte_val)

    if bytes(sig_bytes) != SIGNATURE:
        print(f"{CYAN}⚠️  No O2PNG signature found{NC}")
        return None

    # Decode length (4 bytes)
    len_bytes = bytearray()
    for i in range(4):
        x_base = (4 + i) * 3
        y = 0
        byte_val = 0

        for bit_idx in range(8):
            x = x_base + (bit_idx // 3)
            if x >= width:
                break

            if x >= width:
                y += 1
                x = x % width

            r, g, b = pixels[x, y]
            channel = [r, g, b][bit_idx % 3]
            byte_val = (byte_val << 1) | (channel & 1)

        len_bytes.append(byte_val)

    data_len = struct.unpack('<I', bytes(len_bytes))[0]
    print(f"{CYAN}🔍 Found O2PNG data: {data_len} bytes{NC}")

    # Decode data
    data_bytes = bytearray()
    for i in range(data_len):
        x_base = (8 + i) * 3
        y = x_base // width
        x_base = x_base % width
        byte_val = 0

        for bit_idx in range(8):
            x = x_base + (bit_idx // 3)
            if x >= width:
                y += 1
                x = x % width

            if y >= height:
                break

            r, g, b = pixels[x, y]
            channel = [r, g, b][bit_idx % 3]
            byte_val = (byte_val << 1) | (channel & 1)

        data_bytes.append(byte_val)

    # Decode JSON
    json_str = bytes(data_bytes).decode('utf-8')
    data = json.loads(json_str)

    print(f"{GREEN}✅ Decoded successfully{NC}")
    return data


# Quick CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(f"{MAGENTA}O2PNG Simple - Quick Test Tool{NC}")
        print("Usage:")
        print("  Encode: python3 o2png_simple.py encode input.json output.png")
        print("  Decode: python3 o2png_simple.py decode input.png")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "encode":
        with open(sys.argv[2], 'r') as f:
            data = json.load(f)
        encode_to_png(data, sys.argv[3])

    elif cmd == "decode":
        data = decode_from_png(sys.argv[2])
        if data:
            print(json.dumps(data, indent=2))
