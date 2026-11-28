"""Copy reviewed Indian-plate images from archive (2)-(6) into one folder tree. Deletes nothing.

Input: dataset/annotations/archive_review.json  {"status": {"<archive path>": "plate" | "unclear" | "no_plate"}}
  plate    -> dataset/archive_dataset/archive_N/...
  unclear  -> dataset/archive_dataset_unclear/archive_N/...   (for the owner to check)
  no_plate -> not copied

Plate annotations shipped with archive 3 (YOLO .txt) and archive 4 (VOC .xml) are copied beside their images.
Archive 5 .xml files label vehicle types, not plates, so they are left behind.

  python scripts/dataset/extract_archive_dataset.py
"""
from __future__ import annotations

import collections
import csv
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ANNOT, ROOT, long_path  # noqa: E402

DEST = {"plate": ROOT / "dataset" / "archive_dataset", "unclear": ROOT / "dataset" / "archive_dataset_unclear"}
SIDECAR = {"3": ".txt", "4": ".xml"}


def copy(src: Path, dst: Path) -> None:
    Path(long_path(dst.parent)).mkdir(parents=True, exist_ok=True)
    shutil.copy2(long_path(src), long_path(dst))


def main() -> None:
    status: dict[str, str] = json.loads((ANNOT / "archive_review.json").read_text(encoding="utf-8"))["status"]
    missing = [p for p in status if not Path(long_path(ROOT / p)).exists()]
    if missing:
        sys.exit(f"{len(missing)} reviewed files are missing, e.g. {missing[:3]}")

    rows, count = [], collections.Counter()
    for path, state in sorted(status.items()):
        folder, _, rest = path.partition("/")
        n = re.fullmatch(r"archive \((\d)\)", folder).group(1)
        count[(n, state)] += 1
        if state not in DEST:
            rows.append((path, state, "", ""))
            continue
        out = DEST[state] / f"archive_{n}" / rest
        copy(ROOT / path, out)
        ann = ""
        side = (ROOT / path).with_suffix(SIDECAR[n]) if n in SIDECAR else None
        if side and Path(long_path(side)).exists():
            copy(side, out.with_suffix(side.suffix))
            ann = out.with_suffix(side.suffix).relative_to(ROOT).as_posix()
            count[(n, "annotation")] += 1
        rows.append((path, state, out.relative_to(ROOT).as_posix(), ann))

    classes = ROOT / "archive (3)"
    for f in classes.glob("*.txt"):
        copy(f, DEST["plate"] / "archive_3" / f.name)

    with (DEST["plate"] / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source_path", "status", "copied_to", "annotation"])
        w.writerows(rows)
    for key, v in sorted(count.items()):
        print(f"archive ({key[0]}) {key[1]}: {v}")


if __name__ == "__main__":
    main()
