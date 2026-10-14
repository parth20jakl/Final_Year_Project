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

## External candidates - licence check 2026-10-05 (metadata only, NOT downloaded)
| Candidate | Size | Licence as listed | Verdict |
|---|---|---|---|
| Roboflow Universe: license-plate-detection-khhkb/indian-license-plate-detection-6tmbr | 833 imgs | CC BY 4.0 (Universe listing) | candidate - attribution required |
| Roboflow Universe: nivu/indian-license-plate-knte7 | 1,650 imgs | CC BY 4.0 | candidate |
| Roboflow Universe: i5hub/indian-number-plate-keeo5-zllyl | 548 imgs | CC BY 4.0 | candidate |
| Roboflow Universe: vehicle-license-plate/indian-vehicle-plate | 451 imgs | CC BY 4.0 | candidate |
| Roboflow Universe: iiser/indian-vehicle-license-plate | 60 imgs | CC BY 4.0 | too small, optional |
| Kaggle kedarsai/indian-license-plates-with-labels | ~66 MB | CC0 | candidate; provenance unclear, dedup against ours |
| Kaggle deepakat002/indian-vehicle-number-plate-yolo-annotation | ~97 MB, video frames, YOLO txt | CC0 | candidate; frames are highly redundant |
| Kaggle dataclusterlabs/indian-number-plates-dataset | ~152 MB, VOC XML | CC0 on Kaggle (our HF sample was CC BY-NC-ND 4.0: conflict, keep stricter) | we already hold the 47-image sample |
| Kaggle paneraghanshyam/gujarat-vehicle-number-plates-yolo-ready | ~46 MB | Apache 2.0 | candidate (Gujarat only) |
| Kaggle sunrajbishnolia/license-plate-detection | ~910 MB, ~15k imgs | "Other (specified in description)" - description unreadable via API/fetch | **blocked until licence confirmed**; files are Roboflow-augmented (`.rf.<hash>` several variants per source image) -> inflates counts, risks leakage |
| Kaggle saisirishan/indian-vehicle-dataset | 187 MB | CC BY-NC-ND 4.0 | already in use as archive 5; academic only, no redistribution |
| Open Images V7 "Vehicle registration plate" | thousands, global | annotations CC BY 4.0, images CC BY 2.0 (per FiftyOne docs) | candidate, attribution; not Indian |
| UFPR-ALPR, RodoSol-ALPR | - | signed request / academic | NOT acquired |
Licences above come from listings/search snippets; re-confirm on each source page when downloading and record the download date and version.

## Downloaded 2026-10-05, ingested 2026-10-14 (split v2, train only)
| Component | Source | Licence | Images used | Notes |
|---|---|---|---|---|
| rf_ilpd_khhkb | https://universe.roboflow.com/holi-milan/indian-license-plate-detection-6tmbr (v1) | CC BY 4.0 | 833 | attribution required |
| rf_nivu | https://universe.roboflow.com/nivu/indian-license-plate-knte7 (v1) | CC BY 4.0 | 1,209 of 1,650 | 441 dropped (near-dup of val/test or no box) |
| rf_i5hub | https://universe.roboflow.com/i5hub/indian-number-plate-keeo5-zllyl (v1) | CC BY 4.0 | 428 of 548 | |
| rf_vlp | https://universe.roboflow.com/vehicle-license-plate/indian-vehicle-plate (v1) | CC BY 4.0 | 234 of 451 | `vehicle` class dropped |
