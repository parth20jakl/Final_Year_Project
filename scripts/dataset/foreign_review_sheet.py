"""Build an HTML page showing every image listed in foreign_ids.json, so the owner can check before deleting.

  python scripts/dataset/foreign_review_sheet.py  ->  dataset/reports/foreign_review.html
To keep an image, remove its line from dataset/annotations/foreign_ids.json before running purge_foreign.py --apply.
"""
from __future__ import annotations

import base64
import collections
import html
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent))
from common import ANNOT, PROCESSED, REPORTS, ROOT, imread, read_jsonl  # noqa: E402


def main() -> None:
    foreign: dict[str, str] = json.loads((ANNOT / "foreign_ids.json").read_text(encoding="utf-8"))
    recs = {}
    for name in ("records_unlabeled.jsonl", "records_auto.jsonl", "records_labeled.jsonl"):
        recs.update({r["id"]: r for r in read_jsonl(PROCESSED / name)})
    groups = collections.defaultdict(list)
    for i, reason in foreign.items():
        groups[reason].append(i)
    parts = [
        "<meta charset=utf-8><style>body{font:12px sans-serif;margin:20px}figure{display:inline-block;width:260px;"
        "margin:5px;vertical-align:top}img{max-width:260px;max-height:190px}figcaption{word-break:break-all}</style>",
        f"<h2>{len(foreign)} images listed as not Indian - check before deleting</h2>",
    ]
    for reason, ids in sorted(groups.items()):
        parts.append(f"<h3>{html.escape(reason)} ({len(ids)})</h3>")
        for i in ids:
            img = imread(ROOT / recs[i]["path"]) if i in recs else None
            if img is None:
                parts.append(f"<figure><figcaption>{i}: file not found</figcaption></figure>")
                continue
            s = min(1.0, 520 / max(img.shape[:2]))
            img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            data = base64.b64encode(cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 72])[1].tobytes()).decode()
            parts.append(f"<figure><img src='data:image/jpeg;base64,{data}'><figcaption><b>{i}</b><br>"
                         f"{html.escape(recs[i]['path'])}</figcaption></figure>")
    out = REPORTS / "foreign_review.html"
    out.write_text("".join(parts), encoding="utf-8")
    print(out, f"{out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
