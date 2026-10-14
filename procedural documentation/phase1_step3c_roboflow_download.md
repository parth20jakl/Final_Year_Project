# Phase 1, Step 3c - Download Roboflow Indian sets (2026-10-05, Local)

## Goal
Download the four CC BY 4.0 Roboflow Universe Indian plate sets, as raw, training-only data.

## Steps followed
1. Wrote `scripts/dataset/download_roboflow.py` (uses `ROBOFLOW_API_KEY`, exports each set's latest version in `yolov8` format into `dataset/raw/external/roboflow/<name>/`, writes `download_log.json`).
2. First run reported "ok" but folders were empty: the script created the folder first and then called `download(..., overwrite=False)`, which silently skipped. Fixed to `overwrite=True`, deleted the empty folders, re-ran.
3. The process did not see the user-level env var (set after the shell started); the key was loaded for that process only from the user environment, never printed or written to a file.
4. Counted images per split and read `data.yaml` / `README.dataset.txt` for classes and licence.

## Results (all version 1, licence CC BY 4.0 in each README)
| Folder | Source | Train / valid / test | Total | Classes |
|---|---|---|---|---|
| rf_ilpd_khhkb | Indian License Plate Detection (holi-milan / license-plate-detection-khhkb) | 583 / 167 / 83 | 833 | license_plate |
| rf_nivu | nivu/indian-license-plate-knte7 | 1156 / 330 / 164 | 1,650 | indian_licence_plate |
| rf_i5hub | i5hub/indian-number-plate-keeo5-zllyl | 411 / 78 / 59 | 548 | number_plate |
| rf_vlp | vehicle-license-plate/indian-vehicle-plate | 351 / 100 / 0 | 451 | **2 classes: license plate (287 boxes in train), vehicle (147)** |
Totals match the Universe listing counts, so no augmented copies were added. Disk used: 173 MB.

## Findings / things to handle at ingest
- Class names differ across sets; all `plate` classes must map to `license_plate` (id 0). In rf_vlp the `vehicle` class (id 1) must be dropped.
- Roboflow's own train/valid/test split is ignored: these sets go entirely to our **train** pool; dedup against our Indian test/val is done by the dHash component split (`split.py`).
- Attribution is required for each set (add to final report/attribution doc).
- Images may overlap each other or our archives; near-duplicate handling happens in ingest/split.

## Outputs
`dataset/raw/external/roboflow/{rf_*}`, `download_log.json`, `scripts/dataset/download_roboflow.py`. Existing processed data untouched (not yet ingested).
