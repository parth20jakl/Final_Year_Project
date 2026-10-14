# Compatibility matrix (Phase 0 gate - REVIEW BEFORE ANY FULL TRAINING)

Status: draft 2026-10-14. Items marked **verify** are assumptions to confirm in the Phase 2/3 smoke tests; nothing here is a result.

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

## Gate
Reviewer approves: families, teacher sizes, tap strategy, per-family framework, YOLOv6 provenance policy, Colab-only heavy training.
