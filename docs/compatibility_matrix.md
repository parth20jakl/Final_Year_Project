# Compatibility matrix (Phase 0 gate)

**Status: APPROVED by the project owner on 2026-10-14.** Full Colab training may start once the baselines/FGD scripts exist. Items marked **verify** remain assumptions to confirm in the Phase 2/3 smoke tests.

Original draft note: Items marked **verify** are assumptions to confirm in the Phase 2/3 smoke tests; nothing here is a result.

| Item | YOLOv6n | YOLO11n | YOLO26n |
|---|---|---|---|
| Framework | official meituan/YOLOv6 repo (separate pipeline) | Ultralytics | Ultralytics |
| Teacher (same family) | YOLOv6s | YOLO11s (m optional) | YOLO26s |
| Baseline weights | official release (**may be self-distilled**: record provenance; prefer non-self-distilled or train from scratch) | `yolo11n.pt` pretrained, fine-tune | `yolo26n.pt` pretrained, fine-tune (**verify** availability in installed ultralytics) |
| FGD adapter | `YOLOv6FGDAdapter` | `YOLO11FGDAdapter` | `YOLO26FGDAdapter` |
| FGD taps | neck outputs feeding the 3 detect scales (P3/P4/P5) - find by semantic position | `model.model[16/19/22]`-style neck outputs: **verify indices at runtime**, never hard-code across families | neck outputs before detect head: **verify** |
| Student/teacher channels | n vs s differ -> 1x1 projector | differ -> projector | differ -> projector |
| Detection loss kept | yes (+ lambda * FGD) | yes (hook into trainer loss) | yes; Ultralytics native KD is NOT used |
| Export | official export.py -> ONNX | `model.export(format='onnx')` | `model.export(format='onnx')` (**end-to-end / NMS-free output**) |
| Output parser (Android) | raw predictions + NMS | raw predictions + NMS | NMS-free top-k parser |
| Runtime | ONNX Runtime Mobile | same | same |
| Main risks | self-distilled checkpoint; separate code base; hook points differ | Ultralytics hook into trainer loop; AGPL | NMS-free output differs; newest family, API churn |

## Compute fit
| Task | Local RTX 2050 4 GB / 8 GB RAM | Colab A100 |
|---|---|---|
| Unit tests, FGD loss on tiny tensors | yes (CPU) | - |
| Smoke 1-2 epochs nano, imgsz 320, batch 2-4 | yes (needs CUDA torch, see environment.md) | - |
| Baseline n @640 | no | yes |
| Teacher s/m @640 | no | yes |
| FGD teacher+student @640 | no | yes |
| ONNX export + parity | yes | optional |
| Android build/test | yes | no |

## Gate - approved 2026-10-14
Approved without changes: (1) three families YOLOv6n / YOLO11n / YOLO26n, each baseline and FGD student; (2) same-family teachers one size larger (s; m optional for YOLO11); (3) Ultralytics for YOLO11/26, official YOLOv6 repo as a separate pipeline; (4) record YOLOv6 checkpoint provenance and prefer a non-self-distilled baseline; (5) neck P3/P4/P5 taps chosen per family, never a shared hard-coded index; (6) all heavy training and distillation on Colab, local for code/tests/export/app.

## Local findings (2026-10-14, ultralytics 8.4.177, CPU)
- yolo11n: 181 layers, 2.59M params, `Detect` is layer 23, fed by layers [16, 19, 22] (neck outputs, channels 64/128/256).
- yolo26n: 2.57M params, `Detect` is layer 23. Its feeder layers and NMS-free head output must still be confirmed in Phase 3 (verify).
- A 1-epoch CPU smoke test of yolo11n on 48 images at 320 px ran end to end (24 s). Not a baseline.
