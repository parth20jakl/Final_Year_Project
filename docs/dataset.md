# Dataset plan and build record

Everything here is reproducible with the scripts in `scripts/dataset/` (run from the repo root, in this order).

| Step | Command | Output |
|---|---|---|
| 1 ingest | `python scripts/dataset/ingest.py` | `dataset/processed/records_{labeled,unlabeled}.jsonl`, `dataset/annotations/recognition_manual.jsonl`, `dataset/reports/ingest_log.json` |
| 2 split | `python scripts/dataset/split.py` | `dataset/splits/split_v1.json` |
| 3 export (manual) | `python scripts/dataset/export_yolo.py --tag manual` | `dataset/processed/yolo_manual/` |
| 4 train annotator | `python scripts/dataset/train_annotator.py` | `runs/annotator/weights/best.pt` |
| 5 auto-annotate | `python scripts/dataset/auto_annotate.py` | `records_auto.jsonl`, `reports/auto_annotation_report.json`, `reports/review_queue.html` |
| 6 (human) review | write `dataset/annotations/review_decisions.json`, then `auto_annotate.py --apply-review` | reviewed labels |
| 7 export (final) | `python scripts/dataset/export_yolo.py --include-auto --tag final` | `dataset/processed/yolo_final/` |
| 8 QC | `python scripts/dataset/qc.py --root dataset/processed/yolo_final` | `dataset/reports/yolo_final/dataset_{statistics.json,report.html}` |

## Sources
See `docs/licensing.md`. Domain tags: `indian` (archives 2-6, Datacluster sample) and `external` (keremberke, mixed countries).

## Split policy (leakage-safe)
- Images are connected if they share a group (plate text / video sequence / Roboflow source stem) or are near-duplicates (64-bit dHash, Hamming <= 4), including across sources. Each connected component lives in exactly one split. `split.py` asserts this; `qc.py` re-verifies on the exported files.
- Indian manual data: 70/15/15 train/val/test. External data: train only. Auto-labelled pool: train only. **Val and test are 100% human-labelled Indian images.**
- Seed 42, version `v1` (`dataset/splits/split_v1.json`).

## Labels
- Detection: one class `license_plate` (id 0), YOLO txt `0 xc yc w h` normalised. Images exported with max side 1280 (boxes unaffected).
- Recognition (separate file): `image_id, bbox, plate_text, label_source, text_suspect`. Only archive 4 has plate text (1,692 rows). Rows where the text does not look like an Indian plate are flagged `text_suspect` (grouped by file, not by text) and should be corrected before OCR training/evaluation.
- Provenance per image: `label_source` = `manual` | `auto_accepted` | `auto_reviewed`.

## Preparing for knowledge distillation (FGD)
- Teacher and student train on the **same** YOLO dataset and the same augmentation pipeline; no separate KD data is needed.
- FGD's focal term needs ground-truth boxes to build foreground/background masks, so every KD training image must have >= 1 box: the exported train split contains only images with plates (auto-labelled images are included only when accepted/reviewed). Images with no detected plate are deliberately left out rather than used as unverified negatives.
- Teachers should be trained on this dataset first (same split) so their features are plate-aware; evaluate teacher and student on the same val/test.

## Known limitations (do not hide in the paper)
- Independent Indian images are few (~1.9k manual); the majority of train images are external (non-Indian) data. Report results on the Indian-only test set and ablate with/without external data.
- Archive 4 images are web photos / low resolution; archive 3 has only 3 video sequences.
- No night / heavy-motion / gate-camera coverage yet: collect the original permitted gate set and use it as the final test set.
- Auto labels carry estimated error (see `auto_annotation_report.json`); they never touch val/test.

## Update 2026-10-14: split v2
- `split_v2.json` = v1 assignments unchanged + 2,704 Roboflow Indian images (domain `indian_external`) in **train only**. 552 Roboflow images that were near-duplicates (dHash <= 4) of val/test images were dropped. Val/test remain 281/281, 100% manual.
- Built with `scripts/dataset/ingest_roboflow.py` (incremental; do not re-run `ingest.py`, the source archives are no longer on disk - see `procedural documentation/`).
- Export: `python scripts/dataset/export_yolo.py --split v2 --include-auto --tag v2` -> `dataset/processed/yolo_v2`.
- Pending human work: 407 images in `dataset/reports/review_queue.html` still need accept/reject decisions; ~300-500 own-gate test images still to be collected.

## Update 2026-10-14 (later): split v3 - Indian plates only (CURRENT)
- User decision: only Indian number plates. `split_v3.json` excludes keremberke (8,823 mixed-country images) and every auto-labelled image that is multi-box, human-rejected, or not verified Indian (IVDB `cars_*` contains US plates). Details: `procedural documentation/phase1_step4_human_review_and_indian_only_v3.md`.
- Current dataset: `dataset/frozen/dataset_v3.zip` - train 4,320 / val 281 / test 281 images; QC clean, 0 leakage. v2 is superseded (kept as history).
- Caveat: nationality/box checks are single-reviewer visual judgements; independent Indian images are fewer than 4.3k (2,254 within-train near-duplicate pairs).
