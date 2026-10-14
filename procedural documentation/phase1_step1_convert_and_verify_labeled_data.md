# Phase 1, Step 1 - Convert existing labeled data to unified YOLO + recognition annotations (2026-10-05, Local)

## Goal
Confirm that existing VOC XML / YOLO labeled data is converted into one unified format (records JSONL -> YOLO txt, plus separate recognition annotations with group ids), and that the conversion is internally consistent.

## Decision
The conversion had already been done by `scripts/dataset/ingest.py` (outputs present, `docs/dataset.md`). With user approval I **did not rebuild** (rebuilding would overwrite and the source zips are no longer on disk). I audited the existing output instead.

## Inputs
- `dataset/processed/records_labeled.jsonl` (10,722), `records_unlabeled.jsonl` (1,481), `dataset/annotations/recognition_manual.jsonl` (1,692), `dataset/reports/ingest_log.json`.

## Steps followed
1. Read `ingest.py` header, `ingest_log.json`, line counts and sample rows (`wc -l`, `head`).
2. Wrote `scripts/dataset/verify_ingest.py`. Checks: duplicate ids, image file exists, group id present, labeled record has >= 1 box, every box valid (`box_ok`), labeled `label_source == manual`, unlabeled has no boxes, every recognition row links to a labeled record with a matching bbox.
3. Ran `python scripts/dataset/verify_ingest.py` -> `dataset/reports/verify_ingest.json`.
4. Investigated the one failing check (missing images): compared with and without the Windows long-path prefix, searched the folders, looked for the source zips, and checked whether the exported dataset still holds those images. Saved the ids to `dataset/reports/missing_image_ids.json`.

## Results
| Check | Result |
|---|---|
| Labeled / unlabeled / recognition rows | 10,722 / 1,481 / 1,692 |
| Domain | indian 1,899, external 8,823 |
| Sources (labeled) | keremberke 8,823; archive4 video 654, OLX 600, google 438; archive3 frames 160; datacluster 47 |
| Distinct groups | 9,874 |
| Recognition rows flagged `text_suspect` | 68 |
| Duplicate ids, missing group, bad boxes, orphan recognition rows, bbox mismatches | **0** |
| **Image file missing on disk** | **55** (29 labeled `archive4_google_images`, 26 `archive2_unlabeled`) |

## Findings / problems
- 55 originals are absent from `archive (4)/google_images` and `archive (2)`, with and without the long-path prefix. The source zips (`archive (n).zip`) are also gone, so they cannot be re-extracted. Likely cause: Windows long-filename extraction failures; only 12 files were recovered earlier.
- The images are not lost for training: the earlier export `dataset/processed/yolo_final/` contains copies (64 matching files, i.e. images and labels). 29 recognition rows belong to the missing labeled images.
- Not changed yet. Options: (a) leave records and rely on the exported copies, (b) drop the 55 records from the JSONL and recognition files, (c) recover originals from `yolo_final` into `dataset/raw/`.

## Outputs
- New: `scripts/dataset/verify_ingest.py`, `dataset/reports/verify_ingest.json`, `dataset/reports/missing_image_ids.json`.
- No existing data modified.

## Reproduce
`python scripts/dataset/verify_ingest.py` from the repo root (exit code 1 while any issue exists).

## Follow-up fix (user chose "Recover from yolo_final")
1. Wrote `scripts/dataset/recover_missing_from_export.py`: for each id in `missing_image_ids.json`, copy `dataset/processed/yolo_final/images/<split>/<id>.jpg` to `dataset/raw/recovered_from_export/<id>.jpg`, repoint `path` in `records_labeled/unlabeled/auto.jsonl`, add `extra.recovered_from_export = true`. Backups: `*.jsonl.bak_pre_recover`. Log: `dataset/reports/recover_missing_log.json`.
2. Ran it: **32 restored** (29 labeled Indian + 3 auto-labeled archive2 images), **23 unrecoverable** (archive2 unlabeled images that were never auto-labeled/exported, so never used in training data).
3. Re-ran `verify_ingest.py`: only the 23 unused unlabeled originals still missing; all other checks 0 issues.

Caveats: recovered files are the exported JPEGs (re-encoded, max side 1280), not the pristine originals. The 29 labeled ones belong to the test split of `yolo_final`, so test content is unchanged. The 23 missing unlabeled images are left in `records_unlabeled.jsonl`; they do not affect training or evaluation.
