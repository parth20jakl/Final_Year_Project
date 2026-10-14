# Phase 1, Step 5b - QC result, freeze dataset_v2, close-out (2026-10-14, Local)

## QC of regenerated yolo_v2 (after fixes)
`errors: {}`, cross-split near-duplicates **0**, within-split near-duplicate pairs 6,101 (v1: 3,921).
| Split | Images | Plates | Provenance |
|---|---|---|---|
| train | 13,266 | 13,893 | manual 12,858 (incl. 2,698 Roboflow Indian + 8,823 keremberke), auto_accepted 408 |
| val | 281 | 315 | 100% manual Indian |
| test | 281 | 306 | 100% manual Indian |

## Freeze
`python scripts/dataset/freeze.py --tag v2 --name dataset_v2` (refuses when QC is not clean) ->
- `dataset/frozen/dataset_v2.zip` (739 MB), `dataset/frozen/dataset_v2.sha256` = c91f843cffe7266ba21d86349399e3f0c1122b231547fda29442e5f3369bcb0d
- `dataset/processed/yolo_v2/version.json`: content_hash a762cc32dd46f513, split_v2 sha256, counts, QC summary.
- Note: `git_commit` is "unknown" in version.json because git's safe.directory was not yet set when freeze ran; the data are unchanged by that. Commit eaaaeac holds the code that produced them.

## Git
- `git config --global --add safe.directory <repo>` (Phase 0 step 2).
- Found `.gitignore` pattern `dataset/` also ignored `scripts/dataset/`: all dataset scripts were untracked. Changed to `/dataset/`.
- Commit eaaaeac: docs, configs, colab, scripts, procedural documentation.

## Phase 1 status vs workflow exit criteria
| Step | State |
|---|---|
| 1 convert labeled data | done + verified |
| 2 QC | done, repeated on v2 (clean after fixes) |
| 3 external data | Roboflow Indian x4 done (2,698 net images). Kaggle small CC0/Apache sets and Open Images V7 NOT downloaded (not selected); big Kaggle set rejected (licence unverified, augmented copies). |
| 4 auto-annotate | pool labelled earlier (408 accepted). **407 review-queue images await human accept/reject**; no new auto-annotation needed for Roboflow data. |
| 5 group split + freeze | done: split v2, dataset_v2 frozen |
| 6 own gate test set | **NOT done - needs the user** (300-500 permitted gate images, manually labelled) |
| 7 upload to Drive | **NOT done - needs the user** (`dataset/frozen/dataset_v2.zip` -> `/MyDrive/anpr/datasets/`) |

Exit criterion check: "independent images >= ~6-10k": total labeled train images 13,266 but 6,101 within-split near-duplicate pairs and non-Indian keremberke (8,823) mean the *independent Indian* count is far lower (manual Indian ~1.9k + ~2.7k Roboflow). Report this honestly and ablate with/without external data. Val/test manual-verified and leak-free: met.
