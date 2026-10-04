# Licensing and attribution register (dataset side; extend for code/models)

Use is academic / non-commercial research. Re-verify each licence before any redistribution.

| Component | Source | Version / date | Licence | How used | Modifications | Redistribute? |
|---|---|---|---|---|---|---|
| archive (2)-(6) | user-supplied zips (original sources not stated in the files; archive 4 OLX part matches GitHub ChSatyaSavith/NumberPlate_Annotated_Dataset; archive 5 matches Kaggle saisirishan/indian-vehicle-dataset) | as received 2026-10-03 | **UNKNOWN - provenance unverified** | training/val/test (labelled), auto-annotation pool | VOC/YOLO -> unified YOLO, resized | **No** until provenance confirmed |
| keremberke/license-plate-object-detection | https://huggingface.co/datasets/keremberke/license-plate-object-detection (Roboflow "Vehicle Registration Plates v1", 8,823 images) | downloaded 2026-10-04 | CC BY 4.0 (README.dataset.txt) | training only (external domain) | COCO -> YOLO, resized | Yes with attribution |
| Datacluster Indian number plates (sample) | https://huggingface.co/datasets/Dataclusterlabspvtltd/indian-number-plates-dataset (47 images) | downloaded 2026-10-04 | CC BY-NC-ND 4.0 | academic training/eval only | format conversion only (no derivative redistribution) | **No** |
| Ultralytics YOLO11/YOLO26 code and `yolo11s.pt` | https://github.com/ultralytics/ultralytics (assets v8.4.0) | ultralytics 8.4.150 | AGPL-3.0 (enterprise licence available) | annotator + training | none | per AGPL |
| UFPR-ALPR, RodoSol-ALPR | https://github.com/raysonlaroca | - | academic only, **signed request required** | NOT downloaded | - | No |

Not used yet / candidates: Roboflow Indian sets (CC BY 4.0, need API key), Kaggle Indian sets (need token and licence check), Open Images V7 plates (CC BY).

Citation reminders: FGD (Yang et al., CVPR 2022) must be cited in the report; it is not an original contribution of this project.
