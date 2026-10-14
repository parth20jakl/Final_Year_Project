"""Incrementally ingest the downloaded Roboflow Indian sets (train-only) and create split v2 = v1 + new train.

Why incremental: re-running ingest.py would rebuild everything from archives that are no longer on disk.
Rules
  * only plate classes are kept (class name containing 'plate' / 'licen'); other classes (e.g. 'vehicle') dropped
  * Roboflow's own splits are ignored; every kept image goes to TRAIN
  * an image whose dHash is within --hd of any existing val/test image is dropped (keeps val/test frozen and leak-free)
  * domain = 'indian_external' (Indian plates, third-party source): train-only, never val/test
Outputs: appended rows in records_labeled.jsonl (backup *.bak_pre_roboflow), splits/split_v2.json, reports/ingest_roboflow_log.json
"""
from __future__ import annotations

import argparse
import collections
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import (  # noqa: E402
    IMG_EXT, PROCESSED, RAW, REPORTS, SPLITS, box_ok, clip_box, read_jsonl, write_jsonl,
)
from ingest import make_record  # noqa: E402
from split import popcount64  # noqa: E402

BASE = RAW / "external" / "roboflow"
LIC = "CC BY 4.0 (Roboflow Universe, attribution required)"


def plate_class_ids(yaml_path: Path) -> set[int]:
    names, ids, in_names = [], set(), False
    for line in yaml_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("names:"):
            in_names = True
            continue
        if in_names:
            if line.startswith("- "):
                names.append(line[2:].strip().strip("'\""))
            elif line.strip() and not line.startswith(" "):
                break
    for i, n in enumerate(names):
        if "plate" in n.lower() or "licen" in n.lower():
            ids.add(i)
    return ids


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hd", type=int, default=4)
    a = ap.parse_args()

    lab_path = PROCESSED / "records_labeled.jsonl"
    lab = read_jsonl(lab_path)
    if any(r["source"].startswith("rf_") for r in lab):
        sys.exit("roboflow records already ingested")
    v1 = json.loads((SPLITS / "split_v1.json").read_text())
    sp = v1["split"]
    hold = np.array([int(r["dhash"], 16) for r in lab if sp.get(r["id"]) in ("val", "test")], dtype=np.uint64)

    new, log = [], collections.defaultdict(list)
    seen_hash: list[int] = []
    for d in sorted(p for p in BASE.iterdir() if p.is_dir() and p.name.startswith("rf_")):
        keep = plate_class_ids(d / "data.yaml")
        for split in ("train", "valid", "test"):
            for lp in sorted((d / split / "labels").glob("*.txt")):
                ip = next((q for ext in IMG_EXT for q in [d / split / "images" / (lp.stem + ext)] if q.exists()), None)
                if ip is None:
                    log["no_image"].append(str(lp))
                    continue
                rows = [l.split() for l in lp.read_text().splitlines() if l.strip()]
                rows = [r for r in rows if len(r) == 5 and int(r[0]) in keep]
                if not rows:
                    log["no_plate_box"].append(ip.name)
                    continue
                rec = make_record("rf", d.name + "/" + split + "/" + ip.name, ip, d.name, LIC, [], [], "", "indian_external",
                                  extra={"orig_split": split})
                if rec is None:
                    log["unreadable"].append(ip.name)
                    continue
                boxes = []
                for _, xc, yc, w, h in rows:
                    xc, yc, w, h = (float(v) for v in (xc, yc, w, h))
                    b = clip_box([(xc - w / 2) * rec.width, (yc - h / 2) * rec.height,
                                  (xc + w / 2) * rec.width, (yc + h / 2) * rec.height], rec.width, rec.height)
                    if box_ok(b, rec.width, rec.height):
                        boxes.append(b)
                if not boxes:
                    log["invalid_box"].append(ip.name)
                    continue
                rec.boxes, rec.plate_texts = boxes, [""] * len(boxes)
                h64 = int(rec.dhash, 16)
                if len(hold) and (popcount64(hold ^ np.uint64(h64)) <= a.hd).any():
                    log["dropped_near_dup_of_val_test"].append(rec.id)
                    continue
                rec.group = f"{d.name}:{ip.stem.split('.rf.')[0].split('_jpg')[0]}"
                new.append(rec)

    shutil.copy2(lab_path, lab_path.with_suffix(".jsonl.bak_pre_roboflow"))
    write_jsonl(lab_path, lab + [r.__dict__ for r in new])
    split2 = dict(sp)
    for r in new:
        assert r.id not in split2
        split2[r.id] = "train"
    v2 = {**v1, "version": "v2", "split": split2, "parent": "v1",
          "note": "v1 assignments unchanged; Roboflow Indian sets added to train only; near-dups of val/test dropped"}
    v2["stats"] = dict(v1.get("stats", {}))
    v2["stats"]["labeled_by_split"] = dict(collections.Counter(split2[r["id"]] for r in lab + [x.__dict__ for x in new]))
    (SPLITS / "split_v2.json").write_text(json.dumps(v2, indent=1))
    summary = {
        "added": len(new), "by_set": dict(collections.Counter(r.source for r in new)),
        "dropped": {k: len(v) for k, v in log.items()},
        "labeled_by_split_v2": v2["stats"]["labeled_by_split"],
    }
    (REPORTS / "ingest_roboflow_log.json").write_text(json.dumps({"summary": summary, "details": log}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
