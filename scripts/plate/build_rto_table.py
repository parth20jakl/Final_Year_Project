"""Fill the RTO table in configs/plate_codes.json from the wikitext of Wikipedia's
"List of Regional Transport Office districts in India" (CC BY-SA 4.0).

  curl -L -o page.wiki "https://en.wikipedia.org/w/index.php?title=List_of_Regional_Transport_Office_districts_in_India&action=raw&oldid=<REV>"
  python scripts/plate/build_rto_table.py page.wiki --revision <REV> --retrieved YYYY-MM-DD            # report only
  python scripts/plate/build_rto_table.py page.wiki --revision <REV> --retrieved YYYY-MM-DD --write

Per state section, every table row gives: column 1 = code(s), column 2 = office name. Nothing is invented:
rows that cannot be parsed are listed in the report and left out.
"""
from __future__ import annotations

import argparse
import collections
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODES = ROOT / "configs" / "plate_codes.json"
SOURCE_URL = "https://en.wikipedia.org/wiki/List_of_Regional_Transport_Office_districts_in_India"
# The page has no Andaman and Nicobar section. These two codes are the ones that third-party listings agreed on
# in a web search (2026-11-27); recorded separately in the output.
SUPPLEMENT = {"AN": {"01": "Port Blair (Sri Vijaya Puram)", "02": "Car Nicobar"}}
SUPPLEMENT_SOURCES = [
    "https://www.drivespark.com/rto-vehicle-registration-details/andaman-nicobar-islands-an-01/",
    "https://vahanx.in/rto-office-details/andaman-and-nicobar-islands/AN-02",
]


def strip_markup(s: str) -> str:
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    return s


def split_top(line: str, sep: str) -> list[str]:
    """Split on sep only outside [[links]] and {{templates}}."""
    out, depth, cur, i = [], 0, "", 0
    while i < len(line):
        two = line[i:i + 2]
        if two in ("[[", "{{"):
            depth += 1
            cur += two
            i += 2
        elif two in ("]]", "}}"):
            depth = max(0, depth - 1)
            cur += two
            i += 2
        elif depth == 0 and line.startswith(sep, i):
            out.append(cur)
            cur = ""
            i += len(sep)
        else:
            cur += line[i]
            i += 1
    return out + [cur]


def parse_cell(raw: str) -> dict:
    parts = split_top(raw, "|")
    attrs, text = "", raw
    if len(parts) > 1 and re.search(r"\b(rowspan|colspan|style|class|scope|align|width|data-sort-value)\b\s*=", parts[0]):
        attrs, text = parts[0], "|".join(parts[1:])
    span = lambda k: int(m.group(1)) if (m := re.search(k + r"""\s*=\s*["']?(\d+)""", attrs)) else 1
    return {"text": text, "rowspan": span("rowspan"), "colspan": span("colspan")}


def tables(section: str):
    """Yield each wikitable as a list of rows; a row is (is_header, [cells])."""
    rows, cells, header, inside = [], [], True, False
    for line in section.splitlines():
        s = line.strip()
        if s.startswith("{|"):
            inside, rows, cells, header = True, [], [], True
        elif not inside:
            continue
        elif s.startswith("|}") or s.startswith("|-"):
            if cells:
                rows.append((header, cells))
            cells, header = [], True
            if s.startswith("|}") or s == "|-|}":
                inside = False
                yield rows
        elif s.startswith("|+"):
            continue
        elif s.startswith(("|", "!")):
            bang = s[0] == "!"
            header = header and bang
            body = s[1:]
            pieces = split_top(body, "||")
            if bang:
                pieces = [q for p in pieces for q in split_top(p, "!!")]
            cells += [parse_cell(p) for p in pieces]
        elif cells:
            cells[-1]["text"] += "\n" + s
    if inside:
        if cells:
            rows.append((header, cells))
        yield rows


def grid(rows):
    """Expand rowspan/colspan into (is_header, [text, ...]) rows."""
    carry: dict[int, list] = {}
    for header, cells in rows:
        line, col, queue = [], 0, list(cells)
        while queue or any(c >= col for c in carry):
            if col in carry:
                text, left = carry[col]
                line.append(text)
                if left <= 1:
                    del carry[col]
                else:
                    carry[col][1] -= 1
                col += 1
            elif queue:
                cell = queue.pop(0)
                for _ in range(cell["colspan"]):
                    line.append(cell["text"])
                    if cell["rowspan"] > 1:
                        carry[col] = [cell["text"], cell["rowspan"] - 1]
                    col += 1
            else:
                line.append("")
                col += 1
        yield header, line


