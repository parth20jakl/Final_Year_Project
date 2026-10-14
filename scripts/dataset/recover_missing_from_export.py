"""Phase 1 step 1 fix: restore raw images lost from disk (source zips deleted) from the yolo_final export.

Copies dataset/processed/yolo_final/images/<split>/<id>.jpg -> dataset/raw/recovered_from_export/<id>.jpg
and repoints `path` in the records files. Originals of ids with no export copy stay missing (logged).
Backups of every edited file are written next to it as *.bak_pre_recover.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import PROCESSED, RAW, REPORTS, ROOT, read_jsonl, rel, write_jsonl  # noqa: E402

FILES = [PROCESSED / n for n in ("records_labeled.jsonl", "records_unlabeled.jsonl", "records_auto.jsonl")]


def main() -> None:
    ids = set(json.loads((REPORTS / "missing_image_ids.json").read_text()))
    export = {p.stem: p for p in (PROCESSED / "yolo_final" / "images").rglob("*.jpg")}
    dst_dir = RAW / "recovered_from_export"
    dst_dir.mkdir(parents=True, exist_ok=True)
    restored, unrecoverable = {}, []
    for i in sorted(ids):
        if i in export:
            dst = dst_dir / f"{i}.jpg"
            shutil.copy2(export[i], dst)
            restored[i] = rel(dst)
        else:
            unrecoverable.append(i)
    for f in FILES:
        rows = read_jsonl(f)
        if not any(r["id"] in restored for r in rows):
            continue
        shutil.copy2(f, f.with_suffix(".jsonl.bak_pre_recover"))
        for r in rows:
            if r["id"] in restored:
                r["path"] = restored[r["id"]]
                r.setdefault("extra", {})["recovered_from_export"] = True
        write_jsonl(f, rows)
    (REPORTS / "recover_missing_log.json").write_text(
        json.dumps({"restored": restored, "unrecoverable": unrecoverable}, indent=1), encoding="utf-8")
    print(f"restored {len(restored)}, unrecoverable {len(unrecoverable)}")


if __name__ == "__main__":
    main()
