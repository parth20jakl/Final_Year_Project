# Procedural documentation

A record of exactly what was done, and how, for every task in this project. One file per step.

## File template
- Task / phase / step, date, tier (Local or Colab)
- Goal
- Inputs (files, versions)
- Steps followed (numbered, with exact commands)
- Outputs (files created/changed)
- Results / observations
- Problems and deviations
- Reproduce (how to rerun)

## Index
| File | Task | Date |
|---|---|---|
| `setup_compute_split_and_workflow.md` | Compute split (Local vs Colab), skill update, workflow document | 2026-10-05 |
| `phase1_step1_convert_and_verify_labeled_data.md` | Phase 1 step 1: audit of unified labeled data (55 missing originals found) | 2026-10-05 |
| `phase1_step2_qc_run.md` | Phase 1 step 2: QC run (clean, 0 leakage, 3,921 in-split near-dup pairs) | 2026-10-05 |
| `phase1_step3a_credentials_and_tooling.md` | Phase 1 step 3a: Kaggle/Roboflow tooling + auth verified | 2026-10-05 |
| `phase1_step3b_licence_check.md` | Phase 1 step 3b: licence/size check of candidate external datasets | 2026-10-05 |
| `phase1_step3c_roboflow_download.md` | Phase 1 step 3c: 4 Roboflow Indian sets downloaded (3,482 imgs, CC BY 4.0) | 2026-10-05 |
| `phase1_step3d_roboflow_ingest_split_v2.md` | Phase 1 step 3d: incremental Roboflow ingest, split v2 (+2,704 train, 552 near-dups dropped) | 2026-10-14 |
| `phase0_foundation.md` | Phase 0 status table (configs, Colab skeleton, compatibility matrix) | 2026-10-14 |
| `phase1_step5a_v2_export_qc_and_fixes.md` | Phase 1 step 5a: v2 export, QC found leakage + rescale defect, fixes | 2026-10-14 |
| `phase1_step5b_freeze_and_phase_closeout.md` | Phase 1 step 5b: clean QC, dataset_v2 frozen, git commit, Phase 1 status | 2026-10-14 |
| `phase1_step4_human_review_and_indian_only_v3.md` | Review queue decisions, nationality check, Indian-only split v3 + dataset_v3 frozen | 2026-10-14 |
| `phase2_local_env_ultralytics_cpu_smoke.md` | Local venv (ultralytics + CPU torch), model load, 1-epoch CPU smoke test | 2026-10-14 |
| `design_sample_ui_mockups.md` | Sample Android UI mockups (7 screens + palette) in design/ui_samples | 2026-10-14 |
| `phase1_step6_audit_foreign_cleanup_v4.md` | Re-audit, foreign-image list (deletion pending), dataset_v4, label defects, plate-decoding spec | 2026-11-27 |
| `phase5_prep_rto_code_table.md` | RTO office table for all states in configs/plate_codes.json | 2026-11-27 |
| `repo_push_to_github.md` | Pushed the project to GitHub for the team; what is and is not included | 2026-11-27 |
