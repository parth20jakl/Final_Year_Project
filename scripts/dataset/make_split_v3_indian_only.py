"""Split v3 = Indian plates only (user decision 2026-10-14).

Rules
  * keremberke_roboflow_vrp (mixed countries, 8,823 imgs) -> excluded
  * every other manual / Roboflow-Indian record keeps its split_v2 assignment
  * auto-labelled pool (records_auto.jsonl): kept (train) only if ALL hold
      - exactly ONE box (user rule: single bbox around an Indian plate)
      - label_source auto_accepted | auto_reviewed (human-rejected ones stay out)
      - if the image is from IVDB cars_* / archive2 / recovered (mixed countries incl. California plates):
        it must also be in the human nationality decisions (dataset/annotations/nationality_keep.json)
Outputs: splits/split_v3.json, reports/split_v3_log.json
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ANNOT, PROCESSED, REPORTS, SPLITS, read_jsonl  # noqa: E402


def main() -> None:
    v2 = json.loads((SPLITS / "split_v2.json").read_text())
    sp = dict(v2["split"])
    lab = read_jsonl(PROCESSED / "records_labeled.jsonl")
    auto = read_jsonl(PROCESSED / "records_auto.jsonl")
    nat_order = json.loads((REPORTS / "nat_sheets" / "order.json").read_text())
    nat_keep = set(json.loads((ANNOT / "nationality_keep.json").read_text()))
    nat_checked = set(nat_order)
    log = collections.defaultdict(int)
    for r in lab:
        if r["source"] == "keremberke_roboflow_vrp":
            if sp.get(r["id"]) != "excluded":
                log["keremberke_excluded"] += 1
            sp[r["id"]] = "excluded"
    for r in auto:
        ok = (r["label_source"] in ("auto_accepted", "auto_reviewed") and len(r["boxes"]) == 1
              and (r["id"] not in nat_checked or r["id"] in nat_keep))
        if ok:
            sp[r["id"]] = "train"
            log["auto_kept"] += 1
        else:
            sp[r["id"]] = "excluded"
            why = ("rejected_in_review" if r["label_source"] == "rejected" else
                   "multi_box" if len(r["boxes"]) != 1 else "not_indian_or_unverified")
            log["auto_excluded_" + why] += 1
    v3 = {**v2, "version": "v3", "parent": "v2", "split": sp,
          "note": "Indian plates only: keremberke excluded; auto pool restricted to single-box, human-verified Indian plates"}
    counts = collections.Counter(sp.values())
    v3["stats"] = {"all_by_split": dict(counts)}
    (SPLITS / "split_v3.json").write_text(json.dumps(v3, indent=1))
    out = {"counts": dict(counts), "log": dict(log),
           "auto_kept_by_source": dict(collections.Counter(r["source"] for r in auto if sp[r["id"]] == "train"))}
    (REPORTS / "split_v3_log.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
