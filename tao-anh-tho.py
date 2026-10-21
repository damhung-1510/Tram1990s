#!/usr/bin/env python3
"""Xuất ảnh thơ giấy hoài cổ 4K dọc, tối đa 10 dòng.

Ví dụ:
  python3 tao-anh-tho.py --id Q038
  python3 tao-anh-tho.py --id Q038 --title "Vầng trăng ai xẻ làm đôi"
"""

import argparse
import json
import math
import random
import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "templates" / "anh-tho-giay-hoai-co"
CONFIG_PATH = TEMPLATE_DIR / "template.json"
DATA_PATH = ROOT / "Thơ" / "bai-chinh-thuc.json"
OUT_DIR = ROOT / "Anh_completed"


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_poem(poem_id):
    poems = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    try:
        return next(p for p in poems if p["id"] == poem_id)
    except StopIteration:
        raise SystemExit(f"Không tìm thấy bài {poem_id}")


def rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def font(path, size):
    return ImageFont.truetype(path, size=size)


def text_width(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0]


def fit_poem_font(draw, lines, path, max_width, max_height):
    for size in range(100, 55, -2):
        fnt = font(path, size)
        line_height = round(size * 1.52)
        if max(text_width(draw, line, fnt) for line in lines) <= max_width:
            if len(lines) * line_height <= max_height:
                return fnt, line_height
    return font(path, 56), 85


def quote_size(block_height):
    """Kích thước dấu nháy tăng theo chiều cao khổ thơ, nhưng có giới hạn."""
    return max(132, min(260, round(block_height * 0.14)))


def paper_background(width, height, base_color, seed=1990):
    """Tạo giấy trắng ngà có hạt, sợi giấy và phần rìa cũ rất nhẹ."""
    random.seed(seed)
    base = Image.new("RGB", (width, height), base_color)
    noise = Image.effect_noise((width, height), 7.5).convert("L").filter(ImageFilter.GaussianBlur(0.45))
    warm_noise = Image.merge("RGB", (noise, noise, noise))
    base = Image.blend(base, warm_noise, 0.055)

    fibers = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fibers)
    for _ in range(1300):
        x = random.randrange(width)
        y = random.randrange(height)
        length = random.randrange(20, 150)
        shade = random.choice([(114, 92, 67, 8), (255, 255, 255, 15), (148, 117, 79, 6)])
        fd.line((x, y, min(width, x + length), y + random.choice((-1, 0, 1))), fill=shade, width=1)
    base = Image.alpha_composite(base.convert("RGBA"), fibers)

    vignette = Image.new("L", (width, height), 0)
    vd = ImageDraw.Draw(vignette)
    for i in range(190, 0, -1):
        alpha = int(32 * (i / 190) ** 2)
        vd.rectangle((190 - i, 190 - i, width - 190 + i, height - 190 + i), outline=alpha, width=3)
    edge = Image.new("RGBA", (width, height), (92, 61, 35, 0))
    edge.putalpha(vignette.filter(ImageFilter.GaussianBlur(25)))
    return Image.alpha_composite(base, edge)


def centered(draw, xy, text, fnt, fill, spacing=4):
    draw.multiline_text(xy, text, font=fnt, fill=fill, anchor="mm", align="center", spacing=spacing)


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:70]


