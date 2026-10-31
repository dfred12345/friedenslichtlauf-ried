from base64 import b64encode
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw
import qrcode
from qrcode.constants import ERROR_CORRECT_H

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
URL = "https://friedenslicht.run/"
BORDER = 4
BOX = 100

qr = qrcode.QRCode(
    version=None,
    error_correction=ERROR_CORRECT_H,
    box_size=BOX,
    border=BORDER,
)
qr.add_data(URL)
qr.make(fit=True)
matrix = qr.get_matrix()
modules = len(matrix)
size = modules * BOX

# High-resolution PNG with a protected white logo field.
image = Image.new("RGB", (size, size), "white")
draw = ImageDraw.Draw(image)
for row, values in enumerate(matrix):
    for col, active in enumerate(values):
        if active:
            draw.rectangle(
                (col * BOX, row * BOX, (col + 1) * BOX - 1, (row + 1) * BOX - 1),
                fill="#10264f",
            )

field_modules = 7
field_size = field_modules * BOX
field_left = (size - field_size) // 2
field_top = (size - field_size) // 2
draw.rounded_rectangle(
    (field_left, field_top, field_left + field_size, field_top + field_size),
    radius=BOX // 2,
    fill="white",
)

logo = Image.open(ROOT / "assets" / "runner-icon.png").convert("RGBA")
logo_max_width = field_size - int(1.8 * BOX)
logo_max_height = field_size - BOX
scale = min(logo_max_width / logo.width, logo_max_height / logo.height)
logo = logo.resize(
    (round(logo.width * scale), round(logo.height * scale)),
    Image.Resampling.LANCZOS,
)
logo_left = (size - logo.width) // 2
logo_top = (size - logo.height) // 2
image.paste(logo, (logo_left, logo_top), logo)
png_path = OUT / "qr-code-friedenslicht-run-mit-logo.png"
image.save(png_path, "PNG", dpi=(600, 600), optimize=True)

# Vector SVG QR modules; only the small supplied runner mark is embedded as PNG.
buffer = BytesIO()
logo.save(buffer, "PNG", optimize=True)
logo_data = b64encode(buffer.getvalue()).decode("ascii")
rects = []
for row, values in enumerate(matrix):
    for col, active in enumerate(values):
        if active:
            rects.append(f'<rect x="{col}" y="{row}" width="1" height="1"/>')
logo_x = modules / 2 - (logo.width / BOX) / 2
logo_y = modules / 2 - (logo.height / BOX) / 2
svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="100mm" height="100mm" viewBox="0 0 {modules} {modules}" role="img"
     aria-label="QR-Code zu {URL}">
  <rect width="{modules}" height="{modules}" fill="#ffffff"/>
  <g fill="#10264f" shape-rendering="crispEdges">{''.join(rects)}</g>
  <rect x="{(modules - field_modules) / 2}" y="{(modules - field_modules) / 2}"
        width="{field_modules}" height="{field_modules}" rx="0.5" fill="#ffffff"/>
  <image x="{logo_x}" y="{logo_y}" width="{logo.width / BOX}" height="{logo.height / BOX}"
         preserveAspectRatio="xMidYMid meet" xlink:href="data:image/png;base64,{logo_data}"/>
</svg>
'''
svg_path = OUT / "qr-code-friedenslicht-run-mit-logo.svg"
svg_path.write_text(svg, encoding="utf-8")

print(f"URL={URL}")
print(f"matrix={modules}x{modules}, png={size}x{size}px")
print(png_path)
print(svg_path)
