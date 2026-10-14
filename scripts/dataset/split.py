"""Leakage-safe split.

Images are linked when they share a group (plate text / sequence / roboflow source stem) OR are
near-duplicates (dHash Hamming <= --hd). Each connected component goes wholly into ONE split.

Policy
  * Indian-domain manual data  -> train/val/test 70/15/15 by component.
  * External-domain data       -> train only (keeps val/test Indian, gate-relevant).
  * Unlabeled images that duplicate a labeled image are dropped; remaining unlabeled -> 'pool'
    (auto-annotated later, train only).
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import PROCESSED, REPORTS, SPLITS, read_jsonl  # noqa: E402


def popcount64(x: np.ndarray) -> np.ndarray:
    x = x - ((x >> np.uint64(1)) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + ((x >> np.uint64(2)) & np.uint64(0x3333333333333333))
    x = (x + (x >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
    return (x * np.uint64(0x0101010101010101)) >> np.uint64(56)


class DSU:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, a: int) -> int:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--hd", type=int, default=4, help="max dHash Hamming distance to call near-duplicate")
    ap.add_argument("--ratios", type=float, nargs=3, default=(0.70, 0.15, 0.15))
    ap.add_argument("--version", default="v1")
    a = ap.parse_args()

    lab = read_jsonl(PROCESSED / "records_labeled.jsonl")
    unl = read_jsonl(PROCESSED / "records_unlabeled.jsonl")
    allr = lab + unl
    n = len(allr)
    h = np.array([int(r["dhash"], 16) for r in allr], dtype=np.uint64)
    dsu = DSU(n)

    by_group = {}
    for i, r in enumerate(allr):
        g = r["group"]
        if g in by_group:
            dsu.union(by_group[g], i)
        else:
            by_group[g] = i
    n_pairs = 0
    for i in range(n):  # vectorised near-dup search, O(n^2/2) in numpy
        d = popcount64(h[i + 1:] ^ h[i])
        for j in np.nonzero(d <= a.hd)[0]:
            dsu.union(i, i + 1 + int(j))
            n_pairs += 1

    comps = collections.defaultdict(list)
    for i in range(n):
        comps[dsu.find(i)].append(i)

    nl = len(lab)
    dropped_unl, pool = [], []
    comp_items = []
    for c, idx in comps.items():
        labeled_idx = [i for i in idx if i < nl]
        unl_idx = [i for i in idx if i >= nl]
        if labeled_idx:
            dropped_unl += [allr[i]["id"] for i in unl_idx]  # unlabeled duplicate of a labeled image
            comp_items.append(labeled_idx)
        else:
            pool += [allr[i]["id"] for i in unl_idx]

    rng = random.Random(a.seed)
    split: dict[str, str] = {}
    indian = [c for c in comp_items if all(allr[i]["domain"] == "indian" for i in c)]
    external = [c for c in comp_items if c not in indian]
    for c in external:
        for i in c:
            split[allr[i]["id"]] = "train"
    total = sum(len(c) for c in indian)
    names = ["train", "val", "test"]
    target = {s: r * total for s, r in zip(names, a.ratios)}
    cur = {s: 0 for s in names}
    rng.shuffle(indian)
    indian.sort(key=len, reverse=True)
    for c in indian:
        s = max(names, key=lambda k: (target[k] - cur[k]) / target[k])
        for i in c:
            split[allr[i]["id"]] = s
        cur[s] += len(c)
    for pid in pool:
        split[pid] = "pool"

    # ---- leakage verification --------------------------------------------------
    comp_split = collections.defaultdict(set)
    for i, r in enumerate(allr):
        if r["id"] in split:
            comp_split[dsu.find(i)].add(split[r["id"]])
    leaks = [c for c, s in comp_split.items() if len({x for x in s if x != "pool"}) > 1]
    assert not leaks, f"leakage in {len(leaks)} components"
    gsplit = collections.defaultdict(set)
    for r in lab:
        gsplit[r["group"]].add(split[r["id"]])
    assert all(len(v) == 1 for v in gsplit.values()), "group crosses splits"

    out = {
        "version": a.version, "seed": a.seed, "dhash_hamming_threshold": a.hd, "ratios": a.ratios,
        "split": split,
        "stats": {
            "labeled_by_split": dict(collections.Counter(split[r["id"]] for r in lab)),
            "indian_by_split": dict(collections.Counter(split[allr[i]["id"]] for c in indian for i in c)),
            "unlabeled_pool": len(pool), "unlabeled_dropped_as_duplicates_of_labeled": len(dropped_unl),
            "near_duplicate_pairs": n_pairs, "components": len(comps), "leaky_components": 0,
        },
        "dropped_unlabeled_ids": dropped_unl,
    }
    SPLITS.mkdir(parents=True, exist_ok=True)
    (SPLITS / f"split_{a.version}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["stats"], indent=1))


if __name__ == "__main__":
    main()
