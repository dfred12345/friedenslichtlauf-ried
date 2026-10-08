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
W_MM, H_MM = 2200, 650
W, H = W_MM * MM, H_MM * MM
OUT = Path(__file__).resolve().parent

NAVY = PCMYKColor(95, 83, 36, 36)
ORANGE = PCMYKColor(13, 72, 100, 3)
GOLD = PCMYKColor(3, 41, 84, 0)
PAPER = PCMYKColor(3, 3, 5, 0)
MUTED = PCMYKColor(56, 46, 31, 10)

pdfmetrics.registerFont(TTFont("FLM-Regular", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("FLM-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))


def mm(value):
    return value * MM


def y_top(value):
    return H - mm(value)


def rect_top(c, x, top, width, height, color):
    c.setFillColor(color)
    c.rect(mm(x), y_top(top + height), mm(width), mm(height), stroke=0, fill=1)


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


def prepare_photo():
    source = Image.open(OUT / "source-photo.jpg").convert("RGB")
    target_ratio = 740 / 650
    source_ratio = source.width / source.height
    if source_ratio > target_ratio:
        new_w = round(source.height * target_ratio)
        left = (source.width - new_w) // 2
        source = source.crop((left, 0, left + new_w, source.height))
    else:
        new_h = round(source.width / target_ratio)
        top = (source.height - new_h) // 2
        source = source.crop((0, top, source.width, top + new_h))
    path = OUT / "poster-photo-landscape-print.jpg"
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
            orange_score = red - max(green, blue)
            if red > 130 and 45 < green < 180 and blue < 130 and orange_score > 35:
                dst[xx, yy] = min(255, max(0, int((orange_score - 25) * 3.2)))
    bbox = alpha.getbbox()
    if bbox is not None:
        left, top, right, bottom = bbox
        crop = (int(left), int(top), int(right), int(bottom))
        runner, alpha = runner.crop(crop), alpha.crop(crop)
    image = Image.new("RGBA", runner.size, (207, 103, 24, 0))
    image.putalpha(alpha)
    image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
    path = OUT / "runner-landscape-print.png"
    image.save(path)
    return path


def draw_qr(c, url, x, top, size):
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=1, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    modules = len(matrix)
    module = mm(size) / modules
    c.setFillColor(white)
    c.rect(mm(x), y_top(top + size), mm(size), mm(size), stroke=0, fill=1)
    c.setFillColor(NAVY)
    for row, values in enumerate(matrix):
        for col, active in enumerate(values):
            if active:
                c.rect(mm(x) + col * module, y_top(top) - (row + 1) * module, module + 0.15, module + 0.15, stroke=0, fill=1)


def build_pdf():
    photo_path, runner_path = prepare_photo(), prepare_runner()
    pdf_path = OUT / "friedenslicht-marathon-plakat-2026-2200x650mm-querformat.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=(W, H), pageCompression=1)
    c.setTitle("Friedenslicht-Marathon Ried 2026 – Plakat Querformat 2200 × 650 mm")
    c.setAuthor("Naturfreunde Ried im Traunkreis")
    c.setSubject("Druckvorlage im Endformat 2200 × 650 mm mit QR-Codes")

    # Markenfläche
    c.drawImage(ImageReader(str(photo_path)), 0, 0, width=mm(740), height=H, mask="auto")
    c.setFillColorRGB(0.03, 0.04, 0.08, alpha=0.34)
    c.rect(0, 0, mm(740), H, stroke=0, fill=1)
    c.setFillColor(white)
    c.ellipse(mm(32), mm(52), mm(708), mm(598), stroke=0, fill=1)
    c.drawImage(ImageReader(str(runner_path)), mm(60), mm(235), width=mm(190), height=mm(280), preserveAspectRatio=True, anchor="c", mask="auto")
    text_fit(c, "FRIEDENS", 255, 120, 395, 54, ORANGE)
    text_fit(c, "LICHT", 255, 200, 395, 68, ORANGE, font="FLM-Regular")
    text_fit(c, "MARATHON", 90, 325, 565, 68, NAVY)
    text_fit(c, "FÜR LICHT INS DUNKEL", 370, 445, 520, 25, NAVY, align="center")
    text_fit(c, "RIED IM TRAUNKREIS", 370, 505, 520, 21, MUTED, align="center")

    # Datum und Treffpunkt
    rect_top(c, 740, 0, 820, 76, ORANGE)
    text_fit(c, "20 JAHRE FRIEDENSLICHTLAUF IN RIED · 2006–2026", 1150, 22, 750, 20, white, align="center")
    rect_top(c, 740, 76, 820, 314, PAPER)
    text_fit(c, "SONNTAG", 790, 112, 710, 25, ORANGE)
    text_fit(c, "13.", 782, 160, 255, 125, NAVY)
    text_fit(c, "DEZEMBER", 1055, 176, 455, 54, NAVY)
    text_fit(c, "2026", 1055, 275, 455, 63, ORANGE)
    rect_top(c, 740, 390, 820, 260, NAVY)
    text_fit(c, "15:00 UHR", 790, 424, 720, 64, GOLD)
    text_fit(c, "GEMEINDEPLATZ", 790, 520, 720, 37, white)
    text_fit(c, "RIED IM TRAUNKREIS", 790, 578, 720, 26, white)

    # Strecken und QR-Codes
    rect_top(c, 1560, 0, 640, 650, ORANGE)
    text_fit(c, "DREI WEGE, DABEI ZU SEIN", 1602, 36, 556, 28, white)
    routes = [("LAUFEN", "CA. 11,2 KM"), ("WALKEN", "CA. 8,2 KM"), ("LICHTERZUG", "LETZTE 500 M")]
    top = 102
    for name, distance in routes:
        text_fit(c, name, 1602, top, 315, 25, NAVY)
        text_fit(c, distance, 2158, top + 3, 205, 16, white, align="right")
        top += 55

    website = "https://friedenslicht.run/"
    registration = "https://friedenslicht.run/#anmeldung"
    draw_qr(c, website, 1602, 292, 222)
    draw_qr(c, registration, 1908, 292, 222)
    text_fit(c, "WEBSITE", 1713, 527, 222, 17, NAVY, align="center")
    text_fit(c, "ANMELDUNG", 2019, 527, 222, 17, NAVY, align="center")
    rect_top(c, 1560, 586, 640, 64, NAVY)
    text_fit(c, "FRIEDENSLICHT.RUN", 1880, 603, 560, 19, white, align="center")

    c.showPage()
    c.save()
    return pdf_path


if __name__ == "__main__":
    print(build_pdf())
