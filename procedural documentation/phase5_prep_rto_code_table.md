# Phase 5 preparation - RTO code table for all states (2026-11-27, Local)

## Owner instruction
Extend the Maharashtra RTO list to the other states, in the appropriate file.

## Steps followed
1. Downloaded the wikitext of Wikipedia "List of Regional Transport Office districts in India" (revision 1387078165) and confirmed it matched that revision.
2. Wrote `scripts/plate/build_rto_table.py`: takes the code and office-name columns from each state section; if the office cell is empty it uses the jurisdiction cell; drops "Not Allocated" / "Defunct" and letter-suffixed sub-series.
3. No Andaman and Nicobar section on the page (latest or previous revision). Added `AN01`, `AN02` from third-party listings found by web search; recorded in `rto_source_supplement`.
4. Ran:
```
curl -L -o page.wiki "https://en.wikipedia.org/w/index.php?title=List_of_Regional_Transport_Office_districts_in_India&action=raw&oldid=1387078165"
python scripts/plate/build_rto_table.py page.wiki --revision 1387078165 --retrieved 2026-11-27 --write
pytest tests/test_plate_codes.py
```
5. Updated `docs/plate_decoding.md`, `docs/licensing.md`, the skill constraints.

## Observations
- The Maharashtra list is now taken from the same source and runs to MH61. Compared with the earlier typed list, names differ for MH06, 16, 20, 25, 31, 43 and 48 (mostly the source omits older or area names).
- A spot check of well-known codes matched. The rest was not checked row by row.
- Names follow the source, so style varies between states (some include "District" or an address).

## Not done
- Verification against official Parivahan / MoRTH lists.
- The decoder itself.
