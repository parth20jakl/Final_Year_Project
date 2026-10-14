# Sample Android UI (rough, NOT final)

Rough layouts to discuss elements and colours. Numbers and the car image are placeholders. Final design is the owner's decision.

| File | Screen | Purpose |
|---|---|---|
| `00_style_guide.png` | Colours, type, components | Palette and reusable pieces |
| `01_live.png` | Live camera | Model selector, FPS/latency HUD, region box, plate box, filter chips, last plate, Stop |
| `02_photo_result.png` | Photo mode result | Plate text, validity, confidence, timing breakdown, Retake/Save |
| `03_filters.png` | Frame filters | Time interval (50-200 ms), region of interest, area threshold, detection confidence |
| `04_models.png` | Model selector | 3 families x baseline/FGD, runtime switch |
| `05_benchmark.png` | Benchmark | Config, FPS/P50/P95/RAM, latency histogram, decision breakdown, export |
| `06_detection_log.png` | Detection log | Per-frame reason (PROCESSED / SKIP_TIME / SKIP_AREA / SKIP_REGION) |
| `overview_all_screens.png` | All screens side by side | Quick look |

Colours: background #0B1220, surface #121C2F, accent cyan #22D3EE; Processed #34D399, Skip time #60A5FA, Skip area #FBBF24, Skip region #A78BFA, error/live #F87171.

Regenerate: `.venv-train\Scripts\python.exe design\make_ui_samples.py`
