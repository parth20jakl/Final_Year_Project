# Adaptive KD-YOLO ANPR on Android - Project Workflow and Technical Document

Last updated: 2026-11-27 (plate decoding and entry log added; Indian-only dataset v4). Companion files: `.claude/skills/anpr-fgd-android/references/*` (operating rules for the AI assistant), `docs/dataset.md`, `docs/licensing.md`.

---

## 1. Project summary

A real-time **Automatic Number Plate Recognition (ANPR)** system for **institutional gates** (**Indian plates only**) that runs **fully on an Android phone**. It reads each plate, explains it (for `MH12CP5156`: Maharashtra, RTO MH12 Pune, series CP, number 5156) and logs when and where the vehicle was seen, for export to Excel. It compares three YOLO families - **YOLOv6n, YOLO11n, YOLO26n** - each as a plain baseline and as a student distilled with **Focal and Global Knowledge Distillation (FGD)**. A configurable **adaptive frame-filtering** stage (time, region, area) cuts unnecessary inference. Everything is evaluated in a controlled benchmark.

**Research questions**
1. Does FGD improve a nano detector's accuracy at no extra inference cost?
2. Which family gives the best accuracy / latency / size trade-off on a real phone?
3. How much compute can time / region / area filtering save without losing plates?

**Deliverables:** frozen dataset, 6 trained models (3 baseline + 3 FGD), ONNX exports with parity proof, Android app (with plate decoding and entry log export), benchmark results and report.

**Hard rules (short):** FGD only (no logit KD), teacher exists at training time only, detection and OCR are separate modules, filters always emit a reason, data split by vehicle/plate/sequence, no fabricated results, licences recorded, configs in YAML, no cloud inference. Full list: `constraints.md` in the skill references.

---

## 2. Compute strategy: Local PC vs Google Colab A100

| | **Local PC** | **Google Colab** |
|---|---|---|
| GPU | NVIDIA RTX 2050 Laptop, 4 GB VRAM (driver 528.20) | A100 (typically 40 GB) |
| RAM | 8 GB (~7.7 GB usable) | 12-80 GB depending on plan |
| OS | Windows 11 | Linux, ephemeral VM |
| Persistence | Permanent disk | Lost on disconnect - use Google Drive |

### 2.1 Local PC (RTX 2050 / 8 GB RAM) - responsibilities
- Coding and debugging (training tools, FGD module, scripts, Kotlin app)
- Dataset organisation and validation (conversion, QC, leakage checks, freezing)
- Android Studio development
- Android application testing (emulator for logic, physical phone for performance)
- Small smoke tests (1-2 epochs, subset, imgsz 320-416, batch 2-4, AMP)
- Small baseline experiments (nano models, subsets, pipeline sanity)
- Export / model-conversion testing (.pt -> ONNX -> ONNX Runtime parity)

**Local limits:** nano models only; `workers` 0-2; `cache` off; no teacher+student at 640; do not run the Android emulator and training simultaneously (RAM). Installed PyTorch is currently CPU-only (2.14.0+cpu); the driver (528.20, CUDA <= 12.0) needs a cu118/cu121 wheel (or a driver update) before local GPU use.

### 2.2 Google Colab A100 - responsibilities
- Full baseline training (3 families, 640 px)
- Teacher training (s / m)
- FGD distillation runs, lambda sweeps, final students, repeated seeds
- Large auto-annotation jobs, OCR model training if a custom OCR is chosen

### 2.3 Hand-off between tiers

```
 LOCAL                                   GOOGLE DRIVE                          COLAB A100
 -----                                   ------------                          ----------
 git push code + configs  ------------------------------------------------->  git clone / pull
 freeze dataset_v1 (zip + hash) -------> /MyDrive/anpr/datasets/dataset_v1.zip --> unzip to /content
                                         /MyDrive/anpr/runs/<run_id>/  <-------  checkpoints every epoch,
 pull best.pt, results.csv, env.json <--                                         results.csv, config, env.json
 evaluate, export ONNX, parity, Android
```

**Run record (mandatory per Colab run):** git commit hash, dataset version hash, config YAML, seed, `pip freeze`, GPU name, CUDA/PyTorch/Ultralytics versions, start/end time. A checkpoint without these is an incomplete experiment.

**Colab rules:** mount Drive; train from `/content` (local SSD), never directly from Drive; save every epoch and support resume after disconnects; pin versions in `requirements-colab.txt`.

---

## 3. System architecture

### 3.1 Two-plane view

