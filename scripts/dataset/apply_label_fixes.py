"""Apply hand-checked box corrections and write the next split.

Input: dataset/annotations/label_fixes_v5.json
  {"<image_id>": {"keep": [[x1,y1,x2,y2], ...], "why": "..."}}
  keep = the complete new box list for that image; [] = no usable plate, the image is excluded.

Edits records_labeled.jsonl / records_auto.jsonl / recognition_manual.jsonl (backups: *.bak_pre_v5, written once)
and writes split_v5.json = split_v4 minus excluded images, minus ids that no longer have a record.
Safe to run again.

  python scripts/dataset/apply_label_fixes.py
"""
from __future__ import annotations

import collections
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ANNOT, PROCESSED, SPLITS, box_ok, norm_text, read_jsonl, write_jsonl  # noqa: E402

NOT_PLATE_TEXT = {"BLUR", "DEVANAGRI", "TERRANO", "DUSTER", "CRETA"}


def backup(path: Path) -> None:
    b = path.with_suffix(path.suffix + ".bak_pre_v5")
    if not b.exists():
        shutil.copy2(path, b)


def main() -> None:
    fixes = json.loads((ANNOT / "label_fixes_v5.json").read_text(encoding="utf-8"))
    excluded = {i for i, f in fixes.items() if not f["keep"]}
    seen: set[str] = set()
    all_ids: set[str] = set()
    count = collections.Counter()

    for name in ("records_labeled.jsonl", "records_auto.jsonl"):
        path = PROCESSED / name
        rows = read_jsonl(path)
        backup(path)
        for r in rows:
            all_ids.add(r["id"])
            f = fixes.get(r["id"])
            if not f:
                continue
            seen.add(r["id"])
            if not f["keep"]:
                r["extra"]["excluded"] = f["why"]
                if name == "records_auto.jsonl":
                    r["label_source"] = "rejected"
                count["excluded"] += 1
                continue
            for b in f["keep"]:
                if not box_ok(b, r["width"], r["height"]):
                    sys.exit(f"bad box for {r['id']}: {b} in {r['width']}x{r['height']}")
            texts = {tuple(round(v) for v in b): t for b, t in zip(r["boxes"], r["plate_texts"])}
            r["plate_texts"] = [texts.get(tuple(round(v) for v in b), "") for b in f["keep"]]
            r["boxes"] = f["keep"]
            r["extra"]["label_fix"] = f["why"]
            if name == "records_auto.jsonl" and r["label_source"] in ("auto_accepted", "review_pending", "rejected"):
                r["label_source"] = "auto_reviewed"
            count["corrected"] += 1
        write_jsonl(path, rows)
    unknown = set(fixes) - seen
    if unknown:
        sys.exit(f"no record for: {sorted(unknown)}")

    rec = ANNOT / "recognition_manual.jsonl"
    rows = read_jsonl(rec)
    backup(rec)
    text_key = next(k for k in ("text", "plate_text", "plate") if rows and k in rows[0])
    kept_boxes = {i: {tuple(round(v) for v in b) for b in f["keep"]} for i, f in fixes.items()}
    keep = [x for x in rows
            if (x["image_id"] not in fixes or tuple(round(v) for v in x["bbox"]) in kept_boxes[x["image_id"]])
            and norm_text(re.sub(r"\s", "", x[text_key])) not in NOT_PLATE_TEXT]
    count["recognition_rows_removed"] = len(rows) - write_jsonl(rec, keep)

    v4 = json.loads((SPLITS / "split_v4.json").read_text())
    split = {}
    for i, s in v4["split"].items():
        if s in ("train", "val", "test", "pool") and (i in excluded or i not in all_ids):
            if s != "pool":
                count[f"left_{s}"] += 1
                s = "excluded"
        split[i] = s
    v5 = {**v4, "version": "v5", "parent": "v4", "split": split,
          "stats": {"all_by_split": dict(collections.Counter(split.values()))},
          "note": "v4 with corrected boxes; images without a usable plate and deleted images excluded (2026-11-28)"}
    (SPLITS / "split_v5.json").write_text(json.dumps(v5, indent=1))
    print(json.dumps({**count, "split": v5["stats"]["all_by_split"]}, indent=1))


if __name__ == "__main__":
    main()
