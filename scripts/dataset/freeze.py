"""Freeze an exported dataset: write version.json (hashes, counts, QC summary, licences) and zip it for Colab.

Refuses to freeze when QC reports errors or cross-split near-duplicates.
  python scripts/dataset/freeze.py --tag v2 --name dataset_v2
Output: dataset/frozen/<name>.zip (contains <name>/{images,labels,anpr_detect.yaml,manifest.json,version.json}) + <name>.sha256
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import PROCESSED, REPORTS, ROOT, SPLITS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v2")
    ap.add_argument("--name", default="dataset_v2")
    a = ap.parse_args()
    src = PROCESSED / f"yolo_{a.tag}"
    qc = json.loads((REPORTS / f"yolo_{a.tag}" / "dataset_statistics.json").read_text())
    if qc["errors"] or qc["near_duplicate_pairs_across_splits"]:
        sys.exit(f"QC not clean: {qc['errors']} cross={qc['near_duplicate_pairs_across_splits']}")
    man = json.loads((src / "manifest.json").read_text())
    split_file = SPLITS / f"split_{man['split_version']}.json"
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        commit = "unknown"
    ver = {
        "name": a.name, "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "split_version": man["split_version"], "split_file_sha256": hashlib.sha256(split_file.read_bytes()).hexdigest(),
        "content_hash": man["content_hash"], "counts": man["counts"], "include_auto": man["include_auto"],
        "max_side": man["max_side"], "class_names": ["license_plate"], "git_commit": commit,
        "qc": {"near_duplicate_pairs_within_split": qc["near_duplicate_pairs_within_split"],
               "near_duplicate_pairs_across_splits": 0, "errors": {}},
        "licences": "mixed; see docs/licensing.md. Contains CC BY 4.0 data (attribution) and unknown-provenance / "
                    "non-commercial archives: NOT for redistribution.",
    }
    (src / "version.json").write_text(json.dumps(ver, indent=1))
    out = ROOT / "dataset" / "frozen"
    out.mkdir(parents=True, exist_ok=True)
    zp = out / f"{a.name}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:  # jpgs are already compressed
        for p in sorted(src.rglob("*")):
            if p.is_file():
                z.write(p, f"{a.name}/{p.relative_to(src).as_posix()}")
    h = hashlib.sha256()
    with open(zp, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    (out / f"{a.name}.sha256").write_text(f"{h.hexdigest()}  {zp.name}\n")
    print(json.dumps({"zip": str(zp), "size_mb": round(zp.stat().st_size / 1e6), "sha256": h.hexdigest(), **ver["counts"]}, indent=1))


if __name__ == "__main__":
    main()
