"""Shared helpers for the ANPR dataset pipeline."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "dataset" / "raw"
PROCESSED = ROOT / "dataset" / "processed"
SPLITS = ROOT / "dataset" / "splits"
REPORTS = ROOT / "dataset" / "reports"
ANNOT = ROOT / "dataset" / "annotations"
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class Record:
    """One image with zero or more plate boxes (pixel xyxy in EXIF-oriented frame)."""

    id: str
    path: str  # relative to ROOT, posix
    source: str
    license: str
    width: int
    height: int
    boxes: list[list[float]] = field(default_factory=list)
    plate_texts: list[str] = field(default_factory=list)
    group: str = ""
    label_source: str = "manual"  # manual | auto_accepted | auto_reviewed
    domain: str = "indian"  # indian | external
    dhash: str = ""
    extra: dict = field(default_factory=dict)


def rel(p: Path) -> str:
    return p.resolve().relative_to(ROOT).as_posix()


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def long_path(p: Path) -> str:
    """Windows long-path safe string."""
    s = str(p.resolve())
    return "\\\\?\\" + s if len(s) > 240 and not s.startswith("\\\\?\\") else s


def imread(path: Path) -> np.ndarray | None:
    """cv2 read that survives unicode / long Windows paths and applies EXIF orientation."""
    try:
        data = np.fromfile(long_path(path), dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return None


def oriented_size(path: Path) -> tuple[int, int, int]:
    """(w, h, exif_orientation) with EXIF rotation applied to w/h."""
    with Image.open(long_path(path)) as im:
        w, h = im.size
        try:
            o = int(im.getexif().get(274, 1))
        except Exception:
            o = 1
    if o in (5, 6, 7, 8):
        w, h = h, w
    return w, h, o


def dhash(img: np.ndarray, size: int = 8) -> str:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    g = cv2.resize(g, (size + 1, size), interpolation=cv2.INTER_AREA)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return f"{int(''.join('1' if b else '0' for b in bits), 2):016x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


_PLATE_RE = re.compile(r"[^A-Z0-9]")


def norm_text(s: str) -> str:
    return _PLATE_RE.sub("", s.upper())


# Indian plate: 2 letters state, 1-2 digits RTO, 0-3 letters series, 1-4 digits (BH series ignored here)
_IN_PLATE = re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{1,4}$")


def plausible_indian_plate(t: str) -> bool:
    return bool(_IN_PLATE.match(t)) and 6 <= len(t) <= 11


def clip_box(b: list[float], w: int, h: int) -> list[float]:
    x1, y1, x2, y2 = b
    return [max(0.0, min(x1, w)), max(0.0, min(y1, h)), max(0.0, min(x2, w)), max(0.0, min(y2, h))]


def box_ok(b: list[float], w: int, h: int, min_px: float = 4.0) -> bool:
    x1, y1, x2, y2 = b
    return x2 - x1 >= min_px and y2 - y1 >= min_px and x1 >= 0 and y1 >= 0 and x2 <= w and y2 <= h


def short_id(prefix: str, key: str) -> str:
    return f"{prefix}_{hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]}"
