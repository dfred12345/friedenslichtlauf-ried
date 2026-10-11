from pathlib import Path

from PIL import Image
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from reportlab.lib.colors import PCMYKColor, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

MM = 72 / 25.4
W_MM, H_MM = 3000, 800
W, H = W_MM * MM, H_MM * MM
OUT = Path(__file__).resolve().parent

NAVY = PCMYKColor(95, 83, 36, 36)
BLUE = PCMYKColor(83, 69, 31, 14)
ORANGE = PCMYKColor(13, 72, 100, 3)
GOLD = PCMYKColor(3, 41, 84, 0)
PAPER = PCMYKColor(3, 3, 5, 0)
MUTED = PCMYKColor(56, 46, 31, 10)
LIGHT_ORANGE = PCMYKColor(3, 25, 55, 0)

pdfmetrics.registerFont(TTFont("FLM-Regular", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("FLM-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))


def mm(value):
    return value * MM


def y_top(value):
    return H - mm(value)


def rect_top(c, x, top, width, height, color):
    c.setFillColor(color)
    c.rect(mm(x), y_top(top + height), mm(width), mm(height), stroke=0, fill=1)


def round_rect_top(c, x, top, width, height, radius, color):
    c.setFillColor(color)
    c.roundRect(mm(x), y_top(top + height), mm(width), mm(height), mm(radius), stroke=0, fill=1)


def text_fit(c, text, x, top, max_width, size_mm, color, font="FLM-Bold", align="left"):
    size = mm(size_mm)
    while pdfmetrics.stringWidth(text, font, size) > mm(max_width) and size > mm(7):
        size *= 0.97
    c.setFont(font, size)
    c.setFillColor(color)
    baseline = y_top(top) - size * 0.82
    if align == "center":
        c.drawCentredString(mm(x), baseline, text)
    elif align == "right":
        c.drawRightString(mm(x), baseline, text)
    else:
        c.drawString(mm(x), baseline, text)
    return size


def prepare_photo(name, width_mm, height_mm, focus=0.5):
    source = Image.open(OUT / "source-photo.jpg").convert("RGB")
    ratio = width_mm / height_mm
    if source.width / source.height > ratio:
        new_w = round(source.height * ratio)
        left = round((source.width - new_w) * focus)
        left = max(0, min(left, source.width - new_w))
        source = source.crop((left, 0, left + new_w, source.height))
    else:
        new_h = round(source.width / ratio)
        top = max(0, (source.height - new_h) // 2)
        source = source.crop((0, top, source.width, top + new_h))
    path = OUT / name
    source.save(path, "JPEG", quality=95, subsampling=0)
    return path


def prepare_runner():
    runner = Image.open(OUT / "source-runner.png").convert("RGB")
    alpha = Image.new("L", runner.size, 0)
    src, dst = runner.load(), alpha.load()
    assert src is not None and dst is not None
    for yy in range(runner.height):
        for xx in range(runner.width):
            red, green, blue = src[xx, yy]
            score = red - max(green, blue)
            if red > 130 and 45 < green < 180 and blue < 130 and score > 35:
                dst[xx, yy] = min(255, max(0, int((score - 25) * 3.2)))
    bbox = alpha.getbbox()
    if bbox is not None:
        left, top, right, bottom = bbox
        crop = (int(left), int(top), int(right), int(bottom))
        runner, alpha = runner.crop(crop), alpha.crop(crop)
    image = Image.new("RGBA", runner.size, (207, 103, 24, 0))
    image.putalpha(alpha)
    image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
    path = OUT / "runner-variants-print.png"
    image.save(path)
    return path


def draw_qr(c, url, x, top, size, dark=NAVY):
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=1, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    module = mm(size) / len(matrix)
    c.setFillColor(white)
    c.roundRect(mm(x), y_top(top + size), mm(size), mm(size), mm(10), stroke=0, fill=1)
    c.setFillColor(dark)
    for row, values in enumerate(matrix):
        for col, active in enumerate(values):
            if active:
                c.rect(mm(x) + col * module, y_top(top) - (row + 1) * module, module + 0.15, module + 0.15, stroke=0, fill=1)


def draw_logo(c, runner_path, x, top, width, height, inverse=False):
    fill = NAVY if inverse else white
    c.setFillColor(fill)
    c.ellipse(mm(x), y_top(top + height), mm(x + width), y_top(top), stroke=0, fill=1)
    c.drawImage(ImageReader(str(runner_path)), mm(x + 26), y_top(top + height - 38), width=mm(105), height=mm(155), preserveAspectRatio=True, anchor="c", mask="auto")
    text_fit(c, "FRIEDENS", x + 130, top + 58, width - 170, 30, ORANGE)
    text_fit(c, "LICHT", x + 130, top + 105, width - 170, 38, ORANGE, font="FLM-Regular")
    text_fit(c, "MARATHON", x + 50, top + 176, width - 100, 39, NAVY if not inverse else white)


def route_pill(c, x, top, width, title, detail, dark=False):
    bg = NAVY if dark else white
    primary = white if dark else NAVY
    secondary = GOLD if dark else ORANGE
    round_rect_top(c, x, top, width, 78, 39, bg)
    text_fit(c, title, x + 31, top + 20, width * 0.49, 22, primary)
    text_fit(c, detail, x + width - 31, top + 25, width * 0.46, 15, secondary, align="right")


def base_canvas(filename, title):
    path = OUT / filename
    c = canvas.Canvas(str(path), pagesize=(W, H), pageCompression=1)
    c.setTitle(title)
    c.setAuthor("Naturfreunde Ried im Traunkreis")
    c.setSubject("Druckvorlage 3000 × 800 mm, Querformat")
    return c, path


def variant_a(runner_path):
    c, path = base_canvas("friedenslicht-marathon-plakat-2026-3000x800mm-vorschlag-a.pdf", "Friedenslicht-Marathon 2026 – Vorschlag A Wellenlicht")
    rect_top(c, 0, 0, 3000, 800, PAPER)
    photo = prepare_photo("poster-photo-variant-a.jpg", 980, 800, focus=0.38)
    c.saveState()
    clip = c.beginPath()
    clip.moveTo(0, 0)
    clip.lineTo(mm(925), 0)
    clip.curveTo(mm(1110), mm(175), mm(825), mm(345), mm(980), mm(800))
    clip.lineTo(0, mm(800))
    clip.close()
    c.clipPath(clip, stroke=0, fill=0)
    c.drawImage(ImageReader(str(photo)), 0, 0, width=mm(980), height=H)
    c.setFillColorRGB(0.03, 0.04, 0.08, alpha=0.26)
    c.rect(0, 0, mm(1030), H, stroke=0, fill=1)
    c.restoreState()
    draw_logo(c, runner_path, 78, 75, 660, 430)
    text_fit(c, "GEMEINSAM LICHT BRINGEN.", 115, 585, 700, 29, white)

    text_fit(c, "SONNTAG", 1040, 70, 760, 26, ORANGE)
    text_fit(c, "13.", 1030, 120, 265, 128, NAVY)
    text_fit(c, "DEZEMBER", 1310, 138, 500, 57, NAVY)
    text_fit(c, "2026", 1310, 244, 500, 69, ORANGE)
    round_rect_top(c, 1030, 366, 850, 220, 60, NAVY)
    text_fit(c, "15:00 UHR", 1080, 400, 750, 58, GOLD)
    text_fit(c, "GEMEINDEPLATZ · RIED IM TRAUNKREIS", 1080, 500, 750, 24, white)

    route_pill(c, 1940, 76, 485, "LAUFEN", "CA. 11,2 KM")
    route_pill(c, 2455, 76, 485, "KURZ LAUFEN", "6 KM")
    route_pill(c, 1940, 180, 485, "WALKEN", "CA. 8,2 KM")
    route_pill(c, 2455, 180, 485, "LICHTERZUG", "500 M")
    round_rect_top(c, 1940, 300, 1000, 126, 45, LIGHT_ORANGE)
    text_fit(c, "6-KM-EINSTIEG", 1980, 330, 280, 19, NAVY)
    text_fit(c, "16:30 · WEIGERSDORFER KIRCHE", 2900, 330, 570, 18, NAVY, align="right")

    # Kleiner, einziger QR-Code
    draw_qr(c, "https://friedenslicht.run/", 2665, 500, 150)
    text_fit(c, "INFOS & ANMELDUNG", 2580, 666, 320, 16, NAVY, align="center")
    text_fit(c, "FRIEDENSLICHT.RUN", 2900, 720, 810, 22, ORANGE, align="right")

    # Sanfte orange Lichtspur
    c.setStrokeColor(ORANGE)
    c.setLineWidth(mm(13))
    p = c.beginPath(); p.moveTo(mm(860), mm(40)); p.curveTo(mm(1500), mm(140), mm(1900), mm(10), mm(2570), mm(70)); c.drawPath(p, stroke=1, fill=0)
    c.showPage(); c.save(); return path


def variant_b(runner_path):
    c, path = base_canvas("friedenslicht-marathon-plakat-2026-3000x800mm-vorschlag-b.pdf", "Friedenslicht-Marathon 2026 – Vorschlag B Lichtspur")
    rect_top(c, 0, 0, 3000, 800, NAVY)
    photo = prepare_photo("poster-photo-variant-b.jpg", 1320, 800, focus=0.62)
    c.saveState()
    clip = c.beginPath()
    clip.moveTo(mm(1680), 0)
    clip.curveTo(mm(1530), mm(220), mm(1835), mm(475), mm(1640), mm(800))
    clip.lineTo(mm(3000), mm(800)); clip.lineTo(mm(3000), 0); clip.close()
    c.clipPath(clip, stroke=0, fill=0)
    c.drawImage(ImageReader(str(photo)), mm(1680), 0, width=mm(1320), height=H)
    c.setFillColorRGB(0.03, 0.04, 0.08, alpha=0.18)
    c.rect(mm(1600), 0, mm(1400), H, stroke=0, fill=1)
    c.restoreState()

    # Freie, typografische Marke statt Blockraster
    c.drawImage(ImageReader(str(runner_path)), mm(90), y_top(210), width=mm(110), height=mm(165), preserveAspectRatio=True, anchor="c", mask="auto")
    text_fit(c, "FRIEDENSLICHT", 220, 64, 900, 34, ORANGE)
    text_fit(c, "MARATHON", 220, 116, 900, 50, white)
    text_fit(c, "SONNTAG · 13. DEZEMBER 2026", 95, 240, 1420, 48, white)
    text_fit(c, "15:00 UHR", 95, 336, 1420, 84, GOLD)
    text_fit(c, "GEMEINDEPLATZ", 95, 475, 1420, 43, white)
    text_fit(c, "RIED IM TRAUNKREIS", 95, 545, 1420, 29, white)

    # Organische, geschwungene Informationsfläche
    c.setFillColor(ORANGE)
    wave = c.beginPath(); wave.moveTo(0, 0); wave.lineTo(mm(2360), 0); wave.curveTo(mm(2230), mm(120), mm(2410), mm(230), mm(2260), mm(320)); wave.curveTo(mm(1620), mm(245), mm(850), mm(300), 0, mm(210)); wave.close(); c.drawPath(wave, stroke=0, fill=1)
    labels = [("LAUFEN", "CA. 11,2 KM"), ("KURZ", "6 KM · 16:30 WEIGERSDORF"), ("WALKEN", "CA. 8,2 KM"), ("LICHTERZUG", "500 M")]
    xs = [90, 590, 1210, 1720]
    widths = [420, 540, 430, 470]
    for (title, detail), x, width in zip(labels, xs, widths):
        text_fit(c, title, x, 654, width, 22, NAVY)
        text_fit(c, detail, x, 700, width, 15, white)

    # Kleiner QR-Code in ruhiger, runder Insel
    round_rect_top(c, 2500, 452, 390, 285, 55, PAPER)
    draw_qr(c, "https://friedenslicht.run/", 2608, 478, 140)
    text_fit(c, "INFOS & ANMELDUNG", 2695, 633, 310, 15, NAVY, align="center")
    text_fit(c, "FRIEDENSLICHT.RUN", 2695, 681, 310, 17, ORANGE, align="center")
    c.showPage(); c.save(); return path


def main():
    runner_path = prepare_runner()
    print(variant_a(runner_path))
    print(variant_b(runner_path))


if __name__ == "__main__":
    main()
