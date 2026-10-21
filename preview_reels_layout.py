from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "templates" / "tho-reels-doc-nhanh" / "preview-layout.png"
W, H = 1080, 1920

bg = Image.new("RGB", (W, H), (42, 31, 29))
draw = ImageDraw.Draw(bg)
for y in range(H):
    t = y / H
    draw.line((0, y, W, y), fill=(int(35 + 26*t), int(27 + 18*t), int(28 + 14*t)))
draw.ellipse((520, 170, 1280, 950), fill=(112, 76, 65))
bg = bg.filter(ImageFilter.GaussianBlur(70))
draw = ImageDraw.Draw(bg, "RGBA")
draw.rectangle((0, 0, W, H), fill=(15, 12, 12, 90))

font_dir = Path("/System/Library/Fonts/Supplemental")
regular = str(font_dir / "Georgia.ttf")
bold = str(font_dir / "Georgia Bold.ttf")
small = ImageFont.truetype(regular, 24)
brand = ImageFont.truetype(bold, 25)
hook = ImageFont.truetype(regular, 48)
poem = ImageFont.truetype(regular, 43)
title = ImageFont.truetype(regular, 43)
author = ImageFont.truetype(bold, 43)

cream = (248, 239, 223, 255)
gold = (214, 196, 163, 255)
draw.text((115, 150), "TRẠM 1990s", font=brand, fill=gold, spacing=4)
draw.line((115, 195, 230, 195), fill=(214, 196, 163, 190), width=2)

draw.multiline_text((115, 350), "Có những ngày người ta\nchỉ muốn trở về nhà", font=hook,
                    fill=cream, spacing=16, align="left")
draw.multiline_text((115, 800), "Có những ngày chỉ muốn về quê,\nNghe gió đi qua hàng song cửa.\nKhông cần ai hỏi mình đang mệt mỏi,\nChỉ cần một mái nhà và bữa cơm xưa.",
                    font=poem, fill=cream, spacing=22, align="left")

draw.multiline_text((115, 1570), "“Có những ngày”", font=title, fill=cream, spacing=10)
draw.text((115, 1640), "NGUYỄN THIÊN NGÂN", font=author, fill=gold)
draw.text((115, 1790), "PREVIEW · THƠ REELS ĐỌC NHANH", font=small, fill=(220, 210, 195, 170))

OUT.parent.mkdir(parents=True, exist_ok=True)
bg.save(OUT)
print(OUT)
