# Phase 1, Step 3b - Licence and size check of external datasets (2026-10-05, Local)

## Goal
Decide which external datasets may be used before downloading anything.

## Steps followed
1. Kaggle API (`KaggleApi.dataset_list(search=...)`) for 4 search phrases; recorded `license_name` and `total_bytes` per hit.
2. `dataset_metadata` / `dataset_list_files` for the 4 most relevant sets: description/licence text is not exposed by the API (returned None); file lists inspected.
3. WebSearch (universe.roboflow.com) for Indian plate sets: found 5 CC BY 4.0 sets with image counts. WebSearch for Open Images V7 licensing: annotations CC BY 4.0, images CC BY 2.0.
4. WebFetch of the Kaggle page for `sunrajbishnolia/license-plate-detection` returned no description (page is JS-rendered).
5. Appended the table to `docs/licensing.md`.

## Findings
- 4 Roboflow Indian sets (451 / 548 / 833 / 1,650 images, CC BY 4.0) + small CC0/Apache Kaggle sets are usable with attribution.
- The big Kaggle set (~15k) has an unverified licence and is Roboflow-augmented (multiple augmented copies of each source image, including in its test folder), so its real independent size is far smaller and it would add leakage risk. Not recommended without manual page check.
- Our Datacluster sample is CC BY-NC-ND on Hugging Face but CC0 on Kaggle: we keep the stricter terms.
- Roboflow images may overlap one another and our archives; the existing dHash dedup/split handles this after ingest.
- Licence info came from listings/snippets, not full licence pages; it must be re-confirmed at download time.

## Outputs
`docs/licensing.md` (new section). No data downloaded or changed.
