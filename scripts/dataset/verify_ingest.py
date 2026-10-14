"""Verify ingest output (Phase 1 step 1): files exist, boxes valid, ids unique, groups set, recognition rows linked."""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ANNOT, PROCESSED, REPORTS, ROOT, box_ok, long_path, read_jsonl  # noqa: E402

import os  # noqa: E402


def main() -> int:
    lab = read_jsonl(PROCESSED / "records_labeled.jsonl")
    unl = read_jsonl(PROCESSED / "records_unlabeled.jsonl")
    rec = read_jsonl(ANNOT / "recognition_manual.jsonl")
    issues: dict[str, list] = collections.defaultdict(list)
    ids = collections.Counter(r["id"] for r in lab + unl)
    issues["duplicate_ids"] = [i for i, c in ids.items() if c > 1][:20]
    by_id = {r["id"]: r for r in lab}
    for r in lab + unl:
        if not os.path.exists(long_path(ROOT / r["path"])):
            issues["missing_image"].append(r["id"])
        if not r.get("group"):
            issues["no_group"].append(r["id"])
    for r in lab:
        if not r["boxes"]:
            issues["labeled_without_box"].append(r["id"])
        for b in r["boxes"]:
            if not box_ok(b, r["width"], r["height"]):
                issues["bad_box"].append(r["id"])
        if r.get("label_source") != "manual":
            issues["labeled_not_manual"].append(r["id"])
    for r in unl:
        if r["boxes"]:
            issues["unlabeled_with_box"].append(r["id"])
    for t in rec:
        src = by_id.get(t["image_id"])
        if src is None:
            issues["recognition_orphan"].append(t["image_id"])
        elif not any(list(map(float, t["bbox"])) == list(map(float, b)) for b in src["boxes"]):
            issues["recognition_bbox_not_in_record"].append(t["image_id"])
    summary = {
        "labeled": len(lab), "unlabeled": len(unl), "recognition_rows": len(rec),
        "labeled_by_domain": dict(collections.Counter(r["domain"] for r in lab)),
        "labeled_by_source": dict(collections.Counter(r["source"] for r in lab)),
        "groups": len({r["group"] for r in lab}),
        "text_suspect": sum(1 for t in rec if t.get("text_suspect")),
        "issue_counts": {k: len(v) for k, v in issues.items()},
        "issue_examples": {k: v[:5] for k, v in issues.items()},
    }
    out = REPORTS / "verify_ingest.json"
    out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