```
TRAINING PLANE (offline, Colab A100 + local checks)

 Raw data --> Convert/QC --> Group split --> dataset_v1 (frozen, hashed)
                                                  |
        +-----------------------------------------+------------------------------+
        v                                                                        v
  Baseline training (n)                                              Teacher training (s/m)
        |                                                                        |
        |                                  +-------------------------------------+
        |                                  v
        |                   FGD distillation: student(n) learns from frozen teacher
        |                   total = detection loss + lambda * FGD(focal + global)
        v                                  v
   3 baselines                        3 FGD students
        +----------------+-----------------+
                         v
        Export: .pt -> ONNX -> parity check -> model_metadata.json   (LOCAL)

DEPLOYMENT PLANE (Android phone, fully offline)

 Camera/Image -> [Time filter] -> [Region filter] -> [Area filter] -> Preprocess
              -> Detector (ONNX Runtime) -> NMS -> Crop -> (enhance?) -> OCR
              -> PlateValidator -> PlateDecoder -> UI -> local entry log (CSV for Excel)
              -> Benchmark logger
```

The teacher never reaches the phone. Only the student ONNX does.

### 3.2 Training-plane components

| Component | Purpose |
|---|---|
| Dataset tooling (`scripts/dataset/`) | Convert VOC/YOLO sources to one YOLO format, keep `recognition_annotations/` (plate text), QC, perceptual-hash near-duplicate detection, group-level split, freeze + hash |
| Baseline trainers | Ultralytics for YOLO11n / YOLO26n; official YOLOv6 repo for YOLOv6n |
| Teachers | Same-family larger model (s -> n initially; m allowed for YOLO11), size chosen empirically |
| FGD module (`training/fgd/`) | Implemented once: focal masks, spatial/channel attention, global relation (GcBlock), 1x1 projector |
| FGD adapters | `YOLOv6FGDAdapter`, `YOLO11FGDAdapter`, `YOLO26FGDAdapter` - choose P3/P4/P5 neck taps by semantic position, install forward hooks, never reuse a layer index across families |
| Export tools | ONNX export, numeric parity, metadata JSON |
| Experiment tracking | Per-run folder with config + env + metrics; no results without provenance |

### 3.3 Android app components

| Component | Responsibility |
|---|---|
| `CameraSource` (CameraX) | Live frames (ImageAnalysis) and still capture |
| `FramePipeline` | Orchestrates filters -> detector -> OCR; photo mode bypasses the time filter |
| `TimeFilter` | Process at most one frame per interval (50/75/100/150/200 ms sweep) |
| `RegionFilter` | ROI rectangle first, polygon-ready; frames/detections outside ROI skipped |
| `AreaFilter` | Low-res frame-difference activity % vs configurable threshold |
| `FilterDecision` | Enum `PROCESSED / SKIP_TIME / SKIP_AREA / SKIP_REGION` with reason, always emitted |
| `Detector` interface | `YOLOv6Detector`, `YOLO11Detector`, `YOLO26Detector` -> common `DetectionResult(classId, confidence, x1, y1, x2, y2)`; runtime model switch; per-family output parser (YOLO26 is NMS-free) |
| `PlateRecognizer` interface | `recognize(crop) -> PlateTextResult`; implementation chosen by bake-off |
| `PlateValidator` | Configurable Indian plate patterns (not one hard-coded format) |
| `PlateDecoder` | Splits the text into state, RTO code, series, number using `configs/plate_codes.json`; status `VALID / OFFICE_UNKNOWN / CORRECTED / UNRECOGNISED` |
| `EntryLog` | One local row per accepted sighting (date, time, location, plate, decoded fields, confidences, model); CSV export for Excel |
| `BenchmarkLogger` | Per-frame timings, skip counts, RAM; CSV/JSON export |
| UI | Model selector, filter toggles/parameters, photo/live mode, result overlay with decoded plate, entry list and export, stats |

### 3.4 Filter order and semantics
Time -> Region -> Area. Cheapest first. Each skipped frame carries its reason, so benchmark output can report detector FPS, effective system FPS and skip rate **separately**.

### 3.5 Plate decoding and entry log
Full specification: [plate_decoding.md](plate_decoding.md).

| Part of `MH12CP5156` | Meaning |
|---|---|
| `MH` | State: Maharashtra |
| `12` | RTO office: Pune (MH12) |
| `CP` | Series |
| `5156` | Vehicle number |

