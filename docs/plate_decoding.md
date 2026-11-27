# Number plate decoding and entry log

Requirement from the project owner (2026-11-27). Status: **specified, not yet implemented**.

## 1. Goal

When the app scans a vehicle, it shows more than a text string. It says what the number means, and records when and where the vehicle was seen.

## 2. Example: `MH12CP5156`

| Part | Name | Meaning | Output |
|---|---|---|---|
| `MH` | State / UT code | Registering state | Maharashtra |
| `12` | RTO code | Registering office inside that state | Pune |
| `CP` | Series | Letter series issued by that RTO | CP |
| `5156` | Number | Vehicle's number within the series | 5156 |

Screen output: **MH 12 CP 5156 - Maharashtra vehicle, Pune RTO (MH12), series CP, number 5156.**

The plate shows where the vehicle was registered, not where it is now or where the owner lives. The app does not look up owner details.

## 3. Where this sits in the pipeline

```
detector -> crop -> OCR -> normalise -> PlateValidator -> PlateDecoder -> result screen -> EntryLog -> export
```

* The **detector** still has one class, `license_plate`. It does not learn states or RTOs.
* The state, office, series and number come from the **OCR text** plus a lookup table: [configs/plate_codes.json](../configs/plate_codes.json). No retraining is needed to add a code.
* `PlateDecoder` is a separate module behind its own interface, with unit tests.

## 4. Formats

| Format | Pattern | Example | Handling |
|---|---|---|---|
| Standard | `SS RR X(0-3) NNNN` | MH 12 CP 5156 | Full decode |
| Older / short number | series may be absent, number 1-4 digits | KL 7 BZ 99 | Decode; keep digits as read |
| Delhi | `DL` + district (1-2 digits) + vehicle category letter + series | DL 3C AB 1234 | Special rule: the letter after the district is a category, not part of a normal series |
| Bharat series | `YY BH NNNN X(1-2)` | 22 BH 1234 AA | Show "Bharat series", registration year; no state |
| Temporary / trade (`TC`, `TEMP`), defence, diplomatic (`CD`, `CC`, `UN`) | various | MH 14 TC 206 | Show "special registration"; decode only the parts that are certain |
| Two-line plates (many two-wheelers) | top line then bottom line | MH 47 A / V 6753 | OCR must join top-to-bottom before decoding |

Standard, older, Delhi, temporary and two-line plates were all seen in the current data. A genuine BH-series plate was not specifically checked for, so collect examples before claiming support.

## 5. OCR clean-up rules

1. Upper-case; drop spaces, dots, hyphens and the `IND` band text.
2. Fix look-alike characters **only where the position fixes the type**:
   * letter position: `0->O`, `1->I`, `2->Z`, `5->S`, `8->B`
   * digit position: `O,D,Q->0`, `I,L->1`, `Z->2`, `S->5`, `B->8`
3. Keep both the raw OCR text and the corrected text. Every correction is flagged.
4. Never invent a missing character. Never guess a state or office.

## 6. Result status

| Status | Condition | What the screen shows |
|---|---|---|
| `VALID` | Pattern matches and the state code is known | Full decode |
| `OFFICE_UNKNOWN` | State known, RTO code not in the table | State + RTO code, "office not in table" |
| `CORRECTED` | Valid only after look-alike fixes | Decode, marked "please verify" |
| `UNRECOGNISED` | Pattern or state code does not match | Raw text only; can be edited by hand before saving |

For live video, accept a reading only after the same text appears in several frames (count configurable). This also stops one parked vehicle creating many log rows.

## 7. Entry log and Excel export

One row per accepted vehicle sighting, stored on the phone only.

| Column | Example |
|---|---|
| entry_id | 1 |
| date | 2026-11-30 |
| time | 09:42:18 |
| location | Main Gate (typed once in app settings) |
| direction | IN / OUT (optional setting) |
| plate_number | MH 12 CP 5156 |
| state | Maharashtra |
| rto_code | MH12 |
| rto_office | Pune |
| series | CP |
| number | 5156 |
| status | VALID |
| raw_ocr_text | MH12CP5156 |
| detection_confidence | value from the detector |
| ocr_confidence | value from the OCR engine |
| model | detector used |
| image_file | optional local crop |

The values above are illustrations, not recorded results.

* Export **CSV first** (opens directly in Excel, no extra library). Add native `.xlsx` only if the CSV is not enough.
* Number plates are personal data: keep the log local, let the user delete it, set a retention period, and never put real gate logs in the repository or the report.
* A server database, whitelist and dashboard stay out of scope until the core works.

## 8. Coverage and verification

* State / UT codes: all current codes plus old ones still on the road (`OR`, `UA`, `TS`, `DN`).
* RTO office names: all 36 states and union territories. Taken from Wikipedia's [List of Regional Transport Office districts in India](https://en.wikipedia.org/wiki/List_of_Regional_Transport_Office_districts_in_India) (revision 1387078165, retrieved 2026-11-27, CC BY-SA 4.0 - attribute it in the app and report). That page has no Andaman and Nicobar section, so `AN01` and `AN02` come from third-party listings.
* Rebuild with `scripts/plate/build_rto_table.py`; check with `pytest tests/test_plate_codes.py`. Do not hand-edit the `rto` block.
* Not covered: sub-office series with a letter suffix (for example `TN 15 M`, `HP 08 AA`) resolve to the base code; codes missing from the table give `OFFICE_UNKNOWN`.
* `OR`, `UA` and `TS` plates use the `OD`, `UK` and `TG` tables (`rto_aliases`). Old `DN` codes have no office table.
* Some entries are not a town (state-wide, government or police series), and Andhra Pradesh now issues state-wide codes `AP39` / `AP40`.
* The tables are **not yet verified** against the official Parivahan / MoRTH lists.

## 9. Evaluation

Report separately: detection mAP, OCR exact-match, and **decode accuracy** (state correct, RTO correct, full plate correct) on a hand-checked test set. The 1,692 plate texts in `recognition_manual.jsonl` can test the parser, but they must be checked first: 68 are flagged `text_suspect`, and a few belong to foreign plates or model badges.
