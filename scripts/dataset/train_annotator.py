"""Train the auto-annotation teacher (plate detector) on MANUAL labels only (train split).
Its val split is the Indian manual val set, so auto-label quality is measured on held-out human labels."""
from __future__ import annotations
import argparse
from pathlib import Path
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="yolo11s.pt")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--fraction", type=float, default=1.0)
    ap.add_argument("--name", default="annotator")
    a = ap.parse_args()
    m = YOLO(str(ROOT / "weights" / a.model) if (ROOT / "weights" / a.model).exists() else a.model)
    m.train(data=str(ROOT / "dataset/processed/yolo_manual/anpr_detect.yaml"), epochs=a.epochs, imgsz=a.imgsz,
            batch=a.batch, fraction=a.fraction, workers=4, device=0, amp=True, seed=0, deterministic=False,
            project=str(ROOT / "runs"), name=a.name, exist_ok=True, patience=5, cache=False, plots=False)

if __name__ == "__main__":
    main()
