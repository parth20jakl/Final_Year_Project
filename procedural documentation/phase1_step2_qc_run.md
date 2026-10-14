# Phase 1, Step 2 - Dataset QC (2026-10-05, Local)

## Goal
Run the automated QC checks on the exported dataset and report quality / leakage problems, without changing data.

## Steps followed
1. Command (repo root): `python scripts/dataset/qc.py --root dataset/processed/yolo_final`
2. Read `dataset/reports/yolo_final/dataset_statistics.json`; HTML report written to `dataset/reports/yolo_final/dataset_report.html`.

Checks performed by `qc.py`: missing images/labels, malformed or out-of-range boxes, bad class ids, zero-area boxes, unreadable images, per-split stats, plate-size distribution, near-duplicate detection (64-bit dHash) within and across splits.

## Results
| Item | Result |
|---|---|
| Errors (missing/orphan/malformed/bad class/zero-area/unreadable) | **none** (`errors: {}`) |
| Cross-split near-duplicates (leakage) | **0** |
| Near-duplicate pairs within a split | 3,921 |
| Images / plates: train | 10,568 / 10,957 |
| val | 281 / 315 (100% manual) |
| test | 281 / 306 (100% manual) |
| Train label provenance | manual 10,160, auto_accepted 408 |
| Images without plates | 0 in every split |
| Class counts | license_plate 11,578 |
| Plate area fraction (median) | train 2.1%, val 1.3%, test 1.6% |
| Small plates (< 0.5% of image) | train 1,710, val 81, test 69 |
| Plates per image | mostly 1; up to 7 in train |

## Findings
- Data is structurally clean and leakage-free by the dHash test (consistent with the `split.py` assertions).
- 3,921 near-duplicate pairs inside splits (video frames and external sources) mean the number of *independent* images is lower than 10.5k. This matters for the Phase 1 exit criterion (>= ~6-10k independent images); it is not yet measured per source.
- Val/test are small (281 each, Indian only), so metric confidence intervals will be wide.
- Smaller plates in val/test than train (median area 1.3-1.6% vs 2.1%): evaluation is harder than training distribution.
- Only 408 of the auto-labeled pool were accepted into train.

## Outputs
`dataset/reports/yolo_final/dataset_statistics.json`, `dataset_report.html`. No data changed.

## Reproduce
`python scripts/dataset/qc.py --root dataset/processed/yolo_final`
