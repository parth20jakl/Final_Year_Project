# Sample UI mockups (2026-10-14, Local)

Request: rough images of the Android UI (elements and colours) in a sample folder; not final design.

## Steps followed
1. Derived the screens from `docs/project_workflow.md` section 3.3 (model selector, time/region/area filters, photo vs live, result overlay, benchmark logger, filter reasons).
2. Wrote `design/make_ui_samples.py` (Pillow, 2x supersampled, 720x1500 logical px per screen). Fonts: Segoe UI from Windows.
3. Ran it with `.venv-train` -> `design/ui_samples/` (7 screens + overview). Looked at the overview and the live screen to check layout and text.
4. Added `design/ui_samples/README.md` (screen list, palette).

## Notes
- Placeholder data only (FPS 18.4, plate MH 12 AB 1234, comparison numbers). No result of any experiment is shown.
- These are static PNGs, not a working app; the real UI will be built in Kotlin/Compose after Android Studio is installed.
