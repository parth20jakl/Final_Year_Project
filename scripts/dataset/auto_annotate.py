"""Auto-annotate the unlabeled pool with the annotator model (human-in-the-loop).

Tiers (per image, from the annotator's detections)
  auto_accepted : >=1 box with conf >= --hi and no box in the uncertain band
  review        : any box with --lo <= conf < --hi  -> dataset/reports/review_queue.html (+ review_queue.jsonl)
  none          : no box >= --lo -> NOT used (could be a missed plate; never added as a negative)

The thresholds are validated on the MANUAL val split (precision/recall of the annotator at --hi), and that
number is written to dataset/reports/auto_annotation_report.json. Reviewed decisions are applied with
--apply-review (dataset/annotations/review_decisions.json: {"<image_id>": "accept"|"reject"}).
Auto-labelled images only ever enter TRAIN. Test/val stay manual.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import ANNOT, PROCESSED, REPORTS, ROOT, SPLITS, imread, read_jsonl, write_jsonl  # noqa: E402


def iou(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0


def predict(model, paths: list[str], imgsz: int, conf: float, bs: int = 16):
    out = []
    for i in range(0, len(paths), bs):
        chunk = [imread(ROOT / p) for p in paths[i:i + bs]]
        res = model.predict(chunk, imgsz=imgsz, conf=conf, iou=0.5, verbose=False, device=0, half=True)
        for r in res:
            out.append([(*b.xyxy[0].tolist(), float(b.conf[0])) for b in r.boxes])
    return out


def validate(model, hi: float, imgsz: int) -> dict:
    sp = json.loads((SPLITS / "split_v1.json").read_text())["split"]
    val = [r for r in read_jsonl(PROCESSED / "records_labeled.jsonl") if sp[r["id"]] == "val"]
    preds = predict(model, [r["path"] for r in val], imgsz, 0.05)
    res = {}
    for thr in (0.25, 0.4, 0.5, 0.6, 0.7, 0.8):
        tp = fp = fn = 0
        for r, p in zip(val, preds):
            dets = [d for d in p if d[4] >= thr]
            used = set()
            for d in dets:
                m = max(((iou(d[:4], g), j) for j, g in enumerate(r["boxes"]) if j not in used), default=(0, -1))
                if m[0] >= 0.5:
                    tp += 1
                    used.add(m[1])
                else:
                    fp += 1
            fn += len(r["boxes"]) - len(used)
        res[str(thr)] = {"precision": round(tp / max(tp + fp, 1), 4), "recall": round(tp / max(tp + fn, 1), 4),
                         "tp": tp, "fp": fp, "fn": fn}
    return res


def thumb_b64(rec: dict, dets) -> str:
    img = imread(ROOT / rec["path"])
    for x1, y1, x2, y2, c in dets:
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0) if c >= 0.6 else (0, 165, 255),
                      max(2, img.shape[1] // 200))
    s = 360 / max(img.shape[:2])
    img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return base64.b64encode(cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tobytes()).decode()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="runs/annotator/weights/best.pt")
    ap.add_argument("--hi", type=float, default=0.6)
    ap.add_argument("--lo", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--apply-review", action="store_true")
    a = ap.parse_args()
    from ultralytics import YOLO

    auto_path = PROCESSED / "records_auto.jsonl"
    if a.apply_review:
        dec = json.loads((ANNOT / "review_decisions.json").read_text())
        rows = read_jsonl(auto_path)
        for r in rows:
            d = dec.get(r["id"])
            if r["label_source"] == "review_pending" and d:
                r["label_source"] = "auto_reviewed" if d == "accept" else "rejected"
        write_jsonl(auto_path, rows)
        print("applied", sum(1 for r in rows if r["label_source"] == "auto_reviewed"), "accepted after review")
        return

    model = YOLO(str(ROOT / a.weights))
    val_stats = validate(model, a.hi, a.imgsz)
    sp = json.loads((SPLITS / "split_v1.json").read_text())["split"]
    pool = [r for r in read_jsonl(PROCESSED / "records_unlabeled.jsonl") if sp.get(r["id"]) == "pool"]
    preds = predict(model, [r["path"] for r in pool], a.imgsz, a.lo)
    rows, review, tiers = [], [], {"auto_accepted": 0, "review": 0, "none": 0}
    for r, p in zip(pool, preds):
        if not p:
            tiers["none"] += 1
            continue
        uncertain = [d for d in p if d[4] < a.hi]
        if uncertain:
            r.update(boxes=[list(d[:4]) for d in p], plate_texts=[""] * len(p), label_source="review_pending",
                     extra={"det_conf": [round(d[4], 3) for d in p]})
            review.append((r, p))
            tiers["review"] += 1
        else:
            r.update(boxes=[list(d[:4]) for d in p], plate_texts=[""] * len(p), label_source="auto_accepted",
                     extra={"det_conf": [round(d[4], 3) for d in p]})
            tiers["auto_accepted"] += 1
        rows.append(r)
    write_jsonl(auto_path, rows)
    REPORTS.mkdir(parents=True, exist_ok=True)
    write_jsonl(REPORTS / "review_queue.jsonl", ({"id": r["id"], "path": r["path"], "conf": r["extra"]["det_conf"]} for r, _ in review))
    cards = "".join(f'<div class=c><img src="data:image/jpeg;base64,{thumb_b64(r, p)}"><br><code>{r["id"]}</code> {r["extra"]["det_conf"]}</div>'
                    for r, p in review)
    (REPORTS / "review_queue.html").write_text(
        "<meta charset=utf-8><style>body{font:12px sans-serif}.c{display:inline-block;margin:6px;width:370px}</style>"
        f"<h3>Review queue ({len(review)}) - write decisions to dataset/annotations/review_decisions.json "
        "as {id: accept|reject}</h3>" + cards)
    rep = {"annotator": a.weights, "thresholds": {"hi": a.hi, "lo": a.lo}, "val_manual_precision_recall": val_stats,
           "pool_images": len(pool), "tiers": tiers,
           "note": "auto_accepted precision is estimated from the manual val set; no auto label is ever used in val/test"}
    (REPORTS / "auto_annotation_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
