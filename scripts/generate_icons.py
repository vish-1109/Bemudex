#!/usr/bin/env python3
"""
Generate standard FreeDesktop hicolor icons and scalable SVG
from the master 256x256 application icon.
"""
import os
import sys
import base64
from PIL import Image

SIZES = [16, 22, 24, 32, 48, 64, 96, 128, 256, 512]

def generate_icons(repo_root: str):
    master_path = os.path.join(repo_root, "assets", "bemudex_256.png")
    if not os.path.exists(master_path):
        print(f"Error: master icon not found at {master_path}", file=sys.stderr)
        sys.exit(1)

    icons_dir = os.path.join(repo_root, "assets", "icons")
    os.makedirs(icons_dir, exist_ok=True)

    base_img = Image.open(master_path)

    for size in SIZES:
        size_dir = os.path.join(icons_dir, f"{size}x{size}")
        os.makedirs(size_dir, exist_ok=True)
        out_path = os.path.join(size_dir, "org.bemudex.Bemudex.png")
        if size == 256:
            base_img.save(out_path, format="PNG", optimize=True)
        else:
            resized = base_img.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(out_path, format="PNG", optimize=True)
        print(f"Generated {size}x{size} -> {out_path} ({os.path.getsize(out_path)} bytes)")

    scalable_dir = os.path.join(icons_dir, "scalable")
    os.makedirs(scalable_dir, exist_ok=True)
    svg_path = os.path.join(scalable_dir, "org.bemudex.Bemudex.svg")

    with open(master_path, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode("ascii")

    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="256" height="256" viewBox="0 0 256 256">
  <image width="256" height="256" xlink:href="data:image/png;base64,{b64_data}" href="data:image/png;base64,{b64_data}"/>
</svg>
'''
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated scalable SVG -> {svg_path} ({os.path.getsize(svg_path)} bytes)")

if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    generate_icons(repo_root)
