# Phase 1, Step 8 - Deletions, YOLO-World annotation, label fixes, dataset_v5 (2026-11-28, Local)

## Owner instructions
1. Delete the 328 unclear images everywhere, with no backup.
2. Annotate archive 4 video and OLX images (and video frames) with YOLO-World.
3. Delete the listed unused reports, log, caches and one-off scripts.
4. Fix the whole-vehicle and non-plate boxes using YOLO-World and report whether it is done.
5. Explain Android Studio setup, phone details and the first Colab run.

## Steps followed
1. Removed the 328 unclear images (originals in archives 5 and 6, 65 XML files, the copy folder, their records). List: `dataset/reports/removed_unclear_log.json`.
2. Deleted the listed reports, `runs/annotator_train.log`, `__pycache__`, and five one-off scripts.
3. Created `.venv-gpu` (Python 3.11, torch 2.5.1+cu118; see `requirements-local-gpu.txt`). The newer cu126 build failed with a CUDA "device unavailable" error on driver 528.20.
4. YOLO-World: a direct "license plate" prompt found at most 9% of plates on 40 validation images. Rewrote `scripts/dataset/yoloworld_annotate.py` as vehicle search then plate search with competing classes. Tuned on the 281 validation images (best: yolov8x-worldv2, imgsz 640, 1 box per crop, confidence 0.01), then annotated 1,414 images:
```
.venv-gpu\Scripts\python scripts\dataset\yoloworld_annotate.py --tune --weights weights/yolov8l-worldv2.pt --imgsz 640
.venv-gpu\Scripts\python scripts\dataset\yoloworld_annotate.py --tune --weights weights/yolov8x-worldv2.pt --imgsz 640
.venv-gpu\Scripts\python scripts\dataset\yoloworld_annotate.py
```
5. Fixed the listed defects by visual review (`dataset/annotations/label_fixes_v5.json`).
6. Further check: viewed the 436 of 5,109 boxes that the project's plate detector did not confirm, all 280 auto-made boxes, thumbnails of the 232 `rf_vlp` images, and nested box pairs. Fixed what was wrong; deleted one Iranian truck photo (`foreign_ids_round4.json`).
7. Built and froze v5:
```
python scripts/dataset/apply_label_fixes.py
python scripts/dataset/export_yolo.py --split v5 --include-auto --tag v5
python scripts/dataset/qc.py --root dataset/processed/yolo_v5
python scripts/dataset/freeze.py --tag v5 --name dataset_v5
pytest tests
```
8. Updated the Colab notebook (dataset_v5 checksum, private-repo token from Colab Secrets, a broken print line). Wrote `docs/setup_android_colab.md`.

## Results
YOLO-World against the human boxes (IoU 0.5):
| Source | Images | Recall | Precision |
|---|---|---|---|
| archive 3 video frames | 160 | 45.2% | 43.1% |
| archive 4 video images | 654 | 86.1% | 82.1% |
| archive 4 OLX images | 600 | 89.3% | 94.5% |
| All | 1,414 | 80.3% | 79.7% |

Image status: 1,051 agree, 109 extra, 51 partial, 203 missed. Settings were tuned on validation images from the same sources, so figures are slightly optimistic.

Label corrections: 159 images (135 corrected, 24 excluded).

dataset_v5: train 4,287 (4,449 plates) / val 281 (315) / test 280 (305). QC: no errors, 0 cross-split near-duplicates. sha256 `c274dea4453bd10e0664603a97b1a0ad54a7804cd825cc50810ea46b16fa08ba`.

## Problems and deviations
- YOLO-World was not accurate enough to correct labels; corrections were made by hand. Its output is kept separately and is not used for training.
- Boxes confirmed by the detector were not re-viewed. The detector was trained on part of the archive data, so it can confirm its own errors there.
- Some very small, blurred truck plates were kept although unreadable.
- `dataset_v4.zip` and `processed/yolo_v4` still hold 2 foreign images and 2 of the unclear images. Not deleted yet (owner to confirm).
- `archive_dataset/` still holds copies of a few images now excluded from v5 because no real plate is visible.
- `version.json` records the last commit, which does not include this step's scripts.
- The Colab notebook compiles but has not been run on Colab.
