# Phase 1, Step 7 - Deletion of foreign and unused files; Indian-only archive dataset (2026-11-28, Local)

## Owner instructions
1. Delete the foreign-plate data (345 images and the old mixed-country data).
2. Delete the unused files listed on 2026-11-27.
3. Copy the Indian-plate images from `archive (2)` to `archive (6)` into one folder under `dataset/`; delete foreign-plate images found there.
4. List files that will not be needed (list only, no deletion).

## Steps followed
1. Verified the `dataset_v4.zip` checksum, ran the purge dry run, then:
```
python scripts/dataset/purge_foreign.py --apply
```
2. Deleted: `frozen/dataset_v3.zip`, `processed/yolo_v3`, `processed/smoke_v3`, `runs/detect`, `runs/annotator/weights/last.pt`, `requirements.txt`, `reports/review_queue.html`, `reports/review_sheets/`, `reports/nat_sheets/`, and the older `*.bak_*` files under `dataset/`.
3. Built contact sheets of all images in archives 2, 5 and 6 and reviewed them; checked unusual archive 4 plate texts.
4. Found 5 more foreign images with records (South African, Vietnamese, two Singapore, one US-style) and 1 GIF without a record (Italian-style). Added `--ids` to `purge_foreign.py` and ran it with `foreign_ids_round2.json` (4) and `foreign_ids_round3.json` (1); removed the GIF with `rm`.
5. Wrote per-image status to `dataset/annotations/archive_review.json`, then:
```
python scripts/dataset/extract_archive_dataset.py
pytest tests
```

## Results
| Source | Copied (Indian plate visible) | Unclear | No plate (not copied) |
|---|---|---|---|
| archive 2 | 294 | 0 | 9 |
| archive 3 | 160 | 0 | 0 |
| archive 4 | 1,659 | 0 | 3 |
| archive 5 | 35 | 65 | 0 |
| archive 6 | 401 | 263 | 42 |
| **Total** | **2,549** | **328** | **54** |

- `dataset/archive_dataset/` (about 908 MB, with `manifest.csv`); annotations copied for archive 3 (YOLO .txt) and archive 4 (VOC .xml).
- `dataset/archive_dataset_unclear/` (about 282 MB): Indian road scenes where a plate is too small or doubtful to confirm at review size.
- Originals stay in the archive folders: dataset records point to them.
- Foreign images deleted in total: 351.
- Tests: 16 passed.

## Problems and deviations
- `dataset_v4.zip` and `processed/yolo_v4` still contain one foreign image, `a6_d3b729c19b` (Singapore bus, train split), missed on 2026-11-27. Its record and source file are now deleted, so a new export will not include it. v4 was not rebuilt.
- 23 records in `records_unlabeled.jsonl` point to missing files; all were already listed in `reports/missing_image_ids.json` before this step.
- Archive 4 video and OLX images (1,254) were accepted on their typed Indian plate text and were not viewed one by one.
- Images already carrying a dataset v4 plate box were counted as "plate" without a second per-box check.
- One reviewer, thumbnails.
- `colab/train_colab_skeleton.ipynb` still asks for `dataset_v3`, whose local copy is now deleted.
- `make_split_v3_indian_only.py` can no longer run (`nat_sheets/` deleted); `split_v3.json` is unchanged.
- Backups from the three purge rounds (`*.bak_pre_purge*`) are kept until v5.
