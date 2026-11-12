"""Bundled test images, generated with the stdlib only (zlib PNG writer and
a 5x7 bitmap font), so the judge's vision and OCR batteries have exact
ground truth and need no downloads or image libraries.

Run `python3 -m nimlab.assets` to (re)write assets/vision_test.png and
assets/ocr_test.png.
"""

import os
import struct
import zlib

from . import config

ASSETS_DIR = os.path.join(config.PROJECT_DIR, "assets")

# 5x7 glyphs, one string per row, '#' = ink.
FONT = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    " ": ["....."] * 7,
    ":": [".....", "..#..", "..#..", ".....", "..#..", "..#..", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", "..#..", "..#.."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
}

WHITE, BLACK = (255, 255, 255), (0, 0, 0)
RED, BLUE, GREEN = (220, 30, 30), (30, 60, 220), (30, 170, 60)

# Ground truth for the bundled images (the judge battery reads these).
OCR_LINES = ["NVIDIA TEST LAB 2026", "QUILL READS SEVEN LINES", "CER CHECK: A1 B2 C3", "FOX-42 JUMPS."]
OCR_TEXT = "\n".join(OCR_LINES)
VISION_QA = [
    {"q": "How many red squares are in the image? Answer with a single number.", "accept": ["3", "three"]},
    {"q": "What color is the circle? Answer with one word.", "accept": ["blue"]},
    {"q": "What shape is green? Answer with one word.", "accept": ["triangle"]},
    {"q": "What number is written at the bottom of the image? Answer with the number only.", "accept": ["42", "forty-two", "forty two"]},
]


class Canvas:
    def __init__(self, w, h, bg=WHITE):
        self.w, self.h = w, h
        self.px = [[bg] * w for _ in range(h)]

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(max(0, y0), min(self.h, y1)):
            row = self.px[y]
            for x in range(max(0, x0), min(self.w, x1)):
                row[x] = c

    def circle(self, cx, cy, r, c):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, c)

    def triangle(self, apex_x, top, base_half, bottom, c):
        height = bottom - top
        for y in range(top, bottom + 1):
            half = int(base_half * (y - top) / max(1, height))
            for x in range(apex_x - half, apex_x + half + 1):
                self.set(x, y, c)

    def text(self, x, y, s, scale=4, c=BLACK):
        for ch in s.upper():
            glyph = FONT.get(ch, FONT[" "])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == "#":
                        self.rect(x + gx * scale, y + gy * scale, x + (gx + 1) * scale, y + (gy + 1) * scale, c)
            x += 6 * scale

    def png(self):
        raw = b"".join(b"\x00" + bytes(v for p in row for v in p) for row in self.px)

        def chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def vision_png():
    c = Canvas(480, 320)
    for i in range(3):
        c.rect(40 + i * 140, 30, 40 + i * 140 + 80, 110, RED)
    c.circle(110, 190, 45, BLUE)
    c.triangle(370, 145, 55, 235, GREEN)
    c.text(204, 260, "42", scale=6)
    return c.png()


def ocr_png():
    scale = 4
    width = max(len(line) for line in OCR_LINES) * 6 * scale + 40
    c = Canvas(width, len(OCR_LINES) * 10 * scale + 30)
    for i, line in enumerate(OCR_LINES):
        c.text(20, 15 + i * 10 * scale, line, scale=scale)
    return c.png()


def ensure_assets():
    """Write the bundled images if missing; returns (vision_path, ocr_path)."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    paths = []
    for name, maker in (("vision_test.png", vision_png), ("ocr_test.png", ocr_png)):
        path = os.path.join(ASSETS_DIR, name)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(maker())
        paths.append(path)
    return tuple(paths)


if __name__ == "__main__":
    for p in ensure_assets():
        print(p)