def clean(s: str) -> str:
    s = re.sub(r"\[\[(?:File|Image):[^\]]*\]\]", "", s)
    while re.search(r"\{\{[^{}]*\}\}", s):
        s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^\[\]|]*\|)?([^\[\]|]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://\S+\s*([^\]]*)\]", r"\1", s)
    s = re.sub(r"<br\s*/?>", ", ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s.replace("'''", "").replace("''", ""))
    s = re.sub(r"\s+", " ", s).strip(" ,;:*")
    return s


def parse(text: str):
    text = strip_markup(text)
    heads = list(re.finditer(r"^==\s*([A-Z]{2})\s*[—–-]\s*(.+?)\s*==\s*$", text, flags=re.M))
    result, problems = {}, collections.defaultdict(list)
    for n, h in enumerate(heads):
        st = h.group(1)
        end = heads[n + 1].start() if n + 1 < len(heads) else len(text)
        offices: dict[str, list[str]] = {}
        for table in tables(text[h.end():end]):
            expanded = list(grid(table))
            first_header = next((r for hd, r in expanded if hd and r and clean(r[0]).lower().startswith("code")), None)
            if first_header is None:
                continue  # tables of old codes, schemes, etc.
            for hd, row in expanded:
                if hd or len(row) < 2:
                    continue
                code_cell, name = clean(row[0]), clean(row[1])
                if not name and len(row) > 2:
                    name = clean(row[2])  # state-wide series have no office, only a jurisdiction
                found = re.findall(rf"\b{st}\s*[-– ]?\s*(\d{{1,3}})(?!\d)(\s?[A-Z]{{1,2}}\b)?", code_cell)
                if not found:
                    problems[st].append(f"no code in: {code_cell[:60]!r} | {name[:60]!r}")
                    continue
                for num, suffix in found:
                    if suffix:
                        problems[st].append(f"suffixed series skipped: {code_cell[:40]!r} | {name[:60]!r}")
                        continue
                    key = f"{int(num):02d}"
                    if not name or name.lower() in ("not allocated", "defunct"):
                        problems[st].append(f"no office name for {st}{key}: {name!r}")
                        continue
                    offices.setdefault(key, [])
                    if name not in offices[key]:
                        offices[key].append(name)
        result[st] = {k: " / ".join(v) for k, v in sorted(offices.items(), key=lambda kv: int(kv[0]))}
    return result, problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("wikitext", type=Path)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    rto, problems = parse(a.wikitext.read_text(encoding="utf-8"))
    data = json.loads(CODES.read_text(encoding="utf-8"))
    # state-wide series: the page gives only the authority's abbreviation as the office name
    for key, name in rto.get("AP", {}).items():
        if name == "RTA":
            rto["AP"][key] = "Andhra Pradesh state-wide series (no office)"
    for st, offices in SUPPLEMENT.items():
        if rto.get(st):
            raise SystemExit(f"{st} is now on the page - remove it from SUPPLEMENT")
        rto[st] = dict(offices)
    missing = sorted(set(data["states"]) - {s for s, v in rto.items() if v})
    extra = sorted(set(rto) - set(data["states"]))
    for st in sorted(rto):
        names = rto[st]
        long = [f"{st}{k}" for k, v in names.items() if len(v) > 70]
        dup = [f"{st}{k}" for k, v in names.items() if " / " in v]
        print(f"{st}: {len(names):4d} codes  long={long[:6]}  multi={dup[:6]}  problems={len(problems.get(st, []))}")
    print("total", sum(map(len, rto.values())), "| states without codes:", missing, "| unknown sections:", extra)
    for st, items in problems.items():
        for item in items:
            print("  ", st, item)
    if not a.write:
        return
    if missing or extra:
        raise SystemExit("refusing to write: state sections do not match the state list")
    data["_about"] = (
        "Public registration-code tables used to decode an Indian number plate. Single source of truth for Python "
        "tooling and the Android app (copy into assets at build time). The 'rto' table is generated by "
        "scripts/plate/build_rto_table.py - do not hand-edit it. NOT yet checked against official Parivahan / "
        "MoRTH lists: verify before the report or any deployment."
    )
    data["rto_source"] = {
        "title": "List of Regional Transport Office districts in India (Wikipedia contributors)",
        "url": SOURCE_URL, "revision": a.revision, "retrieved": a.retrieved,
        "licence": "CC BY-SA 4.0", "changes": "code and office-name columns extracted, wiki markup removed",
    }
    data["rto_source_supplement"] = {"states": sorted(SUPPLEMENT), "urls": SUPPLEMENT_SOURCES}
    data["rto_aliases"] = {"OR": "OD", "TS": "TG", "UA": "UK"}
    data["rto"] = {st: rto[st] for st in sorted(rto)}
    CODES.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", CODES)


if __name__ == "__main__":
    main()