The detector only finds the plate (one class). Meaning comes from OCR text plus a code table, so no retraining is needed. Delhi, BH-series, temporary and two-line plates have their own handling. Uncertain readings are flagged, never guessed. Each accepted sighting is stored on the phone with date, time and location and exported as CSV, which opens in Excel. Report OCR exact-match and decode accuracy separately from detection mAP.

---

## 4. Technology stack (what and why)

| Layer | Technology | Why / notes |
|---|---|---|
| Detection models | **YOLOv6n, YOLO11n, YOLO26n** | Three recent nano-scale families to compare; single class `license_plate`, 640 px |
| Training frameworks | **Ultralytics** (YOLO11/26), **official YOLOv6 repo** | Reuse proven training loops; Ultralytics is AGPL-3.0 (record in `licensing.md`); YOLOv6 checkpoints may be self-distilled - record provenance |
| Knowledge distillation | **FGD** (Yang et al., CVPR 2022) | Feature-based; focal term separates foreground/background and attends spatially/by channel; global term transfers relations via GcBlock. Cited, never claimed as ours. Adapted from MMDetection style to our PyTorch hooks |
| Deep learning | **PyTorch** (CUDA on Colab) | Training and FGD |
| Mixed precision | **AMP** | Required for VRAM on both tiers |
| Interchange | **ONNX** | Common export for all 6 models |
| On-device runtime | **ONNX Runtime Mobile** (Android) | One backend for fair comparison; INT8/NNAPI deferred |
| App language | **Kotlin**, **CameraX**, Gradle, Android Studio | Standard Android camera pipeline |
| OCR candidates | PaddleOCR, ML Kit, Tesseract, LPRNet-style custom | Selected by measured bake-off on cropped plates |
| Dataset tooling | Python, OpenCV, imagehash/pHash, PyYAML | QC, dedup, conversion |
| Auto-annotation | Teacher/annotator YOLO model + human review queue | Only for unlabeled pools; val/test must be manually verified |
| Tests | pytest (Python), JUnit (Kotlin) | FGD shapes/backward, filters, ROI, parsing, scaling |
| Compute | Local RTX 2050 + **Google Colab A100** | See section 2 |
| Config / repro | YAML in `configs/`, seeds, version logging | Hyper-parameters never in code |
| Source control | git | Code travels to Colab via git; data/weights via Drive |

### 4.1 FGD in detail
- **Loss:** `L_total = L_detection + lambda_FGD * (L_focal + L_global)`. Detection loss is never replaced. Lambda is configurable per family.
- **Focal:** ground-truth boxes build a foreground/background binary mask (scaled to the feature level); teacher feature attention (spatial + channel) rescales importance; student mimics teacher features separately in foreground and background with different weights.
- **Global:** a GcBlock-style context module on student and teacher features; MSE between the relation (context) maps.
- **Projector:** 1x1 conv aligns student channels to teacher channels when they differ.
- **Taps:** neck outputs (P3/P4/P5 or closest equivalent) mapped per family via adapters.
- **Required tests:** shape alignment, student-teacher mapping, focal output, global output, total loss, backward pass.

### 4.2 Dataset design
- One detector class: `license_plate`. YOLO txt `0 xc yc w h` normalised.
- Recognition labels kept separately: `{image_id, bbox, plate_text, group_id}`.
- Split ~70/15/15 by **group** (plate text / vehicle / sequence / source), never by random frame; leakage proven by script.
- QC: missing/orphan files, malformed or zero-area boxes, bad class ids, exact + near duplicates, unreadable images, plate-size distribution -> `dataset_statistics.json`, `dataset_report.html`.
- Frozen as `dataset_v1` with version file and hash. Original gate images only with permission; no PII in filenames; third-party and original data licensed separately.

### 4.3 Export contract
`.pt` -> validate -> ONNX -> compare with PyTorch on fixed inputs (input shape, class count, output shape, box coordinates, confidences within tolerance) -> `model_metadata.json` (family, FGD flag, imgsz, classes, output format, parser type, source commit, dataset hash). A model that cannot export cleanly is documented before any runtime change.

### 4.4 Benchmark metrics
- Detection: P, R, F1, mAP50, mAP50-95.
- Recognition: character accuracy, exact match, CER, OCR confidence.
- Android: FPS mean/median, latency P50/P95, preprocess/inference/postprocess/OCR times, RAM, model size, APK size, CPU/battery/temperature where measurable.
- Filter: captured, processed, skipped, skip %, per-filter skip counts, effective FPS, filter overhead.
- Protocol: same phone, camera, resolution, thresholds, ROI, duration; warm-up; fixed duration; >= 3 repetitions; mean/median/std/P95.
- Final table: `Model | FGD | mAP50 | mAP50-95 | Plate Acc | FPS | P50 | P95 | RAM | Size | Skip%`.
- Ablations: baseline vs FGD; filters (none / time / time+region / time+area+region); model comparison; optional OCR comparison.

