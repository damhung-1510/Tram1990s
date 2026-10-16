#!/usr/bin/env python3
"""Gắn khóa template vào từng bài, lưu ở Thơ/template-bai.json (mỗi bài một dòng, sửa tay được).

    python3 gan-template.py            # chỉ gắn cho bài chưa có khóa, giữ nguyên khóa bạn đã sửa
    python3 gan-template.py --reset    # gắn lại tất cả theo quy tắc

Quy tắc: ≤7 dòng → tho-hoai-co (chữ tĩnh 1 trang); đúng 8 dòng → tho-hoai-co-chay-chu-2-trang (2 trang × 4 dòng);
>8 dòng → tho-hoai-co-chay-chu-nhieu-trang (mỗi trang 6 dòng); truyện ngắn → nhiều trang, mỗi trang 2 câu.
Khóa hợp lệ: tho-hoai-co · tho-hoai-co-chay-chu-2-trang · tho-hoai-co-chay-chu-nhieu-trang.
tao_video.py chỉ đọc khóa này khi tạo video.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tao_video as T

poems = T.load_poems()
keys = {} if "--reset" in sys.argv else T.load_keys()
new = 0
for pid, p in poems.items():
    if pid not in keys:
        k, per, why = T.auto_template(p)
        keys[pid] = dict(template=k, per_page=per, ghi_chu=why, tieu_de=p["title"])
        new += 1
json.dump(keys, open(T.TEMPLATE_KEYS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(keys)} bài có khóa template ({new} bài mới gắn).")
from collections import Counter
for k, n in Counter(v["template"] for v in keys.values()).items():
    print(f"  {n:3} bài → {T.LABELS[k]}")
