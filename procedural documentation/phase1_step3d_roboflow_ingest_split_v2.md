# Phase 1, Step 3d - Ingest Roboflow sets, create split v2 (2026-10-14, Local)

Decision basis: user asked to continue through Phases 0-1 without per-step prompts; I used the recommended policy "train-only, keep val/test unchanged".

## Goal
Add the 4 downloaded CC BY 4.0 Indian sets to the labeled pool without disturbing the frozen val/test sets.

## Steps followed
1. Read `ingest.py`, `split.py`, `export_yolo.py`, `common.py` to see how records, domains and splits are used.
2. Constraint found: re-running `ingest.py` would rebuild from archives no longer on disk and lose the 32 restored images -> wrote an **incremental** script `scripts/dataset/ingest_roboflow.py` instead.
3. Constraint found: `split.py` sends any mixed (Indian + external) near-duplicate component to train, which could silently pull existing val/test images into train and re-shuffle the split. So v2 is built by carrying v1 assignments forward unchanged and adding new images to train only.
4. Script rules: keep only plate classes from each `data.yaml` (drops `vehicle` in rf_vlp); ignore Roboflow splits; convert YOLO txt -> pixel xyxy; validate boxes; drop any image within dHash Hamming <= 4 of an existing val/test image; `domain = indian_external` (not "indian", so `split.py`/`export_yolo --manual-only-indian` treat it as train-only); group = set + source stem; license "CC BY 4.0".
5. Backed up `records_labeled.jsonl` -> `records_labeled.jsonl.bak_pre_roboflow`, appended new rows, wrote `dataset/splits/split_v2.json`, log `dataset/reports/ingest_roboflow_log.json`.
6. Ran: `python scripts/dataset/ingest_roboflow.py`.

## Results
| Item | Count |
|---|---|
| Added to train | **2,704** (rf_nivu 1,209; rf_ilpd_khhkb 833; rf_i5hub 428; rf_vlp 234) |
| Dropped: near-duplicate of existing val/test image | **552** |
| Dropped: no plate-class box | 226 (mostly rf_vlp vehicle-only images) |
| Labeled by split v2 | train 12,864 / val 281 / test 281 |

## Findings
- 552 of the new images (16%) are near-copies of our own val/test images: the Roboflow sets share sources with our archives. Dropping them prevents train/test leakage; without this check the test score would have been inflated.
- Remaining Roboflow images may still near-duplicate our *train* images; harmless for leakage, but they reduce the number of independent images (measured in the QC step).
- Val/test unchanged (281 / 281), so earlier numbers remain comparable.

## Outputs / reproduce
`scripts/dataset/ingest_roboflow.py`, `dataset/splits/split_v2.json`, `dataset/reports/ingest_roboflow_log.json`. The script refuses to run twice (guard on `rf_` sources); restore the `.bak_pre_roboflow` file to redo.
