"""Dataset QC for an exported YOLO dataset -> dataset_statistics.json + dataset_report.html.

Checks: missing image/label pairs, unreadable images, malformed label lines, bad class ids, out-of-range /
zero-area boxes, exact + near duplicates (within and ACROSS splits = leakage), class counts, plate-size
and resolution distributions, per-split / per-source counts. Exit code 1 if any hard error is found.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import PROCESSED, REPORTS, ROOT, dhash, hamming, imread, read_jsonl  # noqa: E402


def pct(a, q):
    return round(float(np.percentile(a, q)), 5) if len(a) else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="dataset/processed/yolo_manual")
    ap.add_argument("--out", default="")
    ap.add_argument("--hd", type=int, default=4)
    a = ap.parse_args()
    base = ROOT / a.root
    out_dir = REPORTS / (a.out or base.name)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = {r["id"]: r for r in read_jsonl(PROCESSED / "records_labeled.jsonl")}
    for p in (PROCESSED / "records_auto.jsonl",):
        if p.exists():
            src.update({r["id"]: r for r in read_jsonl(p)})

    errors: dict[str, list] = collections.defaultdict(list)
    stats: dict = {"root": a.root, "splits": {}}
    hashes: dict[str, list[tuple[str, str]]] = {}
    for split in ("train", "val", "test"):
        imgs = {p.stem: p for p in (base / "images" / split).glob("*.jpg")}
        lbls = {p.stem: p for p in (base / "labels" / split).glob("*.txt")}
        for k in set(imgs) - set(lbls):
            errors["missing_label"].append(f"{split}/{k}")
        for k in set(lbls) - set(imgs):
            errors["missing_image"].append(f"{split}/{k}")
        areas, ws, hs, nplates, empties = [], [], [], [], 0
        by_source: collections.Counter = collections.Counter()
        by_label_source: collections.Counter = collections.Counter()
        hl = []
        for k, ip in sorted(imgs.items()):
            im = imread(ip)
            if im is None:
                errors["unreadable_image"].append(f"{split}/{k}")
                continue
            h, w = im.shape[:2]
            ws.append(w)
            hs.append(h)
            hl.append((k, dhash(im)))
            rec = src.get(k, {})
            by_source[rec.get("source", "?")] += 1
            by_label_source[rec.get("label_source", "?")] += 1
            if k not in lbls:
                continue
            n = 0
            for ln, line in enumerate(lbls[k].read_text().splitlines(), 1):
                if not line.strip():
                    continue
                p = line.split()
                try:
                    if len(p) != 5:
                        raise ValueError("fields")
                    c, xc, yc, bw, bh = int(p[0]), *map(float, p[1:])
                except ValueError:
                    errors["malformed_line"].append(f"{split}/{k}:{ln}")
                    continue
                if c != 0:
                    errors["bad_class_id"].append(f"{split}/{k}:{ln}")
                if not (0 <= xc <= 1 and 0 <= yc <= 1 and 0 < bw <= 1 and 0 < bh <= 1):
                    errors["out_of_range"].append(f"{split}/{k}:{ln}")
                    continue
                if bw * w < 2 or bh * h < 2:
                    errors["tiny_or_zero_area"].append(f"{split}/{k}:{ln}")
                if xc - bw / 2 < -1e-4 or xc + bw / 2 > 1 + 1e-4 or yc - bh / 2 < -1e-4 or yc + bh / 2 > 1 + 1e-4:
                    errors["box_outside_image"].append(f"{split}/{k}:{ln}")
                areas.append(bw * bh)
                n += 1
            nplates.append(n)
            empties += n == 0
        hashes[split] = hl
        stats["splits"][split] = {
            "images": len(imgs), "plates": int(sum(nplates)), "images_without_plates": empties,
            "plates_per_image": dict(collections.Counter(nplates)), "by_source": dict(by_source),
            "by_label_source": dict(by_label_source),
            "resolution_px": {"w_p5_p50_p95": [pct(ws, 5), pct(ws, 50), pct(ws, 95)],
                              "h_p5_p50_p95": [pct(hs, 5), pct(hs, 50), pct(hs, 95)]},
            "plate_area_fraction": {"min": pct(areas, 0), "p10": pct(areas, 10), "p50": pct(areas, 50),
                                    "p90": pct(areas, 90), "max": pct(areas, 100)},
            "small_plates_lt_0.5pct_area": int(sum(x < 0.005 for x in areas)),
        }
    # duplicates (within split) and leakage (across splits) via dHash
    allh = [(s, k, int(h, 16)) for s, lst in hashes.items() for k, h in lst]
    arr = np.array([x[2] for x in allh], dtype=np.uint64)
    from split import popcount64  # noqa: E402
    cross, within = [], 0
    for i in range(len(allh)):
        d = popcount64(arr[i + 1:] ^ arr[i])
        for j in np.nonzero(d <= a.hd)[0]:
            jj = i + 1 + int(j)
            if allh[i][0] != allh[jj][0]:
                cross.append((allh[i][:2], allh[jj][:2]))
            else:
                within += 1
    stats["near_duplicate_pairs_within_split"] = within
    stats["near_duplicate_pairs_across_splits"] = len(cross)
    if cross:
        errors["cross_split_near_duplicate"] = [f"{x[0]} <-> {x[1]}" for x in cross[:200]]
    stats["errors"] = {k: len(v) for k, v in errors.items()}
    stats["error_examples"] = {k: v[:10] for k, v in errors.items()}
    stats["class_counts"] = {"license_plate": sum(s["plates"] for s in stats["splits"].values())}
    (out_dir / "dataset_statistics.json").write_text(json.dumps(stats, indent=1))
    rows = "".join(
        f"<tr><td>{s}</td><td>{v['images']}</td><td>{v['plates']}</td><td>{v['plate_area_fraction']['p50']}</td>"
        f"<td>{v['small_plates_lt_0.5pct_area']}</td><td>{v['by_source']}</td></tr>" for s, v in stats["splits"].items())
    (out_dir / "dataset_report.html").write_text(
        "<meta charset=utf-8><style>body{font:14px sans-serif;margin:24px}td,th{border:1px solid #ccc;padding:4px 8px}"
        "table{border-collapse:collapse}</style>"
        f"<h2>Dataset QC - {a.root}</h2><table><tr><th>split</th><th>images</th><th>plates</th><th>median plate area frac</th>"
        f"<th>plates &lt;0.5% area</th><th>sources</th></tr>{rows}</table>"
        f"<h3>Errors</h3><pre>{json.dumps(stats['errors'], indent=1)}</pre>"
        f"<h3>Leakage</h3>near-duplicate pairs across splits: <b>{len(cross)}</b>; within a split: {within}"
        f"<h3>Full JSON</h3><pre>{json.dumps(stats, indent=1)}</pre>")
    print(json.dumps({"errors": stats["errors"], "across_split_dups": len(cross),
                      "splits": {s: (v["images"], v["plates"]) for s, v in stats["splits"].items()}}, indent=1))
    hard = {k: v for k, v in stats["errors"].items() if k != "tiny_or_zero_area"}
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
