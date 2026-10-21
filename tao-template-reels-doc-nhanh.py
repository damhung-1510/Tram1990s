#!/usr/bin/env python3
"""Tạo template Reels dễ đọc từ template Hoài Cổ nhiều trang."""
import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "templates" / "tho-hoai-co-chay-chu-nhieu-trang" / "template.json"
TARGET = ROOT / "templates" / "tho-reels-doc-nhanh" / "template.json"


def make_template():
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    doc["name"] = "Trạm 1990s · Reels Đọc Nhanh"

    first_poem = next(c for c in doc["clips"] if c.get("trackId") == "T2")
    clips = [c for c in doc["clips"] if c.get("trackId") != "T2"]
    poem = copy.deepcopy(first_poem)
    poem.update(id="c13", name="Dòng thơ thứ nhất\nDòng thơ thứ hai\nDòng thơ thứ ba\nDòng thơ thứ tư",
                start=0.5, duration=28.8, offsetX=-0.08, offsetY=-0.06)
    poem["text"].update(content=poem["name"], fontSize=0.025, fontWeight=400,
                        italic=False, align="left", color="#f8efdf", maxWidth=0.84,
                        tracking=0.0, lineHeight=1.38)
    poem["videoEffects"] = []
    poem.update(keys=[], fadeIn=0.0, fadeOut=0.0, opacity=1.0)
    clips.append(poem)

    for clip in clips:
        if clip.get("name") == "dim":
            clip["opacity"] = 0.62
        elif clip.get("trackId") == "T1":
            clip.update(offsetX=-0.39, offsetY=-0.405)
            clip["text"].update(fontSize=0.0105, align="left", tracking=0.0045,
                                color="#d6c4a3", maxWidth=0.3)
        elif clip.get("name") == "page rule":
            # Shape and left-aligned text use different anchors in Concat;
            # this offset makes the rule's left edge meet the brand's left edge.
            clip.update(offsetX=-0.341, offsetY=-0.382, opacity=0.75)
            clip["shape"].update(size=0.055, strokeWidth=0.0012)
        elif clip.get("trackId") == "T3":
            clip.update(start=26.0, duration=4.0, offsetX=0.0, offsetY=-0.015)
            clip["text"].update(fontSize=0.025, italic=True, align="center",
                                color="#f8efdf", maxWidth=0.84)
        elif clip.get("trackId") == "T3.2":
            clip.update(start=26.0, duration=4.0, offsetX=0.0, offsetY=0.04)
            clip["text"].update(fontSize=0.025, align="center", color="#d6c4a3",
                                tracking=0.006, maxWidth=0.84)

    order = {"T2": 13, "T3": 14, "T3.2": 15, "FADE": 16}
    doc["clips"] = sorted(clips, key=lambda c: order.get(c.get("trackId"), int(c["id"][1:]) if c["id"][1:].isdigit() else 99))
    return doc


if __name__ == "__main__":
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(make_template(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(TARGET)
