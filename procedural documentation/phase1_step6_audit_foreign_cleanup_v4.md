# Phase 1, Step 6 - Re-audit, foreign-data cleanup, dataset_v4, plate-decoding spec (2026-11-27, Local)

## Owner instructions
1. Study the project (skill, documents, procedural records, UI samples, scripts).
2. Delete previously uploaded data that has non-Indian number plates; the dataset must contain Indian plates only.
3. Add plate decoding (state / RTO / series / number) to the skill, documents and workflow.
4. List what will not be needed (owner deletes after review) and what is pending to reach about 80% in 3-4 days.
5. A new dataset will be uploaded later and annotated with a "world model" (not part of this step).

## Steps followed
1. Inventory of folders and records.
2. Viewed every v3 image not covered by typed plate text as plate-crop contact sheets (3,190 images, 34 sheets), plus the archive4 google images (438).
3. Viewed the 702 mixed-country images not used by v3 (archive2 and IVDB `cars_*`) as full-image sheets, zooming on unclear ones.
4. Found 345 foreign images (below) and wrote `dataset/annotations/foreign_ids.json`.
5. Wrote `scripts/dataset/purge_foreign.py` and ran the dry run.
6. Ran `purge_foreign.py --apply` -> **refused by the assistant's auto-mode permission check** (destructive action). Not retried. **No file was deleted.**
7. Added `--split-only` and `foreign_review_sheet.py`; ran:
```
python scripts/dataset/foreign_review_sheet.py
python scripts/dataset/purge_foreign.py --split-only
python scripts/dataset/export_yolo.py --split v4 --include-auto --tag v4
python scripts/dataset/qc.py --root dataset/processed/yolo_v4
python scripts/dataset/freeze.py --tag v4 --name dataset_v4
```
8. Saved label defects to `dataset/annotations/label_defects.json`.
9. Wrote `docs/plate_decoding.md` and `configs/plate_codes.json`; updated skill, workflow, dataset docs, licensing note, `configs/project.yaml`.

## Results
| Foreign group | Images |
|---|---|
| US street scenes | 297 |
| UK | 18 |
| Russian | 12 |
| German | 7 |
| Korean | 4 |
| Other (Norway, Cyprus-style, South Africa, Pakistan, unknown) | 5 |
| Mock-up, not a real plate | 2 |
| **Total** (39 archive2, 300 IVDB, 3 archive4, 3 rf_nivu) | **345** |

dataset_v4: train 4,314 (4,599 plates) / val 281 (315) / test 281 (306). QC: no errors, 0 cross-split near-duplicates. sha256 `82b2b91a94898ff4829c7fc83078cf8e2f64a6be72626e3f9e7af40b9c092c8e`, content hash `4ac13df2d4f3e258`.

## Pending: deletion (owner)
```
.venv-train\Scripts\python.exe scripts\dataset\purge_foreign.py           # dry run
.venv-train\Scripts\python.exe scripts\dataset\purge_foreign.py --apply   # permanent
```
Deletes 350 individual files (images and their annotation files), `raw/external/keremberke` (8,831 files, 469.5 MB), `processed/yolo_manual` (520.7 MB), `yolo_final` (552.5 MB), `yolo_v2` (734.4 MB) and `frozen/dataset_v2.zip` (738.8 MB), and removes the matching records. `dataset_v3.zip` and `yolo_v3` are not touched by the script and still contain the 6 foreign images. Archive images have no other local copy (the archive zips are gone).

## Problems found (not fixed)
- Vehicle-sized boxes labelled as plates: 93 boxes (92 images) that also have a plate box, plus 17 images with only the big box. All `rf_ilpd_khhkb`, train. Found by geometry, spot-checked.
- At least 13 boxes on non-plates (model badges, logos, signboards, watermark, wheel); `a4g_ccfaaca369` (CRETA badge) is in **test**.
- The 2026-10-14 records state Indian-only and a clean QC; QC checks format and leakage, not whether a box is really a plate.
- Exit criterion of 6-10k independent images still not met; many images repeat the same vehicles.

## Caveats
- One reviewer, small thumbnails. Foreign plates that could not be recognised may remain. Two unclear images were kept.
- v4 was frozen with uncommitted script changes, so the commit hash in `version.json` does not contain `purge_foreign.py`.
- `colab/train_colab_skeleton.ipynb` still points to dataset_v3 (v4 not uploaded; update it for v5).