def render(poem, title_override=None, output=None):
    cfg = load_config()
    canvas = cfg["canvas"]
    type_cfg = cfg["typography"]
    content_cfg = cfg["content"]
    width, height = canvas["width"], canvas["height"]
    lines = [line.strip() for line in poem["text"].splitlines() if line.strip()]
    max_lines = int(content_cfg["maxLines"])
    if not lines:
        raise SystemExit("Bài thơ không có nội dung")
    if len(lines) > max_lines:
        raise SystemExit(f"Template chỉ nhận tối đa {max_lines} dòng; bài này có {len(lines)} dòng")

    image = paper_background(width, height, rgb(canvas["color"]))
    draw = ImageDraw.Draw(image)
    ink = rgb(type_cfg["ink"])
    muted = rgb(type_cfg["mutedInk"])
    accent = rgb(type_cfg["accent"])
    tagline_ink = rgb(type_cfg.get("taglineInk", type_cfg["mutedInk"]))

    # Khung giấy và dấu trang tối giản.
    draw.rounded_rectangle((132, 132, width - 132, height - 132), radius=10, outline=(*muted, 88), width=3)
    draw.rounded_rectangle((158, 158, width - 158, height - 158), radius=8, outline=(*muted, 38), width=1)
    brand_font = font(type_cfg["fontBold"], 94)
    tag_font = font(type_cfg["fontRegular"], 34)
    # Đưa nhận diện vào vùng 4:5 trung tâm để vẫn thấy trên Facebook Home.
    centered(draw, (width // 2, 650), content_cfg["pageName"], brand_font, accent)
    centered(draw, (width // 2, 745), content_cfg["pageTagline"], tag_font, tagline_ink)
    draw.line((width // 2 - 150, 820, width // 2 + 150, 820), fill=(*accent, 135), width=3)
    draw.ellipse((width // 2 - 6, 814, width // 2 + 6, 826), fill=accent)

    title = title_override or poem["title"]
    if content_cfg.get("showTitle", True):
        title_font = font(type_cfg["fontBold"], 78)
        while text_width(draw, title, title_font) > width - 500 and title_font.size > 48:
            title_font = font(type_cfg["fontBold"], title_font.size - 2)
        centered(draw, (width // 2, 690), title.upper(), title_font, ink)
        draw.line((width // 2 - 90, 785, width // 2 + 90, 785), fill=(*muted, 95), width=2)

    poem_font, line_height = fit_poem_font(
        draw, lines, type_cfg["fontRegular"], width - 520, 2050
    )
    block_height = len(lines) * line_height
    # Căn giữa cả cụm dấu nháy + khổ thơ trong khoảng giữa tên page và tác giả.
    # Khổ thơ vẫn căn trái theo yêu cầu trước đó.
    content_top = 860 if not content_cfg.get("showTitle", True) else 1150
    content_bottom = 2640
    content_center = (content_top + content_bottom) / 2
    group_offset_from_poem = ((len(lines) - 1.5) * line_height) / 2
    top = round(content_center - group_offset_from_poem)
    poem_left = 300
    if content_cfg.get("showQuotes", True):
        quote_font = font(type_cfg["fontBold"], round(quote_size(block_height) * 3.0))
        draw.text((poem_left, top - line_height * 1.0), "“", font=quote_font,
                  fill=accent, anchor="lm")
    for index, line in enumerate(lines):
        draw.text((poem_left, top + index * line_height), line, font=poem_font,
                  fill=ink, anchor="lm")

    # Tên tác giả/nguồn nằm riêng để không lẫn vào phần thơ.
    author = poem.get("author") or "Không rõ tác giả"
    author_font = font(type_cfg["fontItalic"], 56)
    author_y = 2780
    author_text = f"— {author} —"
    centered(draw, (width // 2, author_y), author_text, author_font, muted)

    gap = 40
    author_box = draw.textbbox((width // 2, author_y), author_text, font=author_font, anchor="mm")
    divider_y = author_box[3] + gap
    footer_text = "LƯU GIỮ NHỮNG VẦN THƠ ĐẸP"
    footer_font = font(type_cfg["fontRegular"], 29)
    footer_box_at_zero = draw.textbbox((0, 0), footer_text, font=footer_font, anchor="mm")
    footer_y = divider_y + gap - footer_box_at_zero[1]
    draw.line((350, divider_y, width - 350, divider_y), fill=(*muted, 48), width=2)
    centered(draw, (width // 2, footer_y), footer_text, footer_font, muted)

    watermark_font = font(type_cfg["fontBold"], 34)
    watermark = content_cfg["pageName"]
    watermark_width = text_width(draw, watermark, watermark_font)
    draw.text((width - 205 - watermark_width, height - 250), watermark,
              font=watermark_font, fill=(*accent, 72))

    OUT_DIR.mkdir(exist_ok=True)
    if output is None:
        output = OUT_DIR / f"{poem['id']}_{slug(title)}_4K.png"
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, "PNG", optimize=True, compress_level=7, dpi=(300, 300))
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--id", required=True, help="mã bài trong Thơ/bai-chinh-thuc.json")
    ap.add_argument("--title", help="đổi tên bài trên ảnh, không sửa dữ liệu gốc")
    ap.add_argument("--output", help="đường dẫn PNG đầu ra")
    args = ap.parse_args()
    out = render(load_poem(args.id), args.title, args.output)
    print(out)


if __name__ == "__main__":
    main()
