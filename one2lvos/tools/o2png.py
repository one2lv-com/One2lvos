#!/usr/bin/env python3
"""
============================================================================
O2PNG - One2lvOS PNG Steganography & Data Encoding Tool
============================================================================
Hide and retrieve data from PNG images using LSB steganography
Store system state, configurations, and memory snapshots in images
"""

import os
import sys
import json
import struct
import argparse
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  Pillow not installed. Install with: pip install Pillow")

# ANSI colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
MAGENTA = '\033[0;35m'
NC = '\033[0m'


class O2PNG:
    """One2lvOS PNG Steganography Engine"""

    def __init__(self):
        self.version = "1.0.0"
        self.signature = b"O2LV"  # File signature

    def encode(self, data: Dict[Any, Any], output_path: str,
               width: int = 1024, height: int = 64,
               visual: bool = False) -> bool:
        """
        Encode data into a PNG image using LSB steganography

        Args:
            data: Dictionary to encode
            output_path: Output PNG file path
            width: Image width
            height: Image height
            visual: Create visual pattern instead of solid color
        """
        if not PIL_AVAILABLE:
            print(f"{RED}❌ Pillow not available{NC}")
            return False

        try:
            # Add metadata
            data_with_meta = {
                "o2png_version": self.version,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }

            # Serialize to JSON and encode
            json_bytes = json.dumps(data_with_meta, indent=2).encode('utf-8')

            # Create payload: signature + length + data
            length_prefix = struct.pack('<I', len(json_bytes))
            payload = self.signature + length_prefix + json_bytes

            # Check if image is large enough
            max_capacity = width * height * 3  # 3 channels (RGB)
            if len(payload) > max_capacity:
                print(f"{RED}❌ Data too large for image size{NC}")
                print(f"   Data: {len(payload)} bytes, Capacity: {max_capacity} bytes")
                return False

            # Create base image
            if visual:
                img = self._create_visual_image(width, height, data)
            else:
                img = Image.new('RGB', (width, height), color=(13, 2, 32))

            pixels = img.load()

            # Encode data using LSB steganography
            data_index = 0
            for y in range(height):
                for x in range(width):
                    if data_index >= len(payload):
                        break

                    r, g, b = pixels[x, y]

                    # Encode one byte across RGB channels
                    if data_index < len(payload):
                        # Modify LSB of red channel
                        byte_val = payload[data_index]
                        r = (r & 0xFC) | ((byte_val >> 6) & 0x03)
                        g = (g & 0xFC) | ((byte_val >> 4) & 0x03)
                        b = (b & 0xFC) | ((byte_val >> 2) & 0x03)

                        pixels[x, y] = (r, g, b)

                        # Store remaining bits in next pixel if needed
                        if x + 1 < width:
                            r2, g2, b2 = pixels[x + 1, y]
                            r2 = (r2 & 0xFC) | (byte_val & 0x03)
                            pixels[x + 1, y] = (r2, g2, b2)

                        data_index += 1

                if data_index >= len(payload):
                    break

            # Save image
            img.save(output_path, 'PNG', compress_level=1)

            print(f"{GREEN}✅ Data encoded successfully{NC}")
            print(f"   Output: {output_path}")
            print(f"   Size: {len(payload)} bytes encoded in {width}x{height} image")
            print(f"   Capacity used: {(len(payload)/max_capacity)*100:.2f}%")

            return True

        except Exception as e:
            print(f"{RED}❌ Encoding failed: {e}{NC}")
            return False

    def decode(self, input_path: str, output_json: Optional[str] = None) -> Optional[Dict]:
        """
        Decode data from a PNG image

        Args:
            input_path: Input PNG file path
            output_json: Optional output JSON file path

        Returns:
            Decoded data dictionary or None
        """
        if not PIL_AVAILABLE:
            print(f"{RED}❌ Pillow not available{NC}")
            return None

        try:
            img = Image.open(input_path)
            pixels = img.load()
            width, height = img.size

            # Extract signature first
            signature = bytearray()
            for i in range(4):  # 4 bytes for signature
                if i >= width:
                    break
                r, g, b = pixels[i, 0]
                byte_val = ((r & 0x03) << 6) | ((g & 0x03) << 4) | ((b & 0x03) << 2)
                if i + 1 < width:
                    r2, g2, b2 = pixels[i + 1, 0]
                    byte_val |= (r2 & 0x03)
                signature.append(byte_val)

            if bytes(signature) != self.signature:
                print(f"{YELLOW}⚠️  Not an O2PNG encoded image (no signature found){NC}")
                return None

            # Extract length
            length_bytes = bytearray()
            for i in range(4, 8):  # 4 bytes for length
                x = i % width
                y = i // width
                r, g, b = pixels[x, y]
                byte_val = ((r & 0x03) << 6) | ((g & 0x03) << 4) | ((b & 0x03) << 2)
                if x + 1 < width:
                    r2, g2, b2 = pixels[x + 1, y]
                    byte_val |= (r2 & 0x03)
                length_bytes.append(byte_val)

            data_length = struct.unpack('<I', bytes(length_bytes))[0]

            print(f"{CYAN}🔍 Decoding O2PNG image...{NC}")
            print(f"   Signature: {bytes(signature).decode('latin-1')}")
            print(f"   Data length: {data_length} bytes")

            # Extract data
            data_bytes = bytearray()
            pixel_index = 8  # Skip signature and length

            for i in range(data_length):
                x = pixel_index % width
                y = pixel_index // width

                if y >= height:
                    break

                r, g, b = pixels[x, y]
                byte_val = ((r & 0x03) << 6) | ((g & 0x03) << 4) | ((b & 0x03) << 2)

                if x + 1 < width:
                    r2, g2, b2 = pixels[x + 1, y]
                    byte_val |= (r2 & 0x03)

                data_bytes.append(byte_val)
                pixel_index += 1

            # Decode JSON
            json_str = bytes(data_bytes).decode('utf-8')
            data = json.loads(json_str)

            print(f"{GREEN}✅ Data decoded successfully{NC}")
            print(f"   O2PNG Version: {data.get('o2png_version', 'unknown')}")
            print(f"   Timestamp: {data.get('timestamp', 'unknown')}")

            # Save to file if requested
            if output_json:
                with open(output_json, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"   Saved to: {output_json}")

            return data

        except Exception as e:
            print(f"{RED}❌ Decoding failed: {e}{NC}")
            return None

    def _create_visual_image(self, width: int, height: int, data: Dict) -> Image:
        """Create a visually interesting base image"""
        img = Image.new('RGB', (width, height))
        pixels = img.load()

        # Create gradient pattern based on data hash
        data_hash = hash(json.dumps(data, sort_keys=True))

        for y in range(height):
            for x in range(width):
                # Create color based on position and data hash
                r = (x * 255 // width + data_hash) % 256
                g = (y * 255 // height + data_hash // 2) % 256
                b = ((x + y) * 255 // (width + height) + data_hash // 3) % 256

                # Darken for aesthetics
                r = r // 4 + 13
                g = g // 4 + 2
                b = b // 4 + 32

                pixels[x, y] = (r, g, b)

        return img

    def encode_file(self, file_path: str, output_path: str) -> bool:
        """Encode any file into a PNG image"""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Encode as base64 to ensure JSON compatibility
            encoded = base64.b64encode(file_data).decode('utf-8')

            data = {
                "filename": os.path.basename(file_path),
                "size": len(file_data),
                "mime_type": self._guess_mime_type(file_path),
                "content": encoded
            }

            return self.encode(data, output_path, width=2048, height=128)

        except Exception as e:
            print(f"{RED}❌ File encoding failed: {e}{NC}")
            return False

    def decode_file(self, input_path: str, output_dir: str = ".") -> bool:
        """Decode a file from a PNG image"""
        try:
            data = self.decode(input_path)
            if not data or 'data' not in data:
                return False

            file_data = data['data']
            filename = file_data.get('filename', 'decoded_file')
            content = file_data.get('content', '')

            # Decode base64
            decoded_bytes = base64.b64decode(content)

            # Write to file
            output_path = os.path.join(output_dir, filename)
            with open(output_path, 'wb') as f:
                f.write(decoded_bytes)

            print(f"{GREEN}✅ File extracted: {output_path}{NC}")
            print(f"   Size: {len(decoded_bytes)} bytes")

            return True

        except Exception as e:
            print(f"{RED}❌ File decoding failed: {e}{NC}")
            return False

    def _guess_mime_type(self, file_path: str) -> str:
        """Guess MIME type from file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.html': 'text/html',
            '.css': 'text/css',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.zip': 'application/zip',
        }
        return mime_types.get(ext, 'application/octet-stream')

    def info(self, input_path: str) -> None:
        """Display information about a PNG image"""
        if not PIL_AVAILABLE:
            print(f"{RED}❌ Pillow not available{NC}")
            return

        try:
            img = Image.open(input_path)
            width, height = img.size
            mode = img.mode

            print(f"{CYAN}📊 Image Information{NC}")
            print(f"   File: {input_path}")
            print(f"   Dimensions: {width}x{height}")
            print(f"   Mode: {mode}")
            print(f"   Size: {os.path.getsize(input_path)} bytes")
            print(f"   Max capacity: {width * height * 3} bytes")

            # Try to detect O2PNG encoding
            pixels = img.load()
            signature = bytearray()
            for i in range(4):
                if i >= width:
                    break
                r, g, b = pixels[i, 0]
                byte_val = ((r & 0x03) << 6) | ((g & 0x03) << 4) | ((b & 0x03) << 2)
                if i + 1 < width:
                    r2, g2, b2 = pixels[i + 1, 0]
                    byte_val |= (r2 & 0x03)
                signature.append(byte_val)

            if bytes(signature) == self.signature:
                print(f"{GREEN}   ✅ O2PNG encoded data detected{NC}")
            else:
                print(f"{YELLOW}   ⚠️  No O2PNG encoding detected{NC}")

        except Exception as e:
            print(f"{RED}❌ Error: {e}{NC}")


def main():
    parser = argparse.ArgumentParser(
        description='O2PNG - One2lvOS PNG Steganography Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Encode JSON data
  o2png.py encode --data '{"key":"value"}' --output data.png

  # Encode from JSON file
  o2png.py encode --input config.json --output config.png

  # Decode PNG to view data
  o2png.py decode --input data.png

  # Decode and save to JSON
  o2png.py decode --input data.png --output decoded.json

  # Encode any file
  o2png.py encode-file --input document.pdf --output doc.png

  # Decode file from PNG
  o2png.py decode-file --input doc.png --output-dir ./extracted

  # Get PNG info
  o2png.py info --input image.png
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Encode command
    encode_parser = subparsers.add_parser('encode', help='Encode data to PNG')
    encode_parser.add_argument('--data', type=str, help='JSON data string')
    encode_parser.add_argument('--input', type=str, help='Input JSON file')
    encode_parser.add_argument('--output', type=str, required=True, help='Output PNG file')
    encode_parser.add_argument('--width', type=int, default=1024, help='Image width')
    encode_parser.add_argument('--height', type=int, default=64, help='Image height')
    encode_parser.add_argument('--visual', action='store_true', help='Create visual pattern')

    # Decode command
    decode_parser = subparsers.add_parser('decode', help='Decode data from PNG')
    decode_parser.add_argument('--input', type=str, required=True, help='Input PNG file')
    decode_parser.add_argument('--output', type=str, help='Output JSON file')

    # Encode file command
    encode_file_parser = subparsers.add_parser('encode-file', help='Encode file to PNG')
    encode_file_parser.add_argument('--input', type=str, required=True, help='Input file')
    encode_file_parser.add_argument('--output', type=str, required=True, help='Output PNG file')

    # Decode file command
    decode_file_parser = subparsers.add_parser('decode-file', help='Decode file from PNG')
    decode_file_parser.add_argument('--input', type=str, required=True, help='Input PNG file')
    decode_file_parser.add_argument('--output-dir', type=str, default='.', help='Output directory')

    # Info command
    info_parser = subparsers.add_parser('info', help='Show PNG information')
    info_parser.add_argument('--input', type=str, required=True, help='Input PNG file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    o2png = O2PNG()

    if args.command == 'encode':
        # Get data
        if args.data:
            data = json.loads(args.data)
        elif args.input:
            with open(args.input, 'r') as f:
                data = json.load(f)
        else:
            print(f"{RED}❌ Provide --data or --input{NC}")
            return

        o2png.encode(data, args.output, args.width, args.height, args.visual)

    elif args.command == 'decode':
        data = o2png.decode(args.input, args.output)
        if data and not args.output:
            print(f"\n{CYAN}Decoded Data:{NC}")
            print(json.dumps(data, indent=2))

    elif args.command == 'encode-file':
        o2png.encode_file(args.input, args.output)

    elif args.command == 'decode-file':
        o2png.decode_file(args.input, args.output_dir)

    elif args.command == 'info':
        o2png.info(args.input)


if __name__ == "__main__":
    print(f"{MAGENTA}╔══════════════════════════════════════════════════════════════════════╗{NC}")
    print(f"{MAGENTA}║                                                                      ║{NC}")
    print(f"{MAGENTA}║       O2PNG - One2lvOS PNG Steganography Tool v1.0.0                ║{NC}")
    print(f"{MAGENTA}║                                                                      ║{NC}")
    print(f"{MAGENTA}╚══════════════════════════════════════════════════════════════════════╝{NC}")
    print()
    main()
