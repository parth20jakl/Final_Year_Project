# Local training environment + first CPU smoke test (2026-10-14, Local)

User decision: install ultralytics locally, CPU torch only, in a virtual environment.

## Steps followed
1. `python -m venv .venv-train` (system Python 3.14.6); upgraded pip.
2. `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` -> torch 2.14.1+cpu, torchvision 0.29.1+cpu.
3. `pip install ultralytics onnx onnxruntime pytest pyyaml` -> ultralytics 8.4.177, onnx 1.23.2, onnxruntime 1.31.0, numpy 2.5.2, opencv-python 5.0.0.93. `pip check`: no broken requirements. `torch.cuda.is_available()` = False (expected).
4. `pip freeze` -> `requirements-local-train.txt` (50 lines). `.venv-train/` added to `.gitignore`.
5. Model loading: `yolo11n.pt`, `yolo26n.pt` (auto-downloaded, moved to `weights/`; `yolo11s.pt` was already there). Both load; yolo11n 2.59M params, yolo26n 2.57M params, `DetectionModel`, layers listed via `model.model.model` (Detect is layer 23 in both, neck feeders to be mapped in Phase 3).
6. Smoke test: copied a random subset of `dataset/processed/yolo_v3` (48 train + 12 val images, seed 0) to `dataset/processed/smoke_v3`, then `YOLO('weights/yolo11n.pt').train(data=smoke.yaml, imgsz=320, epochs=1, batch=4, workers=0, device='cpu', seed=42, amp=False)`.

## Results
- Pipeline OK: labels/yaml parse, cache created, one epoch trained and validated, last/best.pt written to `runs/detect/runs/smoke/yolo11n_cpu_smoke/`.
- Time: 24 s for 1 epoch on 48 images at 320 px (CPU, Intel i7-1355U). Inference 39 ms/img at 320 px on CPU.
- Metrics (mAP50 0.0007, P 0.002, R 0.31) are **meaningless** (1 epoch, 48 images, pretrained COCO weights, loss still high). The test only proves the pipeline works; it is not a baseline.

## Notes
- Ultralytics prints a "slow image access" warning for this path; harmless.
- Ultralytics wrote its settings to `%APPDATA%\Ultralytics\settings.json`.
- The run folder ended up in a nested `runs/detect/runs/smoke/...` path because `project=` is relative to ultralytics' runs_dir; set `project` absolute or change `runs_dir` for later runs.
- AGPL-3.0 applies to ultralytics (academic use, noted in docs/licensing.md).

## Reproduce
`.venv-train\Scripts\python.exe` + the commands above; smoke subset script not kept in repo (one-off).

## Addendum 2026-10-14: dataset hand-off to Colab
- User uploaded `dataset_v3.zip` to a Drive folder (ID 1CmwJB6IxwyJi0SQSC6JXJp4KiEar0Dgj) in an account that is not the one connected to this session (folder lookup: "not found"), so presence/size could not be verified from here.
- `colab/train_colab_skeleton.ipynb` dataset cell now authenticates in Colab, finds `dataset_v3.zip` in that folder via the Drive API, downloads it, **verifies sha256 (f83368585d8e...)**, unzips to /content/data. Requirement: the Colab account must own or have Viewer access to the folder. Not executed yet.