---

## 5. Repository layout (target)

```
Project/
  .claude/skills/anpr-fgd-android/   assistant context
  configs/                           project.yaml, train_*.yaml, fgd_*.yaml, filters.yaml
  dataset/ (raw, annotations, processed, splits, reports)    git-ignored, versioned by hash
  docs/                              this file, dataset.md, licensing.md, architecture, decisions...
  scripts/dataset/                   convert, qc, split, freeze
  training/ (fgd/, adapters/, train_*.py)
  export/                            export_onnx.py, parity.py
  colab/                             notebooks + requirements-colab.txt
  android/                           Android Studio project
  runs/, weights/                    git-ignored
  tests/
```

---

## 6. Phase-wise workflow

Each phase lists: **goal -> tier -> steps -> outputs -> exit criteria**. Tiers: **[L]** local, **[C]** Colab.

### Phase 0 - Foundation
Goal: reproducible base and agreed plan. Tier: mostly [L].
1. [L] Create repo layout (section 5); add `.gitignore` for dataset/weights/runs; move `archive (n)` folders into `dataset/raw/`.
2. [L] Fix git (`safe.directory`), make first commit.
3. [L] Write docs: project context, architecture, dataset plan, FGD plan, Android plan, benchmark protocol, licensing, decisions; create `configs/project.yaml`.
4. [L] Environment: decide local torch (CUDA wheel cu118/cu121, or CPU-only); install Android Studio, SDK, platform-tools; obtain physical phone and record model.
5. [C] Build the Colab notebook skeleton: Drive mount, repo clone, dataset unzip, GPU check, env logging, resume logic.
6. [L] Write the **compatibility matrix** (family / teacher / student / FGD taps / framework / export / runtime / risks).
Outputs: repo, docs, configs, matrix. Exit: **user reviews the matrix before any full training.**

### Phase 1 - Dataset (v1 built; finish and harden)
Goal: trustworthy frozen dataset. Tier: [L] (annotation of large pools on [C]).
1. [L] Convert VOC XML / YOLO sources into unified YOLO + recognition annotations with group ids.
2. [L] Run QC; fix or drop defective items; remove near-duplicates.
3. [L] Acquire external sets (Roboflow CC BY Indian, Kaggle Indian, Open Images plates, RodoSol subset); check and log each licence. UFPR-ALPR is non-commercial only.
4. [L/C] Auto-annotate unlabeled pools; review queue; accept only verified labels.
5. [L] Group-level split 70/15/15; prove zero leakage; freeze `dataset_v1` (hash, version.json); zip.
6. [L] Collect and manually label a small own-gate test set (300-500 images, with permission).
7. [L] Upload `dataset_v1.zip` to Drive.
Outputs: dataset_v1, statistics, report. Exit: >= ~6-10k independent plate images, manually verified val/test, leakage script passes.

### Phase 2 - Baselines
Goal: three trained baselines and the teachers. 
1. [L] Smoke test each family: 1-2 epochs, subset, imgsz 320-416, batch 2-4, AMP, workers 0-2. Confirms data loading, config, logging, export hook.
2. [L] Optional small baseline (nano, subset) to sanity-check metrics.
3. [C] Full baselines: YOLO11n, YOLO26n (Ultralytics), YOLOv6n (official repo), imgsz 640, AMP, seed logged, `save_period` to Drive.
4. [C] Train teachers (s, m where useful) on the same data.
5. [L] Pull back best.pt/results.csv/config; evaluate on val and test; choose teacher size by experiment (accuracy, stability, VRAM).
Outputs: 3 baselines, teacher(s), metrics table. Exit: reproducible metrics for each; provenance recorded (especially YOLOv6 self-distillation status).

### Phase 3 - FGD
Goal: working, tested distillation for all three families.
1. [L] Implement `training/fgd/` loss core with tests first (tiny tensors, CPU).
2. [L] Implement adapters: YOLO11 first, then YOLO26, then YOLOv6; verify hook capture and teacher/student channel mapping; 2-step forward/backward at imgsz 320, batch 1-2.
3. [C] FGD smoke test, 2-5 epochs, full setup: teacher loads, features captured, loss finite, backward OK, VRAM OK.
4. [C] Lambda sweep per family; select by validation mAP.
5. [C] Final FGD students (same seed policy as baselines).
6. [L] Pull back and evaluate; compare to baselines.
Outputs: 3 FGD students, sweep logs. Exit: tests green, finite and decreasing FGD loss, results with provenance. Cite Yang et al. 2022.

