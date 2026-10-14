"""Generate rough sample UI mockups (NOT final design) for the Android ANPR app.

Run from the repo root:  .venv-train\\Scripts\\python.exe design/make_ui_samples.py
Output: design/ui_samples/*.png
"""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "ui_samples"
OUT.mkdir(exist_ok=True)
S = 2             # supersampling factor
W, H = 720, 1500  # logical px

# ---- palette (dark theme) -------------------------------------------------
BG, SURF, SURF2, LINE = "#0B1220", "#121C2F", "#1A2740", "#2A3A57"
TXT, MUTED = "#E8EEF8", "#8FA3C0"
ACC = "#22D3EE"
OK, WARN, ERR, VIO, BLU = "#34D399", "#FBBF24", "#F87171", "#A78BFA", "#60A5FA"
REASON = {"PROCESSED": OK, "SKIP_TIME": BLU, "SKIP_AREA": WARN, "SKIP_REGION": VIO}
FD = "C:/Windows/Fonts/"


def font(sz, bold=False):
    for n in (("segoeuib.ttf" if bold else "segoeui.ttf"), ("arialbd.ttf" if bold else "arial.ttf")):
        try:
            return ImageFont.truetype(FD + n, int(sz * S))
        except OSError:
            continue
    return ImageFont.load_default()


