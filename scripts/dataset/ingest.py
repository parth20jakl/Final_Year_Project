"""Ingest every source (local archives + downloaded external sets) into unified JSONL records.

Outputs
  dataset/processed/records_labeled.jsonl     images that already have manual plate boxes
  dataset/processed/records_unlabeled.jsonl   images without plate labels (auto-annotation pool)
  dataset/annotations/recognition_manual.jsonl  plate text annotations (detection/recognition kept separate)
  dataset/reports/ingest_log.json             everything dropped and why
"""
from __future__ import annotations

import collections
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (  # noqa: E402
    ANNOT, IMG_EXT, PROCESSED, RAW, REPORTS, ROOT, Record, box_ok, clip_box, dhash, imread,
    norm_text, oriented_size, plausible_indian_plate, rel, short_id, write_jsonl,
)

LOG: dict[str, list] = collections.defaultdict(list)
LIC_A = "unknown-provenance (user supplied; academic use)"


def recover_zip_only(n: int) -> None:
    """Some zip members failed to extract on Windows (long names). Recover them with short names."""
    zpath = ROOT / f"archive ({n}).zip"
    folder = ROOT / f"archive ({n})"
    if not zpath.exists():
        return
    have = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    out_root = RAW / "zip_recovered" / f"archive_{n}"
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            name = info.filename.rstrip("/")
            if info.is_dir() or name in have:
                continue
            d, _, fn = name.rpartition("/")
            stem, dot, ext = fn.rpartition(".")
            tag = short_id("r", stem)
            dst = out_root / d / f"{tag}.{ext}"
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(z.read(info))
            # keep original name for provenance
            LOG["recovered_from_zip"].append({"zip": zpath.name, "member": name[:120], "as": rel(dst)})


def make_record(prefix: str, key: str, path: Path, source: str, lic: str, boxes, texts, group, domain,
                label_source="manual", extra=None) -> Record | None:
    try:
        w, h, orient = oriented_size(path)
    except Exception as e:  # unreadable
        LOG["unreadable"].append({"path": rel(path), "err": str(e)[:100]})
        return None
    img = imread(path)
    if img is None:
        LOG["unreadable"].append({"path": rel(path), "err": "cv2 decode failed"})
        return None
    if img.shape[1] != w or img.shape[0] != h:  # trust decoded (EXIF-applied) size
        w, h = img.shape[1], img.shape[0]
    return Record(id=short_id(prefix, key), path=rel(path), source=source, license=lic, width=w, height=h,
                  boxes=[list(map(float, b)) for b in boxes], plate_texts=list(texts), group=group,
                  label_source=label_source, domain=domain, dhash=dhash(img), extra=extra or {})


