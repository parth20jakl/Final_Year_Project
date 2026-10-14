# Setup: compute split, skill update, workflow document (2026-10-05, Local)

## Goal
Record the Local PC vs Google Colab A100 split in the project context and produce a detailed workflow document.

## Steps followed
1. Listed `.claude/` and read `SKILL.md`, `references/plan.md`, `references/constraints.md`, `docs/`.
2. Verified hardware: `nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv` -> RTX 2050, 4096 MiB, driver 528.20. `python -c "import torch..."` -> `2.14.0+cpu`, CUDA unavailable. PowerShell `Win32_ComputerSystem.TotalPhysicalMemory` -> 7.71 GB.
3. Rewrote `.claude/skills/anpr-fgd-android/references/environment.md` (two tiers, local limits, Colab rules).
4. Rewrote `references/plan.md` with [LOCAL]/[COLAB] tags per phase.
5. Edited `references/constraints.md` ("remote GPU" -> "cloud inference"; Colab training allowed) and `SKILL.md` (rule 11, pointer to workflow doc).
6. Wrote `docs/project_workflow.md` (architecture, stack, phases 0-6, risks).

## Outputs
Files above; no code executed beyond hardware checks.

## Problems / deviations
Earlier audit (RTX 3050 6 GB) did not match this machine; superseded by the measured values.
