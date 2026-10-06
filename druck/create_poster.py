from pathlib import Path

from PIL import Image
from reportlab.lib.colors import PCMYKColor, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

MM = 72 / 25.4
W_MM, H_MM = 650, 2200
W, H = W_MM * MM, H_MM * MM
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

NAVY = PCMYKColor(95, 83, 36, 36)
BLUE = PCMYKColor(83, 69, 31, 14)
ORANGE = PCMYKColor(13, 72, 100, 3)
GOLD = PCMYKColor(3, 41, 84, 0)
PAPER = PCMYKColor(3, 3, 5, 0)
INK = NAVY
MUTED = PCMYKColor(56, 46, 31, 10)

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
pdfmetrics.registerFont(TTFont("FLM-Regular", FONT_REG))
pdfmetrics.registerFont(TTFont("FLM-Bold", FONT_BOLD))


def mm(v):
    return v * MM


def y_top(v):
    return H - mm(v)


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


def prep_assets():
    photo_source = OUT / "source-photo.jpg"
    runner_source = OUT / "source-runner.png"
    if not photo_source.exists() or not runner_source.exists():
        raise FileNotFoundError("Die Plakat-Quellbilder fehlen im Ordner druck.")

    photo = Image.open(photo_source).convert("RGB")
    target_ratio = 650 / 560
    source_ratio = photo.width / photo.height
    if source_ratio > target_ratio:
        new_w = round(photo.height * target_ratio)
        left = (photo.width - new_w) // 2
        photo = photo.crop((left, 0, left + new_w, photo.height))
    else:
        new_h = round(photo.width / target_ratio)
        top = (photo.height - new_h) // 2
        photo = photo.crop((0, top, photo.width, top + new_h))
    photo_path = OUT / "poster-photo-print.jpg"
    photo.save(photo_path, "JPEG", quality=95, subsampling=0)

    runner = Image.open(runner_source).convert("RGB")
    pix = runner.load()
    alpha = Image.new("L", runner.size, 0)
    ap = alpha.load()
    for yy in range(runner.height):
        for xx in range(runner.width):
            r, g, b = pix[xx, yy]
            orange_score = r - max(g, b)
            if r > 130 and 45 < g < 180 and b < 130 and orange_score > 35:
                ap[xx, yy] = min(255, max(0, int((orange_score - 25) * 3.2)))
    bbox = alpha.getbbox()
    if bbox is not None:
        left, top, right, bottom = bbox
        crop_box = (int(left), int(top), int(right), int(bottom))
        runner = runner.crop(crop_box)
        alpha = alpha.crop(crop_box)
    orange = Image.new("RGBA", runner.size, (207, 103, 24, 0))
    orange.putalpha(alpha)
    orange = orange.resize((orange.width * 2, orange.height * 2), Image.Resampling.LANCZOS)
    runner_path = OUT / "runner-print.png"
    orange.save(runner_path)
    return photo_path, runner_path


def build_pdf():
    photo_path, runner_path = prep_assets()
    pdf_path = OUT / "friedenslicht-marathon-plakat-2026-650x2200mm.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=(W, H), pageCompression=1)
    c.setTitle("Friedenslicht-Marathon Ried 2026 – Plakat 650 × 2200 mm")
    c.setAuthor("Naturfreunde Ried im Traunkreis")
    c.setSubject("Druckvorlage im Endformat 650 × 2200 mm")

    # 1. Bild- und Markenfläche
    c.drawImage(ImageReader(str(photo_path)), 0, y_top(560), width=W, height=mm(560), mask="auto")
    c.setFillColorRGB(0.03, 0.04, 0.08, alpha=0.32)
    c.rect(0, y_top(560), W, mm(560), stroke=0, fill=1)
    c.setFillColor(white)
    c.ellipse(mm(35), y_top(535), mm(615), y_top(25), stroke=0, fill=1)
    c.drawImage(ImageReader(str(runner_path)), mm(55), y_top(395), width=mm(170), height=mm(250), preserveAspectRatio=True, anchor="c", mask="auto")
    text_fit(c, "FRIEDENS", 230, 105, 345, 49, ORANGE)
    text_fit(c, "LICHT", 230, 176, 345, 63, ORANGE, font="FLM-Regular")
    text_fit(c, "MARATHON", 90, 285, 490, 61, NAVY)
    text_fit(c, "FÜR LICHT INS DUNKEL", 325, 385, 455, 23, INK, align="center")
    text_fit(c, "RIED IM TRAUNKREIS", 325, 435, 455, 19, MUTED, align="center")

    # 2. Jubiläumsband
    rect_top(c, 0, 560, 650, 90, ORANGE)
    text_fit(c, "20 JAHRE FRIEDENSLICHTLAUF IN RIED · 2006–2026", 325, 584, 590, 18, white, align="center")

    # 3. Datum – maximale Fernwirkung
    rect_top(c, 0, 650, 650, 395, PAPER)
    text_fit(c, "SONNTAG", 55, 705, 540, 30, ORANGE)
    text_fit(c, "13.", 48, 760, 240, 118, NAVY)
    text_fit(c, "DEZ", 285, 772, 310, 79, NAVY)
    text_fit(c, "2026", 285, 900, 310, 58, ORANGE)

    # 4. Treffpunkt
    rect_top(c, 0, 1045, 650, 300, NAVY)
    text_fit(c, "15:00 UHR", 48, 1093, 554, 75, GOLD)
    text_fit(c, "GEMEINDEPLATZ", 48, 1210, 554, 38, white)
    text_fit(c, "RIED IM TRAUNKREIS", 48, 1270, 554, 24, white)

    # 5. Drei Teilnahmewege
    rect_top(c, 0, 1345, 650, 450, PAPER)
    text_fit(c, "DREI WEGE, DABEI ZU SEIN", 48, 1395, 554, 29, ORANGE)
    rows = [
        ("LAUFEN", "CA. 11,2 KM"),
        ("WALKEN", "CA. 8,2 KM"),
        ("LICHTERZUG", "LETZTE 500 M"),
    ]
    top = 1477
    for idx, (name, distance) in enumerate(rows):
        if idx:
            c.setStrokeColor(PCMYKColor(18, 14, 8, 14))
            c.setLineWidth(mm(1))
            c.line(mm(48), y_top(top - 15), mm(602), y_top(top - 15))
        text_fit(c, name, 48, top, 340, 39, NAVY)
        text_fit(c, distance, 602, top + 10, 220, 22, ORANGE, align="right")
        top += 103

    # 6. Abschluss / Webadresse
    rect_top(c, 0, 1795, 650, 405, ORANGE)
    text_fit(c, "GEMEINSAM", 48, 1855, 554, 53, white)
    text_fit(c, "BEWEGEN.", 48, 1930, 554, 53, NAVY)
    text_fit(c, "GEMEINSAM", 48, 2010, 554, 53, white)
    text_fit(c, "HELFEN.", 48, 2085, 554, 53, NAVY)
    c.setFillColor(NAVY)
    c.rect(0, 0, W, mm(52), stroke=0, fill=1)
    text_fit(c, "FRIEDENSLICHT.RUN", 325, 2164, 560, 19, white, align="center")

    c.showPage()
    c.save()
    return pdf_path


if __name__ == "__main__":
    print(build_pdf())
