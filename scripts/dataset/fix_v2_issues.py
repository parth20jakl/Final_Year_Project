"""Fixes found by QC of yolo_v2 (2026-10-14).

1. Recovered-from-export images are downscaled (max side 1280) but their records kept original-resolution
   width/height/boxes -> rescale records (and recognition bboxes) to the file actually on disk.
2. Roboflow train images that are near-duplicates (dHash Hamming <= --hd2, default 8, looser than ingest's 4 because
   QC hashes the re-encoded export) of a val/test image are excluded in split_v2 (split value 'excluded').
Backups: *.bak_pre_fixv2
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import ANNOT, PROCESSED, REPORTS, ROOT, SPLITS, imread, read_jsonl, write_jsonl  # noqa: E402
from split import popcount64  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hd2", type=int, default=8)
    a = ap.parse_args()
    log = {"rescaled": [], "excluded": []}
    scale: dict[str, float] = {}
    for name in ("records_labeled", "records_auto", "records_unlabeled"):
        f = PROCESSED / f"{name}.jsonl"
        rows = read_jsonl(f)
        changed = False
        for r in rows:
            if not r.get("extra", {}).get("recovered_from_export") or r.get("extra", {}).get("rescaled_to_export_size"):
                continue
            im = imread(ROOT / r["path"])
            h, w = im.shape[:2]
            if (w, h) == (r["width"], r["height"]):
                continue
            sx, sy = w / r["width"], h / r["height"]
            r["boxes"] = [[b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy] for b in r["boxes"]]
            log["rescaled"].append({"file": name, "id": r["id"], "from": [r["width"], r["height"]], "to": [w, h]})
            r["width"], r["height"] = w, h
            r["extra"]["rescaled_to_export_size"] = True
            scale[r["id"]] = (sx, sy)
            changed = True
        if changed:
            shutil.copy2(f, f.with_suffix(".jsonl.bak_pre_fixv2"))
            write_jsonl(f, rows)
    rf = ANNOT / "recognition_manual.jsonl"
    rows = read_jsonl(rf)
    if scale:
        shutil.copy2(rf, rf.with_suffix(".jsonl.bak_pre_fixv2"))
        for t in rows:
            if t["image_id"] in scale:
                sx, sy = scale[t["image_id"]]
                b = t["bbox"]
                t["bbox"] = [b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy]
        write_jsonl(rf, rows)

    sp_path = SPLITS / "split_v2.json"
    v2 = json.loads(sp_path.read_text())
    sp = v2["split"]
    lab = read_jsonl(PROCESSED / "records_labeled.jsonl")
    hold = np.array([int(r["dhash"], 16) for r in lab if sp.get(r["id"]) in ("val", "test")], dtype=np.uint64)
    for r in lab:
        if r["source"].startswith("rf_") and sp.get(r["id"]) == "train":
            if (popcount64(hold ^ np.uint64(int(r["dhash"], 16))) <= a.hd2).any():
                sp[r["id"]] = "excluded"
                log["excluded"].append(r["id"])
    v2["note"] += f"; {len(log['excluded'])} more Roboflow images excluded as near-dups (hd<={a.hd2}) of val/test"
    shutil.copy2(sp_path, sp_path.with_suffix(".json.bak_pre_fixv2"))
    sp_path.write_text(json.dumps(v2, indent=1))
    (REPORTS / "fix_v2_issues_log.json").write_text(json.dumps(log, indent=1))
    print(len(log["rescaled"]), "rescaled;", len(log["excluded"]), "excluded")


if __name__ == "__main__":
    main()