### Phase 4 - Export and conversion testing
Goal: all six models run identically in ONNX. Tier: [L].
1. Export each `.pt` to ONNX at fixed imgsz.
2. Run parity script against PyTorch on fixed images.
3. Determine output format per family; write parsers (YOLO26 NMS-free vs YOLOv6/11 raw).
4. Generate `model_metadata.json`.
5. Test with ONNX Runtime on desktop (CPU) first, then on phone in Phase 5.
Outputs: 6 ONNX files + metadata + parity report. Exit: parity within tolerance, or documented failure with the smallest workaround.

### Phase 5 - Android application
Goal: model-agnostic, filterable, benchmarkable app. Tier: [L] (OCR training, if custom, on [C]).
1. CameraX preview and capture.
2. One detector via ORT end-to-end (YOLO11n first).
3. `Detector` interface + 3 detectors + runtime switch.
4. TimeFilter -> RegionFilter -> AreaFilter with `FilterDecision` reasons.
5. OCR bake-off on cropped plates (PaddleOCR / ML Kit / Tesseract / custom); pick by measured accuracy and latency.
6. `PlateValidator` with configurable patterns.
7. `PlateDecoder` (state, RTO, series, number) and `EntryLog` with CSV export for Excel; confirm a live reading over several frames before logging.
8. Benchmark logger, CSV/JSON export.
9. UI: model selector, filter controls, photo/live modes, overlay with decoded plate, entry list, stats.
10. Unit tests: filters, ROI, parsing, decoding, scaling. Emulator for logic; physical phone for performance.
Outputs: installable APK. Exit: all six models switchable on device; filters emit correct reasons; a scanned plate shows its state/RTO; entry and benchmark logs export.

### Phase 6 - Experiments and reporting
Goal: honest, reproducible results. Tier: [L] on-phone, [C] extra training.
1. Run benchmark protocol (warm-up, fixed duration, >= 3 reps, same conditions).
2. Ablations: A baseline vs FGD; B filter configs; C model comparison; D (optional) OCR comparison.
3. Result scripts -> final matrix table + graphs.
4. Write methodology, limitations, privacy/retention, attribution, licensing.
5. Report FPS, effective FPS, and skip rate separately. Never pre-write conclusions.
Outputs: results tables, graphs, report. Exit: every number traceable to a run record.

---

## 7. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Colab session limit / disconnect | Lost training | Drive checkpoints every epoch, resume, shorter runs |
| A100 not available on free tier | Delays | Pro plan, or reduce batch and run on lower GPU with documented change |
| 4 GB VRAM / 8 GB RAM locally | OOM | Nano models, small batch, imgsz <= 416, workers 0-2, heavy work on Colab |
| Local torch is CPU-only | No local GPU smoke | Install cu118/cu121 wheel or update driver; CPU fallback for tests |
| YOLOv6 checkpoint self-distilled | Confounds FGD claim | Record provenance; prefer non-self-distilled baseline |
| YOLO26 NMS-free output | Parser mismatch | Per-family output parsers; parity tests |
| Dataset leakage | Inflated metrics | Group split + automated leakage check |
| Licence (UFPR non-commercial, AGPL) | Legal | `licensing.md`; academic use noted |
| No Android SDK / phone | Blocks Phase 5 | Install early; emulator for logic |
| Time overrun | Incomplete coverage | Priority order: dataset > baselines + FGD (>= 2 families) > app > benchmarks; say so openly |

## 8. Scope control
One class, 640 px, ONNX Runtime only, three nano students, Indian plates only. Excluded until the core works: INT8/NNAPI, vehicle detection, tracking, server databases, cloud features, face recognition, owner lookup. The local entry log with CSV export is in scope. Colab is for training only; the app is fully offline.

## 9. Open decisions
1. Kaggle token / Roboflow API key available?
2. Physical Android phone model; permission to photograph a gate?
3. Colab plan (Pro/Pro+), Drive space for dataset and checkpoints?
4. Confirm official YOLOv6 repo as a separate pipeline.
5. Accept AGPL-3.0 (Ultralytics) for an academic project?
6. Local torch: CUDA wheel (cu118/cu121), driver update, or CPU-only?
