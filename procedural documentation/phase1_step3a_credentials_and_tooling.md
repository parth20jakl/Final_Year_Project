# Phase 1, Step 3a - Credentials and download tooling (2026-10-05, Local)

## Goal
Prepare to acquire external datasets (Step 3) without exposing keys.

## Steps followed
1. User created a Kaggle token (saved as `C:\Users\ACER\.kaggle\kaggle.json`) and a Roboflow API key (user env var `ROBOFLOW_API_KEY`). Keys were never pasted into chat or printed.
2. Detected presence only (booleans) via PowerShell `[Environment]::GetEnvironmentVariable(...)` and `Test-Path`. Free disk on C: 67 GB.
3. With user approval: `pip install kaggle roboflow` -> kaggle 2.2.4, roboflow 1.6.1.
4. Side effects checked: install pulled numpy 2.3.5 and opencv-python-headless 5.0.0.93; `pip check` reports no broken requirements; `verify_ingest.py` still runs with the same result.
5. Authentication tests (no data downloaded): Kaggle `KaggleApi().authenticate()` + a 20-result dataset search -> OK; Roboflow `Roboflow(api_key).workspace()` -> OK.

## Findings
- Both credentials work.
- `ultralytics` is NOT installed in this Python (earlier skill notes said 8.4.150 on the previous machine). Needed from Phase 2 for local smoke tests; install when that phase starts. Colab will install its own.
- numpy/opencv versions changed by the install; re-check if later tools misbehave.

## Next
Licence check (metadata only) of candidate datasets, then downloads, one source at a time.
