# Phase 1, Step 4 (human review) + Indian-only dataset v3 (2026-10-14, Local)

## User instructions
1. Keep only review-queue images that have a **single bounding box around an Indian number plate**; reject the rest (not a plate / not Indian).
2. Keep only Indian number plates in the dataset; remove all non-Indian plates.

## Steps followed
1. **Review queue (407 images).** `records_auto.jsonl` rows with `label_source=review_pending`. 175 had 2-6 boxes -> rejected by the single-box rule. For the 232 single-box images I built contact sheets (crop = 3x the box, red box drawn; `dataset/reports/review_sheets/sheet_00..09.jpg`, index->id in `order.json`) and judged each by eye: keep only if the box covers (essentially) the whole plate and the plate looks Indian. Rejected: taillights/text/logos/tyres, partial or one-line-of-two boxes, UK/US/EU-format plates, unreadable specks. Result: **116 accepted / 291 rejected**, stored in `dataset/annotations/review_decisions.json`; applied to `records_auto.jsonl` (`auto_reviewed` / `rejected`; backup `.bak_pre_review`).
2. **Nationality problem found.** Several accepted images were clearly California plates and came from `archive6_IVDB/cars_*` (a car dataset with US cars). So the source folder is not a reliable "Indian" marker. I then checked, by sheet (`dataset/reports/nat_sheets/sheet_00..08.jpg`, 347 images), every auto-labelled image from `IVDB/cars_*`, `archive2` and the 3 recovered ones (both previously auto-accepted and review-accepted). Only 110 were judged Indian with a proper single box -> `dataset/annotations/nationality_keep.json`. Many were Californian (27FX374, 4MCP021 repeated ...), UK/EU, Russian-format, or unreadable.
3. **Split v3** with `scripts/dataset/make_split_v3_indian_only.py`: keremberke (8,823 mixed-country images) excluded; Roboflow Indian + manual Indian records unchanged; auto pool kept only if single box, accepted/reviewed, and (for IVDB cars / archive2) in `nationality_keep.json`. `split_v2.json` and `dataset_v2.zip` are left untouched as history.
4. `export_yolo.py --split v3 --include-auto --tag v3` -> `dataset/processed/yolo_v3`; `qc.py` -> clean; `freeze.py --tag v3 --name dataset_v3`.
5. Updated `configs/project.yaml` and the Colab skeleton to v3.

## Results
| Split | Images | Plates | Provenance |
|---|---|---|---|
| train | 4,320 | 4,605 | manual 4,035 (archive Indian + Roboflow Indian), auto_accepted 201, auto_reviewed 84 |
| val | 281 | 315 | manual Indian |
| test | 281 | 306 | manual Indian |
QC: no errors, 0 cross-split near-duplicates, 2,254 within-split near-duplicate pairs.
Frozen: `dataset/frozen/dataset_v3.zip` (403 MB), sha256 f83368585d8e0449a7093ceee0acd61cfc5b1e4a6090e5a769b4d53d77d9533a, content hash e426f55d3fc447b4.
Excluded counts: keremberke 8,823; auto rejected in review 291; auto not-Indian/unverified 227; auto multi-box 12.

## Caveats (must go in the report)
- Nationality and box quality were judged by one reviewer (me) from small crops; no second reviewer. Blurry white-plate images were kept only when the car/region looked Indian; this is a judgement, not ground truth. The 4,035 "manual" images were not re-checked for nationality (archive 4 was filtered by Indian plate-text pattern; Roboflow sets are titled Indian).
- IVDB auto/bus/lorry and archive5 auto-accepted images (detector conf >= 0.7, single box) were NOT visually verified.
- Train is now 4.3k images with 2.2k near-duplicate pairs: independent Indian images are fewer than that. The earlier ">= 6-10k" exit criterion is NOT met; val/test (281 each) are manual and leak-free.
- The v3 train set is much smaller than v2 (13.3k); the removed keremberke data may be useful for pre-training; if wanted it can be used as a clearly labelled non-Indian pretraining set, not in this dataset.
