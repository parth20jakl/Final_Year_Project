# Phase 0 - Foundation (2026-10-05 and 2026-10-14, Local)

| # | Step (from workflow doc) | Status | What was done |
|---|---|---|---|
| 1 | Repo layout, `.gitignore`, move archives | partly | Created `configs/ colab/ training/ export/ tests/ android/`. `.gitignore` already excludes `dataset/ runs/ weights/ archive (n)/ .env`. Archive folders were **not moved** into `dataset/raw/`: `ingest.py` and the existing record paths refer to `archive (n)/...`; moving them would break 10k+ record paths. Deferred, documented here. |
| 2 | git safe.directory, first commit | see end of file | |
| 3 | Docs + `configs/project.yaml` | done | `configs/project.yaml`, `docs/compatibility_matrix.md`, `docs/project_workflow.md`, `docs/dataset.md`, `docs/licensing.md` updated. Separate architecture/android/benchmark docs are covered by sections of `project_workflow.md`. |
| 4 | Environment decisions | partly | Measured hardware recorded (RTX 2050 4 GB, 8 GB RAM, torch CPU-only, driver 528.20). **Not done (needs user):** CUDA torch wheel choice, Android Studio/SDK install, phone model. `ultralytics` is not installed locally. |
| 5 | Colab notebook skeleton | done | `colab/train_colab_skeleton.ipynb`, `colab/requirements-colab.txt` (Drive mount, GPU check, git clone, dataset unzip, env.json, resume snippet). Not executed (needs Colab + repo URL). |
| 6 | Compatibility matrix | done (draft) | `docs/compatibility_matrix.md`; **user review gate before full training still applies**. Layer indices/availability marked "verify". |

## Commands
```
mkdir configs colab training export tests android
# files written with the editor tools; no code executed
```

## Update 2026-10-14
Step 6 gate closed: the user approved `docs/compatibility_matrix.md` unchanged; matrix updated with approval note and local layer findings (yolo11n Detect = layer 23 fed by [16,19,22]).
