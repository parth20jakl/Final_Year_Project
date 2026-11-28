"""Annotate number plates with YOLO-World (open vocabulary) and compare against the existing human boxes.

Asking YOLO-World for "license plate" on the whole image finds almost nothing, so two steps are used:
  1. find vehicles (car, truck, bus, motorcycle, auto rickshaw);
  2. inside each vehicle (and its lower part, and the whole image) search for a plate, offering competing classes
     (headlight, logo, grille, ...) so that they do not get labelled as plates. Boxes with an implausible shape are
     dropped and only the best --topk plate candidates per crop are kept.

Human labels are never overwritten. Output (dataset/annotations/yoloworld/):
  labels/<image path>.txt   YOLO format  "0 xc yc w h conf"
  detections.jsonl          one line per image: all candidates and the agreement status
  report.json               settings and agreement with the human boxes (IoU >= 0.5)

Status per image: agree (all human boxes matched, nothing extra), extra, partial, missed.

  python scripts/dataset/yoloworld_annotate.py --tune [--weights W --imgsz N]   # score a setting on the val split
  python scripts/dataset/yoloworld_annotate.py             # archive 3 frames + archive 4 video and OLX images
Needs: ultralytics, CLIP (pip install git+https://github.com/ultralytics/CLIP.git), ftfy, regex.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from auto_annotate import iou  # noqa: E402
from common import ANNOT, PROCESSED, ROOT, SPLITS, imread, long_path, read_jsonl  # noqa: E402

VEHICLES = ["car", "truck", "bus", "motorcycle", "auto rickshaw"]
PLATE_PROMPTS = ["number plate", "license plate", "licence plate", "registration plate"]
DISTRACTORS = ["headlight", "logo", "grille", "wheel", "tail light", "bumper"]
TARGETS = ("archive (3)/", "archive (4)/video_images/", "archive (4)/State-wise_OLX/")


class Finder:
    """Two-step YOLO-World plate search."""

    def __init__(self, weights: str, device: str):
        from ultralytics import YOLOWorld

        self.device = device
        self.vehicles = YOLOWorld(str(ROOT / weights))
        self.vehicles.set_classes(VEHICLES)
        self.plates = YOLOWorld(str(ROOT / weights))
        self.plates.set_classes(PLATE_PROMPTS + DISTRACTORS)

    def candidates(self, img, imgsz: int) -> list[list[float]]:
        """[x1, y1, x2, y2, conf, crop_index] in image pixels; at most 5 per crop."""
        height, width = img.shape[:2]
        res = self.vehicles.predict(img, imgsz=imgsz, conf=0.15, agnostic_nms=True, device=self.device,
                                    verbose=False)[0]
        crops = [(0, 0, width, height)]
        for x1, y1, x2, y2 in [b.xyxy[0].tolist() for b in res.boxes][:6]:
            crops.append((int(x1), int(y1), int(x2), int(y2)))
            crops.append((int(x1), int(y1 + 0.45 * (y2 - y1)), int(x2), int(y2)))
        crops = [c for c in crops if c[2] - c[0] >= 20 and c[3] - c[1] >= 20]
        out: list[list[float]] = []
        for k, (ox, oy, ox2, oy2) in enumerate(crops):
            r = self.plates.predict(img[oy:oy2, ox:ox2], imgsz=imgsz, conf=0.001, iou=0.5, max_det=100,
                                    device=self.device, verbose=False)[0]
            found = []
            for b in r.boxes:
                if int(b.cls[0]) >= len(PLATE_PROMPTS):
                    continue
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                w, h = x2 - x1, y2 - y1
                if h <= 0 or not 0.7 <= w / h <= 8:
                    continue
                if w * h > 0.35 * (ox2 - ox) * (oy2 - oy) or w * h > 0.4 * width * height:
                    continue
                found.append([x1 + ox, y1 + oy, x2 + ox, y2 + oy, float(b.conf[0]), k])
            kept: list[list[float]] = []
            for d in sorted(found, key=lambda d: -d[4]):
                if all(iou(d[:4], q[:4]) < 0.5 for q in kept):
                    kept.append(d)
            out += kept[:5]
        return out


def select(cands: list[list[float]], conf: float, topk: int) -> list[list[float]]:
    """Best topk candidates of each crop above conf, merged across crops."""
    per_crop: dict[float, int] = {}
    picked: list[list[float]] = []
    for d in sorted(cands, key=lambda d: -d[4]):
        if d[4] < conf or per_crop.get(d[5], 0) >= topk:
            continue
        per_crop[d[5]] = per_crop.get(d[5], 0) + 1
        if all(iou(d[:4], q[:4]) < 0.4 for q in picked):
            picked.append(d)
    return picked


def match(human: list[list[float]], dets: list[list[float]]) -> tuple[list[float], int]:
    """IoU of each matched human box (greedy by confidence), and the number of unmatched detections."""
    used: dict[int, float] = {}
    extra = 0
    for d in dets:
        best, j = max(((iou(d[:4], g), j) for j, g in enumerate(human) if j not in used), default=(0.0, -1))
        if best >= 0.5:
            used[j] = best
        else:
            extra += 1
    return list(used.values()), extra


def score(rows: list[tuple[list, list]]) -> tuple[float, float, float]:
    """(precision, recall, F1) for a list of (human boxes, detections)."""
    matched = human = found = 0
    for boxes, dets in rows:
        ious, extra = match(boxes, dets)
        matched += len(ious)
        human += len(boxes)
        found += len(ious) + extra
    p, r = matched / max(found, 1), matched / max(human, 1)
    return p, r, 2 * p * r / max(p + r, 1e-9)


def tune(a: argparse.Namespace) -> None:
    split = json.loads((SPLITS / f"split_{a.split}.json").read_text())["split"]
    val = [r for r in read_jsonl(PROCESSED / "records_labeled.jsonl") if split.get(r["id"]) == "val"]
    out = ANNOT / "yoloworld"
    out.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    # run one process per setting on a 4 GB card; results accumulate in tuning_val.json
    saved = out / "tuning_val.json"
    if saved.exists():
        results = [x for x in json.loads(saved.read_text())["all"]
                   if (x["weights"], x["imgsz"]) != (a.weights, a.imgsz)]
    finder = Finder(a.weights, a.device)
    t0 = time.time()
    data = [(r["boxes"], finder.candidates(imread(ROOT / r["path"]), a.imgsz)) for r in val]
    for topk in (1, 2):
        for conf in (0.001, 0.003, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1):
            p, rec, f1 = score([(b, select(c, conf, topk)) for b, c in data])
            results.append({"weights": a.weights, "imgsz": a.imgsz, "topk": topk, "conf": conf,
                            "precision": round(p, 4), "recall": round(rec, 4), "f1": round(f1, 4)})
    mine = max((x for x in results if (x["weights"], x["imgsz"]) == (a.weights, a.imgsz)), key=lambda x: x["f1"])
    print(f"{a.weights} {a.imgsz}: {(time.time() - t0) / len(val):.2f}s/img best {mine}", flush=True)
    top = max(results, key=lambda x: x["f1"])
    saved.write_text(json.dumps({"split": a.split, "images": len(val), "best": top, "all": results}, indent=1))
    print("BEST so far", top, flush=True)


def summary(rows: list[dict]) -> dict:
    matched = sum(r["matched"] for r in rows)
    human = sum(r["human_boxes"] for r in rows)
    found = matched + sum(r["extra"] for r in rows)
    ious = [v for r in rows for v in r["ious"]]
    return {"images": len(rows), "human_boxes": human, "yoloworld_boxes": found, "matched": matched,
            "recall_vs_human": round(matched / max(human, 1), 4),
            "precision_vs_human": round(matched / max(found, 1), 4),
            "mean_iou_of_matches": round(sum(ious) / max(len(ious), 1), 4),
            "status": dict(collections.Counter(r["status"] for r in rows))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--split", default="v5")
    ap.add_argument("--device", default="0")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--weights", default="weights/yolov8l-worldv2.pt", help="used by --tune")
    ap.add_argument("--imgsz", type=int, default=640, help="used by --tune")
    a = ap.parse_args()
    if a.tune:
        tune(a)
        return
    out = ANNOT / "yoloworld"
    best = json.loads((out / "tuning_val.json").read_text())["best"]
    settings = [best["weights"], best["imgsz"]]

    recs = [r for r in read_jsonl(PROCESSED / "records_labeled.jsonl")
            if r["path"].startswith(TARGETS) and "excluded" not in r["extra"]]
    if a.limit:
        recs = recs[: a.limit]
    done: dict[str, dict] = {}
    log = out / "detections.jsonl"
    if log.exists():  # resume: skip images already processed with the same settings
        for row in read_jsonl(log):
            if row["settings"] == settings:
                done[row["id"]] = row

    finder = Finder(best["weights"], a.device)
    t0, rows = time.time(), []
    with log.open("w", encoding="utf-8") as f:
        for k, r in enumerate(recs, 1):
            row = done.get(r["id"])
            if row is None:
                img = imread(ROOT / r["path"])
                if img is None:
                    print("unreadable", r["path"], flush=True)
                    continue
                row = {"id": r["id"], "path": r["path"], "width": img.shape[1], "height": img.shape[0],
                       "settings": settings, "candidates": finder.candidates(img, best["imgsz"])}
            keep = select(row["candidates"], best["conf"], best["topk"])
            ious, extra = match(r["boxes"], keep)
            if not ious:
                status = "missed"
            elif len(ious) < len(r["boxes"]):
                status = "partial"
            else:
                status = "extra" if extra else "agree"
            row.update(status=status, matched=len(ious), human_boxes=len(r["boxes"]), extra=extra, ious=ious)
            f.write(json.dumps(row) + "\n")
            f.flush()
            rows.append(row)
            w, h = row["width"], row["height"]
            txt = out / "labels" / Path(r["path"]).with_suffix(".txt")
            Path(long_path(txt.parent)).mkdir(parents=True, exist_ok=True)
            Path(long_path(txt)).write_text("".join(
                f"0 {(d[0] + d[2]) / 2 / w:.6f} {(d[1] + d[3]) / 2 / h:.6f} {(d[2] - d[0]) / w:.6f} "
                f"{(d[3] - d[1]) / h:.6f} {d[4]:.4f}\n" for d in keep))
            if k % 200 == 0:
                print(f"{k}/{len(recs)}  {(time.time() - t0) / 60:.1f} min", flush=True)

    groups: dict[str, list] = collections.defaultdict(list)
    for r in rows:
        groups["/".join(r["path"].split("/")[: 1 if r["path"].startswith("archive (3)") else 2])].append(r)
    report = {"settings": best, "prompts": PLATE_PROMPTS, "distractors": DISTRACTORS, "all": summary(rows),
              "by_source": {g: summary(v) for g, v in sorted(groups.items())}}
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
