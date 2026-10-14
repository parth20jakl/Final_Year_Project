"""Download Roboflow Universe sets (YOLO format) into dataset/raw/external/roboflow/<name>. Key from env ROBOFLOW_API_KEY."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from roboflow import Roboflow

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dataset" / "raw" / "external" / "roboflow"
SETS = {
    "rf_ilpd_khhkb": ("license-plate-detection-khhkb", "indian-license-plate-detection-6tmbr"),
    "rf_nivu": ("nivu", "indian-license-plate-knte7"),
    "rf_i5hub": ("i5hub", "indian-number-plate-keeo5-zllyl"),
    "rf_vlp": ("vehicle-license-plate", "indian-vehicle-plate"),
}


def main() -> None:
    rf = Roboflow(api_key=os.environ["ROBOFLOW_API_KEY"])
    log = {}
    for name, (ws, proj) in SETS.items():
        dst = OUT / name
        if dst.exists() and any(dst.iterdir()):
            print("skip existing", name)
            continue
        try:
            p = rf.workspace(ws).project(proj)
            vs = p.versions()
            ver = max(vs, key=lambda v: int(str(v.version).split("/")[-1]))
            vnum = int(str(ver.version).split("/")[-1])
            dst.mkdir(parents=True, exist_ok=True)
            ver.download("yolov8", location=str(dst), overwrite=True)
            log[name] = {"workspace": ws, "project": proj, "version": vnum, "licence_listed": "CC BY 4.0"}
            print("ok", name, "v", vnum)
        except Exception as e:  # keep going, record the failure
            log[name] = {"error": str(e)[:300]}
            print("FAILED", name, str(e)[:200])
    (OUT / "download_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())