class Screen:
    def __init__(self):
        self.im = Image.new("RGB", (W * S, H * S), BG)
        self.d = ImageDraw.Draw(self.im, "RGBA")
        self.t(28, 14, "9:41", 15, TXT, True)
        self.t(W - 28, 14, "5G  82%", 14, MUTED, anchor="ra")

    # primitives ---------------------------------------------------------
    def rr(self, x, y, w, h, r=16, fill=SURF, outline=None, width=1):
        self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], r * S, fill=fill,
                                 outline=outline, width=width * S)

    def t(self, x, y, s, sz=16, col=TXT, bold=False, anchor="la"):
        self.d.text((x * S, y * S), s, font=font(sz, bold), fill=col, anchor=anchor)

    def line(self, x1, y1, x2, y2, col=LINE, w=1):
        self.d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=col, width=w * S)

    def circle(self, cx, cy, r, fill):
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill)

    def chip(self, x, y, label, col=ACC, filled=False, h=34, sz=14):
        w = int(len(label) * sz * 0.62 + 28)
        self.rr(x, y, w, h, h // 2, fill=(col if filled else SURF2), outline=col, width=1)
        self.t(x + w / 2, y + h / 2, label, sz, BG if filled else col, True, "mm")
        return w

    def toggle(self, x, y, on=True):
        self.rr(x, y, 56, 30, 15, fill=ACC if on else LINE)
        self.circle(x + (41 if on else 15), y + 15, 11, "#FFFFFF")

    def slider(self, x, y, w, frac, col=ACC):
        self.rr(x, y, w, 6, 3, fill=LINE)
        self.rr(x, y, int(w * frac), 6, 3, fill=col)
        self.circle(x + w * frac, y + 3, 11, col)

    def app_bar(self, title, back=True, right=None):
        if back:
            self.t(28, 62, "<", 26, TXT, True)
        self.t(80 if back else 28, 66, title, 22, TXT, True)
        if right:
            self.t(W - 28, 70, right, 16, ACC, True, "ra")

    def nav(self, active=0):
        self.rr(0, H - 96, W, 96, 0, fill=SURF)
        self.line(0, H - 96, W, H - 96)
        items = [("O", "Live"), ("[]", "Photo"), ("=", "Filters"), ("#", "Models"), ("~", "Bench")]
        for i, (ic, lb) in enumerate(items):
            cx = W / 10 + i * W / 5
            c = ACC if i == active else MUTED
            self.t(cx, H - 78, ic, 24, c, True, "ma")
            self.t(cx, H - 40, lb, 13, c, i == active, "ma")

    def scene(self, y0, y1, boxes=True, roi=True, plate="MH 12 AB 1234"):
        """Fake camera frame: gradient background, a car and a plate."""
        h = y1 - y0
        g = Image.new("RGB", (W * S, h * S))
        gd = ImageDraw.Draw(g)
        for i in range(h * S):
            k = i / (h * S)
            gd.line([(0, i), (W * S, i)], fill=(int(30 + 40 * k), int(38 + 38 * k), int(52 + 30 * k)))
        self.im.paste(g, (0, y0 * S))
        cx = W // 2
        self.rr(cx - 230, y0 + h * 0.30, 460, h * 0.34, 36, fill="#C9CED8")
        self.rr(cx - 170, y0 + h * 0.18, 340, h * 0.20, 40, fill="#AEB6C4")
        self.rr(cx - 150, y0 + h * 0.21, 300, h * 0.12, 22, fill="#2B3446")
        for dx in (-175, 175):
            self.circle(cx + dx, y0 + h * 0.62, 38, "#10151F")
        px, py, pw, ph = cx - 105, y0 + h * 0.50, 210, 62
        self.rr(px, py, pw, ph, 6, fill="#F4F4F0", outline="#222222", width=2)
        self.t(px + pw / 2, py + ph / 2, plate, 24, "#111111", True, "mm")
        if roi:
            x1, ya, x2, yb = 60, y0 + h * 0.36, W - 60, y0 + h * 0.86
            for k in range(int(x1), int(x2), 22):
                self.line(k, ya, k + 11, ya, ACC, 2)
                self.line(k, yb, k + 11, yb, ACC, 2)
            for k in range(int(ya), int(yb), 22):
                self.line(x1, k, x1, k + 11, ACC, 2)
                self.line(x2, k, x2, k + 11, ACC, 2)
            self.t(x1 + 6, ya + 6, "REGION", 12, ACC, True)
        if boxes:
            self.rr(px - 8, py - 8, pw + 16, ph + 16, 8, fill=None, outline=OK, width=3)
            self.rr(px - 8, py - 48, 250, 34, 8, fill=OK)
            self.t(px, py - 31, "MH12AB1234  0.94", 16, BG, True, "lm")

    def save(self, name):
        self.im.resize((W, H), Image.LANCZOS).save(OUT / name)


def live():
    s = Screen()
    s.rr(20, 52, 300, 44, 22, fill=SURF2, outline=LINE)
    s.t(40, 74, "YOLO11n  FGD", 17, TXT, True, "lm")
    s.t(292, 74, "v", 16, MUTED, True, "mm")
    s.chip(W - 130, 56, "LIVE", ERR, True)
    s.scene(110, 1010)
    s.rr(20, 126, 210, 98, 14, fill="#0B1220")
    s.t(34, 136, "FPS  18.4", 16, TXT, True)
    s.t(34, 164, "Infer  38 ms", 15, MUTED)
    s.t(34, 190, "Skip   46 %", 15, MUTED)
    s.chip(W - 190, 130, "PROCESSED", OK, False)
    s.rr(0, 1010, W, H - 1010 - 96, 28, fill=SURF)
    s.rr(W / 2 - 28, 1022, 56, 5, 3, fill=LINE)
    s.t(28, 1048, "Filters  (Time > Region > Area)", 16, MUTED, True)
    x = 28
    for lb, c in (("Time 100 ms", BLU), ("Region ON", VIO), ("Area 12 %", WARN)):
        x += s.chip(x, 1080, lb, c) + 10
    s.rr(28, 1140, W - 56, 128, 20, fill=SURF2)
    s.t(48, 1156, "LAST PLATE", 12, MUTED, True)
    s.t(48, 1180, "MH 12 AB 1234", 36, TXT, True)
    s.t(48, 1232, "Valid format   conf 0.94   OCR 21 ms", 15, OK)
    s.t(W - 48, 1190, "08:41:12", 15, MUTED, anchor="ra")
    s.rr(28, 1288, W - 56, 64, 16, fill=ACC)
    s.t(W / 2, 1320, "Stop", 22, BG, True, "mm")
    s.nav(0)
    s.save("01_live.png")


def photo():
    s = Screen()
    s.app_bar("Photo mode", True, "Gallery")
    s.scene(130, 780, roi=False)
    s.rr(20, 800, W - 40, 500, 24, fill=SURF)
    s.t(44, 824, "RESULT", 12, MUTED, True)
    s.t(44, 848, "MH 12 AB 1234", 44, TXT, True)
    s.chip(44, 916, "Valid Indian format", OK, True)
    s.chip(280, 916, "conf 0.94", ACC)
    s.t(44, 976, "Timing", 14, MUTED, True)
    parts = [("Pre", 6, BLU), ("Detect", 38, ACC), ("Post", 3, VIO), ("OCR", 21, WARN)]
    tot = sum(p[1] for p in parts)
    x, bw = 44, W - 88
    for _, v, c in parts:
        w = bw * v / tot
        s.rr(x, 1004, w - 3, 22, 5, fill=c)
        x += w
    xx = 44
    for lb, v, c in parts:
        s.circle(xx + 6, 1056, 6, c)
        s.t(xx + 18, 1046, f"{lb} {v} ms", 14, MUTED)
        xx += 150
    s.t(44, 1100, "Model  YOLO11n FGD      Total 68 ms", 15, MUTED)
    s.t(44, 1130, "Time filter is bypassed in photo mode", 14, MUTED)
    s.rr(44, 1196, 300, 64, 16, fill=SURF2, outline=LINE)
    s.t(194, 1228, "Retake", 20, TXT, True, "mm")
    s.rr(366, 1196, 310, 64, 16, fill=ACC)
    s.t(521, 1228, "Save result", 20, BG, True, "mm")
    s.nav(1)
    s.save("02_photo_result.png")


def filters():
    s = Screen()
    s.app_bar("Frame filters", False, "Reset")
    s.t(28, 130, "Applied in order: Time > Region > Area. Each skip logs its reason.", 14, MUTED)
    s.rr(20, 180, W - 40, 250, 22, fill=SURF)
    s.t(44, 200, "Time filter", 20, TXT, True)
    s.t(44, 232, "Process one frame per interval (live mode only)", 14, MUTED)
    s.toggle(W - 100, 200, True)
    xs = 44
    for v in ("50", "75", "100", "150", "200"):
        sel = v == "100"
        s.rr(xs, 292, 118, 56, 14, fill=ACC if sel else SURF2, outline=None if sel else LINE)
        s.t(xs + 59, 320, v + " ms", 18, BG if sel else TXT, True, "mm")
        xs += 126
    s.t(44, 372, "About 10 frames/s are sent to the detector", 14, MUTED)

    s.rr(20, 450, W - 40, 330, 22, fill=SURF)
    s.t(44, 470, "Region of interest", 20, TXT, True)
    s.t(44, 502, "Skip frames with no activity inside the region", 14, MUTED)
    s.toggle(W - 100, 470, True)
    s.rr(44, 548, W - 88, 170, 14, fill="#1B2438", outline=LINE)
    for k in range(110, 570, 20):
        s.line(k, 580, k + 10, 580, ACC, 2)
        s.line(k, 690, k + 10, 690, ACC, 2)
    for k in range(580, 690, 20):
        s.line(110, k, 110, k + 10, ACC, 2)
        s.line(570, k, 570, k + 10, ACC, 2)
    s.t(W / 2, 634, "Rectangle now - polygon later", 15, MUTED, False, "mm")
    s.t(44, 736, "Edit region", 16, ACC, True)

    s.rr(20, 800, W - 40, 230, 22, fill=SURF)
    s.t(44, 820, "Area / motion filter", 20, TXT, True)
    s.t(44, 852, "Run detector only if changed pixels exceed threshold", 14, MUTED)
    s.toggle(W - 100, 820, True)
    s.slider(44, 926, W - 88, 0.30, WARN)
    s.t(44, 954, "Threshold", 14, MUTED)
    s.t(W - 44, 954, "12 %", 16, WARN, True, "ra")

    s.rr(20, 1050, W - 40, 170, 22, fill=SURF)
    s.t(44, 1070, "Detection confidence", 20, TXT, True)
    s.slider(44, 1146, W - 88, 0.45, ACC)
    s.t(44, 1174, "Minimum score", 14, MUTED)
    s.t(W - 44, 1174, "0.45", 16, ACC, True, "ra")

    s.rr(20, 1250, W - 40, 60, 16, fill=SURF2, outline=LINE)
    x = 36
    for r, c in REASON.items():
        s.circle(x + 6, 1280, 6, c)
        s.t(x + 18, 1269, r.replace("_", " "), 12, MUTED)
        x += 168
    s.nav(2)
    s.save("03_filters.png")


def models():
    s = Screen()
    s.app_bar("Detector model", False)
    s.t(28, 130, "Switch at runtime. All models run on ONNX Runtime.", 14, MUTED)
    rows = [("YOLOv6n", "Baseline", False), ("YOLOv6n", "FGD", False), ("YOLO11n", "Baseline", False),
            ("YOLO11n", "FGD", True), ("YOLO26n", "Baseline", False), ("YOLO26n", "FGD", False)]
    y = 180
    for name, kind, sel in rows:
        s.rr(20, y, W - 40, 150, 22, fill=SURF2 if sel else SURF, outline=ACC if sel else LINE, width=2 if sel else 1)
        s.t(44, y + 18, name, 24, TXT, True)
        s.chip(44 + len(name) * 15 + 24, y + 18, kind, ACC if kind == "FGD" else MUTED, kind == "FGD", 32, 13)
        s.t(44, y + 62, "Size  - MB      mAP50  -      Latency  - ms", 15, MUTED)
        s.t(44, y + 94, "Values appear after benchmarking", 13, MUTED)
        if sel:
            s.circle(W - 64, y + 40, 16, ACC)
            s.t(W - 64, y + 40, "OK", 13, BG, True, "mm")
        else:
            s.circle(W - 64, y + 40, 16, LINE)
            s.circle(W - 64, y + 40, 14, BG)
        y += 166
    s.nav(3)
    s.save("04_models.png")


def bench():
    s = Screen()
    s.app_bar("Benchmark", False, "Export")
    s.rr(20, 130, W - 40, 150, 22, fill=SURF)
    s.t(44, 150, "Run configuration", 14, MUTED, True)
    s.t(44, 180, "YOLO11n FGD   Time 100 ms, Region ON, Area 12 %", 16, TXT)
    s.t(44, 214, "Warm-up 10 s   Duration 60 s   Repetitions 3", 15, MUTED)
    s.rr(W - 220, 228, 180, 40, 20, fill=ACC)
    s.t(W - 130, 248, "Start run", 16, BG, True, "mm")
    x = 20
    for lb, v, c in (("FPS mean", "18.4", ACC), ("P50 ms", "41", TXT), ("P95 ms", "63", WARN), ("RAM MB", "212", TXT)):
        s.rr(x, 300, 158, 110, 18, fill=SURF)
        s.t(x + 16, 316, lb, 13, MUTED, True)
        s.t(x + 16, 346, v, 34, c, True)
        x += 170
    s.rr(20, 430, W - 40, 300, 22, fill=SURF)
    s.t(44, 450, "Latency distribution (ms)", 16, TXT, True)
    random.seed(3)
    bx = 52
    for i, v in enumerate([4, 9, 20, 34, 50, 44, 30, 18, 10, 6, 4, 2]):
        h = v * 4
        s.rr(bx, 700 - h, 40, h, 6, fill=ACC if i != 9 else WARN)
        bx += 52
    s.line(44, 700, W - 44, 700)
    s.t(44, 708, "20", 12, MUTED)
    s.t(W - 44, 708, "80", 12, MUTED, anchor="ra")
    s.rr(20, 750, W - 40, 250, 22, fill=SURF)
    s.t(44, 770, "Frames by decision", 16, TXT, True)
    x, bw = 44, W - 88
    segs = [("PROCESSED", 54, OK), ("SKIP_TIME", 28, BLU), ("SKIP_AREA", 12, WARN), ("SKIP_REGION", 6, VIO)]
    for _, p, c in segs:
        w = bw * p / 100
        s.rr(x, 812, w - 2, 36, 6, fill=c)
        x += w
    y = 872
    for lb, p, c in segs:
        s.circle(52, y + 12, 7, c)
        s.t(70, y, lb.replace("_", " "), 15, TXT)
        s.t(W - 44, y, f"{p} %", 15, MUTED, True, "ra")
        y += 30
    s.rr(20, 1020, W - 40, 200, 22, fill=SURF)
    s.t(44, 1040, "Compare runs", 16, TXT, True)
    for i, (m, f) in enumerate((("YOLO11n baseline", "17.1"), ("YOLO11n FGD", "18.4"), ("YOLO26n FGD", "16.2"))):
        s.t(44, 1080 + i * 40, m, 15, MUTED)
        s.t(W - 44, 1080 + i * 40, f + " FPS", 15, TXT, True, "ra")
    s.t(44, 1240, "Sample numbers for layout only", 12, MUTED)
    s.nav(4)
    s.save("05_benchmark.png")


def history():
    s = Screen()
    s.app_bar("Detection log", False, "Clear")
    s.t(28, 130, "Stored on this device only", 14, MUTED)
    rows = [("08:41:12", "MH 12 AB 1234", "PROCESSED", "0.94"), ("08:41:11", "-", "SKIP_TIME", ""),
            ("08:41:11", "-", "SKIP_AREA", ""), ("08:41:09", "KA 05 MN 4521", "PROCESSED", "0.88"),
            ("08:41:08", "-", "SKIP_REGION", ""), ("08:41:06", "DL 8C AF 5031", "PROCESSED", "0.91"),
            ("08:41:05", "-", "SKIP_TIME", ""), ("08:41:03", "TN 07 CQ 9912", "PROCESSED", "0.79"),
            ("08:41:02", "-", "SKIP_AREA", ""), ("08:41:00", "GJ 01 XY 0042", "PROCESSED", "0.90")]
    y = 170
    for ts, pl, rs, cf in rows:
        s.rr(20, y, W - 40, 104, 18, fill=SURF)
        s.rr(20, y + 18, 6, 68, 3, fill=REASON[rs])
        s.t(44, y + 16, pl, 24, TXT if pl != "-" else MUTED, True)
        s.t(44, y + 58, ts, 14, MUTED)
        lab = rs.replace("_", " ")
        cw = int(len(lab) * 13 * 0.62 + 28)
        s.chip(W - 44 - cw, y + 18, lab, REASON[rs], False, 32, 13)
        if cf:
            s.t(W - 44, y + 62, "conf " + cf, 14, MUTED, anchor="ra")
        y += 116
    s.nav(0)
    s.save("06_detection_log.png")


def style():
    s = Screen()
    s.t(28, 60, "Style guide (sample)", 28, TXT, True)
    s.t(28, 102, "Dark theme, cyan accent, semantic status colours", 15, MUTED)
    pal = [("Background", BG), ("Surface", SURF), ("Surface 2", SURF2), ("Line", LINE), ("Text", TXT), ("Muted", MUTED),
           ("Accent", ACC), ("Processed", OK), ("Skip time", BLU), ("Skip area", WARN), ("Skip region", VIO),
           ("Error", ERR)]
    for i, (n, c) in enumerate(pal):
        x, y = 28 + (i % 3) * 228, 150 + (i // 3) * 140
        s.rr(x, y, 208, 80, 16, fill=c, outline=LINE)
        s.t(x, y + 88, n, 15, TXT, True)
        s.t(x, y + 110, c.upper(), 13, MUTED)
    y = 730
    s.t(28, y, "Type", 14, MUTED, True)
    s.t(28, y + 28, "Plate text 36 bold", 36, TXT, True)
    s.t(28, y + 84, "Title 22 bold", 22, TXT, True)
    s.t(28, y + 120, "Body 16 regular, caption 13 muted", 16, TXT)
    y = 900
    s.t(28, y, "Components", 14, MUTED, True)
    x = 28
    x += s.chip(x, y + 34, "PROCESSED", OK) + 10
    x += s.chip(x, y + 34, "Time 100 ms", BLU) + 10
    s.chip(x, y + 34, "LIVE", ERR, True)
    s.toggle(28, y + 100, True)
    s.toggle(110, y + 100, False)
    s.slider(210, y + 112, 300, 0.4, ACC)
    s.rr(28, y + 170, 300, 60, 16, fill=ACC)
    s.t(178, y + 200, "Primary action", 18, BG, True, "mm")
    s.rr(350, y + 170, 300, 60, 16, fill=SURF2, outline=LINE)
    s.t(500, y + 200, "Secondary", 18, TXT, True, "mm")
    s.rr(28, y + 260, W - 56, 120, 20, fill=SURF)
    s.t(48, y + 280, "Card on surface", 18, TXT, True)
    s.t(48, y + 312, "Corner radius 20, padding 20", 14, MUTED)
    s.save("00_style_guide.png")


def overview():
    names = ["00_style_guide", "01_live", "02_photo_result", "03_filters", "04_models", "05_benchmark",
             "06_detection_log"]
    ims = [Image.open(OUT / f"{n}.png").resize((360, 750), Image.LANCZOS) for n in names]
    sheet = Image.new("RGB", (len(ims) * 380 + 20, 810), "#05080F")
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FD + "segoeui.ttf", 18)
    for i, (im, n) in enumerate(zip(ims, names)):
        sheet.paste(im, (20 + i * 380, 40))
        d.text((20 + i * 380, 12), n[3:].replace("_", " "), font=f, fill="#8FA3C0")
    sheet.save(OUT / "overview_all_screens.png")


if __name__ == "__main__":
    style()
    live()
    photo()
    filters()
    models()
    bench()
    history()
    overview()
    print(sorted(p.name for p in OUT.iterdir()))
