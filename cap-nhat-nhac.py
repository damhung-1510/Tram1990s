#!/usr/bin/env python3
"""Đồng bộ nhóm Piano radio vào trang GHEP_THO_VIDEO.html."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "GHEP_THO_VIDEO.html"
MUSIC = ROOT / "Nhạc nền" / "Piano radio 40s"

SPECS = [
    (
        "PianoRadio_Reverie",
        "Piano radio · Reverie",
        ["tinh-yeu", "doi-cho", "tung-trai"],
        [MUSIC / "Reverie_40s_minus21dB.mp3"],
    ),
    (
        "PianoRadio_Childhood",
        "Piano radio · Childhood",
        ["thu-hoai-niem", "tinh-yeu", "binh-yen"],
        [MUSIC / "Childhood_40s_minus21dB.mp3"],
    ),
    (
        "PianoRadio_AfterTheRain",
        "Piano radio · After the Rain",
        ["tung-trai", "co-don", "thu-hoai-niem", "doi-cho"],
        sorted((MUSIC / "After the Rain").glob("*.mp3")),
    ),
    (
        "PianoRadio_Passages",
        "Piano radio · Passages",
        ["tinh-yeu", "doi-cho", "tung-trai", "co-don"],
        sorted((MUSIC / "Passages").glob("*.mp3")),
    ),
]


def main():
    text = HTML.read_text(encoding="utf-8")
    marker = "const D="
    pos = text.find(marker)
    if pos < 0:
        raise SystemExit("Không tìm thấy dữ liệu const D trong HTML.")
    start = pos + len(marker)
    data, end = json.JSONDecoder().raw_decode(text[start:])

    data["music"] = [
        item for item in data["music"]
        if not item.get("key", "").startswith("PianoRadio_")
    ]
    added = 0
    for key, title, moods, files in SPECS:
        files = [f for f in files if f.exists()]
        if not files:
            continue
        data["music"].append({
            "key": key,
            "title": title,
            "moods": moods,
            "files": [str(f.relative_to(ROOT)) for f in files],
        })
        added += 1

    rest = text[start + end:]
    head = re.sub(
        r"Nhạc nền \(\d+ bài\)",
        f"Nhạc nền ({len(data['music'])} bài)",
        text[:start],
        count=1,
    )
    rest = rest.replace(
        "▶ ${i?'đoạn 2 (từ 1:00)':'đoạn đầu'}",
        "▶ đoạn ${i+1}",
    )
    HTML.write_text(
        head + json.dumps(data, ensure_ascii=False) + rest,
        encoding="utf-8",
    )
    print(f"Đã thêm/cập nhật {added} nhóm Piano radio; tổng {len(data['music'])} nhóm nhạc.")


if __name__ == "__main__":
    main()
