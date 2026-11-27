# Share the project on GitHub (2026-11-27, Local)

## Owner instruction
Push the project (docs, procedural documentation, design, scripts and other files the team needs to view) to https://github.com/parth20jakl/Final_Year_Project.

## Steps followed
1. Checked the branch and remote: `master` was 7 commits ahead of `origin/master`, 0 behind.
2. Checked visibility: an anonymous API request returned 404; SSH access (`git@github-personal`) works.
3. Searched the commits to be pushed and the new files for keys, tokens and passwords: only mentions of "API key", no values. Largest file to push: a 385 KB UI mockup.
4. Committed the 2026-11-27 work and ran `git push origin master`.

## What is in the repository
`docs/`, `procedural documentation/`, `design/`, `scripts/`, `configs/`, `colab/`, `tests/`, requirement files, `.gitignore`.

## Not in the repository (ignored by `.gitignore`)
| Item | Reason |
|---|---|
| `dataset/`, `archive (2..6)/` | large; some data may not be redistributed (see `docs/licensing.md`) |
| `weights/`, `runs/` | generated model files |
| `.venv-train/` | local environment; rebuild from `requirements-local-train.txt` |
| `.claude/` | existing ignore rule for assistant files; several documents refer to it |

## Notes for the team
- Dataset links in the documents do not work from a clone; the data has to be shared separately.
- `colab/train_colab_skeleton.ipynb` still points to dataset_v3 and has a placeholder repository URL.
- The notebook and one procedural record contain the ID of the Drive folder used for the dataset. Keep that folder shared only with named accounts.
