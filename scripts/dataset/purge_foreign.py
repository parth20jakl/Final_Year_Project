"""Permanently delete non-Indian plate data (user instruction 2026-11-27) and write split_v4.

Input: dataset/annotations/foreign_ids.json  {"<image_id>": "<reason>"}  (human visual review)
Also removes the mixed-country keremberke download and the superseded exports that contain it.

  python scripts/dataset/purge_foreign.py               # dry run: report only, writes nothing
  python scripts/dataset/purge_foreign.py --split-only  # write split_v4.json; deletes nothing
  python scripts/dataset/purge_foreign.py --apply       # delete (not reversible)
  python scripts/dataset/purge_foreign.py --ids foreign_ids_round2.json --apply   # a later review round

--apply also removes the records and recognition rows of deleted images (backups: *.bak_pre_purge).
split_v4 = split_v3 with every listed id marked 'excluded'; it is never overwritten once written (a frozen
dataset records its hash). The log lists every deleted file with its sha256.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ANNOT, PROCESSED, RAW, REPORTS, ROOT, SPLITS, long_path, read_jsonl, write_jsonl  # noqa: E402

RECORD_FILES = ("records_labeled.jsonl", "records_auto.jsonl", "records_unlabeled.jsonl")
OLD_DIRS = [RAW / "external" / "keremberke"] + [PROCESSED / n for n in ("yolo_manual", "yolo_final", "yolo_v2")]
OLD_FILES = [ROOT / "dataset" / "frozen" / "dataset_v2.zip"]
MIXED_SOURCE = "keremberke_roboflow_vrp"


def exists(p: Path) -> bool:
    return Path(long_path(p)).exists()


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(long_path(p), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_size(p: Path) -> tuple[int, int]:
    files = [q for q in p.rglob("*") if q.is_file()]
    return len(files), sum(q.stat().st_size for q in files)


def sidecars(img: Path, source: str) -> list[Path]:
    """Annotation files that belong to one source image (VOC XML next to it, or Roboflow YOLO txt)."""
    out = [img.with_suffix(".xml")]
    if source.startswith("rf_"):
        out.append(img.parent.parent / "labels" / f"{img.stem}.txt")
    return [p for p in out if exists(p)]


def write_split_v4(doomed: set[str]) -> None:
    out = SPLITS / "split_v4.json"
    if out.exists():
        print("split_v4.json already exists - left unchanged")
        return
    v3 = json.loads((SPLITS / "split_v3.json").read_text())
    split = dict(v3["split"])
    for i in doomed:
        if i in split:
            split[i] = "excluded"
    v4 = {**v3, "version": "v4", "parent": "v3", "split": split,
          "stats": {"all_by_split": dict(collections.Counter(split.values()))},
          "note": "v3 minus non-Indian images found in the 2026-11-27 visual audit"}
    out.write_text(json.dumps(v4, indent=1))
    print("wrote", out.name, v4["stats"]["all_by_split"])


def main() -> None:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--split-only", action="store_true")
    ap.add_argument("--ids", default="foreign_ids.json", help="id list in dataset/annotations (later rounds use their own file)")
    a = ap.parse_args()
    # later rounds keep their own backups and log so the first round's are not overwritten
    tag = "" if a.ids == "foreign_ids.json" else "_" + Path(a.ids).stem

    foreign: dict[str, str] = json.loads((ANNOT / a.ids).read_text(encoding="utf-8"))
    tables = {n: read_jsonl(PROCESSED / n) for n in RECORD_FILES}
    doomed = set(foreign)
    doomed |= {r["id"] for rows in tables.values() for r in rows if r["source"] == MIXED_SOURCE}
    known = {r["id"] for rows in tables.values() for r in rows}
    unknown = set(foreign) - known
    if unknown:
        sys.exit(f"ids not found in any record file: {sorted(unknown)[:10]}")

    doomed_paths = {r["path"] for rows in tables.values() for r in rows if r["id"] in doomed}
    kept_paths = {r["path"] for rows in tables.values() for r in rows if r["id"] not in doomed}
    shared = doomed_paths & kept_paths
    if shared:
        sys.exit(f"a kept record shares a file with a deleted one: {sorted(shared)[:5]}")
    old_roots = [d.resolve() for d in OLD_DIRS]
    for p in kept_paths:
        rp = (ROOT / p).resolve()
        if any(rp.is_relative_to(d) for d in old_roots):
            sys.exit(f"a kept record lives inside a folder to be deleted: {p}")

    source_of = {r["path"]: r["source"] for rows in tables.values() for r in rows if r["id"] in foreign}
    targets: list[Path] = []
    for p, src in sorted(source_of.items()):
        img = ROOT / p
        if exists(img):
            targets += [img, *sidecars(img, src)]
    for t in targets + OLD_DIRS + OLD_FILES:
        if not t.resolve().is_relative_to(ROOT):
            sys.exit(f"refusing to delete outside the repo: {t}")

    dirs = {d.relative_to(ROOT).as_posix(): tree_size(d) for d in OLD_DIRS if d.is_dir()}
    files = {f.relative_to(ROOT).as_posix(): f.stat().st_size for f in OLD_FILES if f.is_file()}
    by_source = collections.Counter(
        next(r["source"] for rows in tables.values() for r in rows if r["id"] == i) for i in foreign)
    summary = {
        "applied": a.apply,
        "foreign_images_listed": len(foreign),
        "foreign_by_source": dict(by_source),
        "foreign_by_reason": dict(collections.Counter(foreign.values())),
        "individual_files_to_delete": len(targets),
        "folders_to_delete": {k: {"files": n, "mb": round(s / 1e6, 1)} for k, (n, s) in dirs.items()},
        "files_to_delete_mb": {k: round(s / 1e6, 1) for k, s in files.items()},
        "records_removed": {n: sum(r["id"] in doomed for r in rows) for n, rows in tables.items()},
    }
    print(json.dumps(summary, indent=1))
    if a.split_only:
        write_split_v4(doomed)
    if not a.apply:
        return

    deleted = [{"path": t.relative_to(ROOT).as_posix(), "sha256": sha256(t)} for t in targets]
    for t in targets:
        Path(long_path(t)).unlink()
    version = PROCESSED / "yolo_v2" / "version.json"
    if version.exists():
        shutil.copy2(version, REPORTS / "yolo_v2" / "version.json")
    for d in OLD_DIRS:
        if d.is_dir():
            shutil.rmtree(long_path(d))
    for f in OLD_FILES:
        if f.is_file():
            f.unlink()

    for name, rows in tables.items():
        path = PROCESSED / name
        shutil.copy2(path, path.with_suffix(f".jsonl.bak_pre_purge{tag}"))
        write_jsonl(path, [r for r in rows if r["id"] not in doomed])
    rec = ANNOT / "recognition_manual.jsonl"
    rec_rows = read_jsonl(rec)
    shutil.copy2(rec, rec.with_suffix(f".jsonl.bak_pre_purge{tag}"))
    summary["recognition_rows_removed"] = len(rec_rows) - write_jsonl(
        rec, [r for r in rec_rows if r["image_id"] not in doomed])

    write_split_v4(doomed)
    (REPORTS / f"purge_foreign_log{tag}.json").write_text(
        json.dumps({"summary": summary, "foreign": foreign, "deleted_files": deleted}, indent=1))
    print("done; recognition rows removed:", summary["recognition_rows_removed"])


if __name__ == "__main__":
    main()
