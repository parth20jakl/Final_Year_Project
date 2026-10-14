# Phase 1, Step 5a - Export v2, QC, and two defects found (2026-10-14, Local)

## Steps followed
1. `python scripts/dataset/export_yolo.py --split v2 --include-auto --tag v2` -> `dataset/processed/yolo_v2` (train 13,272 / val 281 / test 281, content hash 5c26a8e71e9d7112).
2. `python scripts/dataset/qc.py --root dataset/processed/yolo_v2` (slow: all-pairs dHash). It found **problems**, unlike v1:
   - 4 cross-split near-duplicate pairs: 3 Roboflow train images vs manual val/test images (leakage).
   - 3 box errors (`out_of_range` x2, `box_outside_image` x1).
3. Diagnosis
   - Leakage: step 3d compared dHash of the *original* images (Hamming <= 4); QC hashes the *re-encoded, resized export*, so borderline pairs slipped through.
   - Box errors: my step-1 recovery restored images from the export, which was downscaled to max side 1280, but kept the records' original-resolution width/height/boxes. The v2 export divided those boxes by the smaller size -> wrong labels. Checked all 32 recovered images: 6 distinct images affected (a4g_676505a5f6, a4g_d46236afac, a4g_b9629de595, a4g_f6c363565e, a4g_d53584d353, a2_06c808f309). **This was a defect introduced by my own recovery script (step 1), not by the source data.**
4. Fix: `scripts/dataset/fix_v2_issues.py`
   - rescale the records and recognition bboxes of recovered images to the on-disk size (7 record rows, 6 images), flagged `extra.rescaled_to_export_size`;
   - exclude Roboflow images within Hamming <= 8 of any val/test image: 6 images marked `excluded` in `split_v2.json`.
   - Backups: `*.bak_pre_fixv2`; log `dataset/reports/fix_v2_issues_log.json`.
5. Regenerated `yolo_v2` from scratch and re-ran QC (see next record for the result).

## Lessons
- Compare near-duplicates with the same representation QC uses, with a margin.
- Anything repointed to a resized copy must be rescaled at the same time.
- Earlier v1 export was unaffected: it was produced from the original images.