def find_image(dirp: Path, stem: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG", ".bmp"):
        p = dirp / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def parse_voc(xml_path: Path):
    r = ET.parse(xml_path).getroot()
    size = r.find("size")
    xw, xh = int(float(size.findtext("width"))), int(float(size.findtext("height")))
    objs = []
    for o in r.findall("object"):
        bb = o.find("bndbox")
        if bb is None:
            continue
        box = [float(bb.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax")]
        objs.append((o.findtext("name", "").strip(), box))
    return xw, xh, objs


def fit_voc(rec_w, rec_h, xw, xh, boxes, path):
    """Check XML canvas against the EXIF-oriented image; scale if only resolution differs, drop if rotated."""
    if (rec_w, rec_h) == (xw, xh):
        return boxes
    if abs(rec_w / rec_h - xw / xh) < 0.01:  # same aspect, different resolution -> scale
        sx, sy = rec_w / xw, rec_h / xh
        return [[b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy] for b in boxes]
    LOG["size_mismatch_dropped"].append({"path": rel(path), "xml": [xw, xh], "img": [rec_w, rec_h]})
    return None


def ingest_voc_dir(dirs: list[Path], prefix: str, source: str, lic: str, domain: str, text_is_name: bool,
                   plate_names=("number_plate",), group_mode="text") -> list[Record]:
    recs: list[Record] = []
    for d in dirs:
        for xp in sorted(d.rglob("*.xml")):
            img = find_image(xp.parent, xp.stem)
            if img is None:
                LOG["xml_without_image"].append(rel(xp))
                continue
            try:
                xw, xh, objs = parse_voc(xp)
            except Exception as e:
                LOG["bad_xml"].append({"path": rel(xp), "err": str(e)[:80]})
                continue
            boxes, texts = [], []
            for name, b in objs:
                if text_is_name:
                    boxes.append(b)
                    texts.append(norm_text(name))
                elif name in plate_names:
                    boxes.append(b)
            if not boxes:
                LOG["no_plate_objects"].append(rel(xp))
                continue
            rec = make_record(prefix, rel(img), img, source, lic, boxes, texts, "", domain)
            if rec is None:
                continue
            fb = fit_voc(rec.width, rec.height, xw, xh, rec.boxes, img)
            if fb is None:
                continue
            kept, kt = [], []
            for i, b in enumerate(fb):
                b = clip_box(b, rec.width, rec.height)
                if box_ok(b, rec.width, rec.height):
                    kept.append(b)
                    kt.append(texts[i] if i < len(texts) else "")
                else:
                    LOG["invalid_box_dropped"].append({"path": rel(img), "box": b})
            if not kept:
                continue
            rec.boxes, rec.plate_texts = kept, kt
            t = rec.plate_texts[0] if rec.plate_texts else ""
            if text_is_name:
                if plausible_indian_plate(t):
                    rec.group = f"txt:{t}"
                else:
                    rec.group = f"file:{rec.id}"
                    LOG["implausible_plate_text"].append({"path": rel(img), "text": t})
                    rec.extra["text_suspect"] = True
            else:
                rec.group = f"file:{rec.id}"
            recs.append(rec)
    return recs


def ingest_a3() -> list[Record]:
    recs = []
    base = ROOT / "archive (3)"
    for seq in sorted(p for p in base.iterdir() if p.is_dir()):
        for ip in sorted(seq.glob("*.jpg")):
            lp = ip.with_suffix(".txt")
            if not lp.exists():
                LOG["image_without_label"].append(rel(ip))
                continue
            rec = make_record("a3", rel(ip), ip, "archive3_video_frames", LIC_A, [], [], f"seq:{seq.name}", "indian")
            if rec is None:
                continue
            for line in lp.read_text().splitlines():
                p = line.split()
                if len(p) != 5 or p[0] != "0":
                    LOG["bad_yolo_line"].append({"path": rel(lp), "line": line})
                    continue
                xc, yc, bw, bh = map(float, p[1:])
                b = clip_box([(xc - bw / 2) * rec.width, (yc - bh / 2) * rec.height,
                              (xc + bw / 2) * rec.width, (yc + bh / 2) * rec.height], rec.width, rec.height)
                if box_ok(b, rec.width, rec.height):
                    rec.boxes.append(b)
                    rec.plate_texts.append("")
            if rec.boxes:
                recs.append(rec)
    return recs


def ingest_keremberke() -> list[Record]:
    recs = []
    base = RAW / "external" / "keremberke"
    lic = "CC BY 4.0 (Roboflow 'Vehicle Registration Plates' via keremberke/license-plate-object-detection)"
    for split in ("train", "valid", "test"):
        d = base / split
        js = json.loads((d / "_annotations.coco.json").read_text())
        by_img = collections.defaultdict(list)
        for a in js["annotations"]:
            by_img[a["image_id"]].append(a["bbox"])
        for im in js["images"]:
            bxs = by_img.get(im["id"])
            if not bxs:
                continue
            p = d / im["file_name"]
            if not p.exists():
                LOG["missing_image"].append(rel(p))
                continue
            boxes = [[x, y, x + w, y + h] for x, y, w, h in bxs]
            stem = im["file_name"].split("_jpg.rf.")[0].split("_png.rf.")[0]
            rec = make_record("kb", rel(p), p, "keremberke_roboflow_vrp", lic, boxes, [""] * len(boxes),
                              f"kb:{stem}", "external", extra={"orig_split": split})
            if rec is None:
                continue
            ok = [clip_box(b, rec.width, rec.height) for b in rec.boxes]
            rec.boxes = [b for b in ok if box_ok(b, rec.width, rec.height)]
            rec.plate_texts = [""] * len(rec.boxes)
            if rec.boxes:
                recs.append(rec)
    return recs


def ingest_unlabeled() -> list[Record]:
    recs = []
    pools = [
        ("a2", ROOT / "archive (2)", "archive2_unlabeled", LIC_A),
        ("a2r", RAW / "zip_recovered" / "archive_2", "archive2_unlabeled", LIC_A),
        ("a5", ROOT / "archive (5)", "archive5_indian_vehicle", LIC_A),
        ("a6", ROOT / "archive (6)", "archive6_IVDB", LIC_A),
    ]
    for pre, d, src, lic in pools:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if p.suffix.lower() in IMG_EXT:
                rec = make_record(pre, rel(p), p, src, lic, [], [], "", "indian", label_source="none")
                if rec:
                    rec.group = f"file:{rec.id}"
                    recs.append(rec)
            elif p.suffix.lower() == ".gif":
                LOG["skipped_gif"].append(rel(p))
    return recs


def main() -> None:
    for n in (2, 4):
        recover_zip_only(n)
    a4 = ROOT / "archive (4)"
    a4r = RAW / "zip_recovered" / "archive_4"
    labeled: list[Record] = []
    dirs_google = [a4 / "google_images"] + ([a4r / "google_images"] if (a4r / "google_images").exists() else [])
    labeled += ingest_voc_dir(dirs_google, "a4g", "archive4_google_images", LIC_A, "indian", True)
    labeled += ingest_voc_dir([a4 / "State-wise_OLX"], "a4o", "archive4_statewise_olx", LIC_A, "indian", True)
    labeled += ingest_voc_dir([a4 / "video_images"], "a4v", "archive4_video_images", LIC_A, "indian", True)
    labeled += ingest_a3()
    dc = RAW / "external" / "datacluster_in"  # images live in images/, XML in Annotations/
    for xp in sorted((dc / "Annotations").glob("*.xml")):
        ip = dc / "images" / f"{xp.stem}.jpg"
        if not ip.exists():
            LOG["xml_without_image"].append(rel(xp))
            continue
        xw, xh, objs = parse_voc(xp)
        bxs = [b for n, b in objs if n == "number_plate"]
        rec = make_record("dc", rel(ip), ip, "datacluster_indian_sample",
                          "CC BY-NC-ND 4.0 (academic use only; do not redistribute)", bxs, [""] * len(bxs),
                          f"dc:{xp.stem}", "indian")
        if rec is None or not bxs:
            continue
        fb = fit_voc(rec.width, rec.height, xw, xh, rec.boxes, ip)
        if fb is None:
            continue
        rec.boxes = [b for b in (clip_box(b, rec.width, rec.height) for b in fb) if box_ok(b, rec.width, rec.height)]
        rec.plate_texts = [""] * len(rec.boxes)
        if rec.boxes:
            labeled.append(rec)
    labeled += ingest_keremberke()
    unlabeled = ingest_unlabeled()

    PROCESSED.mkdir(parents=True, exist_ok=True)
    n1 = write_jsonl(PROCESSED / "records_labeled.jsonl", (r.__dict__ for r in labeled))
    n2 = write_jsonl(PROCESSED / "records_unlabeled.jsonl", (r.__dict__ for r in unlabeled))
    rec_ann = ({"image_id": r.id, "bbox": b, "plate_text": t, "label_source": "manual", "text_suspect": r.extra.get("text_suspect", False)}
               for r in labeled for b, t in zip(r.boxes, r.plate_texts) if t)
    n3 = write_jsonl(ANNOT / "recognition_manual.jsonl", rec_ann)
    summary = {
        "labeled_images": n1, "unlabeled_images": n2, "recognition_rows": n3,
        "by_source": dict(collections.Counter(r.source for r in labeled)),
        "unlabeled_by_source": dict(collections.Counter(r.source for r in unlabeled)),
        "dropped": {k: len(v) for k, v in LOG.items()},
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "ingest_log.json").write_text(json.dumps({"summary": summary, "details": LOG}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
