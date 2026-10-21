#!/usr/bin/env python3
"""Tạo biến thể Reels Đọc Nhanh dùng một ảnh nền blur nhẹ."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "templates" / "tho-reels-doc-nhanh" / "template.json"
TARGET = ROOT / "templates" / "tho-reels-anh-mo" / "template.json"


def make_template():
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    doc["name"] = "Trạm 1990s · Reels Ảnh Mờ"
    media = doc["media"][0]
    media.update(name="Ảnh nền", kind="image", duration=30.0, hasAudio=False,
                 placeholder=True)
    for clip in doc["clips"]:
        if clip.get("trackId") not in ("BG", "FG"):
            continue
        clip["kind"] = "image"
        clip["name"] = "Ảnh nền mờ" if clip["trackId"] == "FG" else "Ảnh nền backdrop"
        if clip["trackId"] == "FG":
            clip["scale"] = 1.05
            clip["videoEffects"] = [{
                "id": "concat.gaussian-blur",
                "params": {"radius": 6.0},
                "enabled": True,
            }]
    return doc


if __name__ == "__main__":
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(make_template(), indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(TARGET)
