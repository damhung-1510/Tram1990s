#!/usr/bin/env python3
"""Thêm / xóa bài ở mọi file cùng lúc (HTML, CSV, JSON, kịch bản ElevenLabs, khóa template, câu mở đầu).

    python3 quan-ly-bai.py --xoa T01 T02               # xóa bài
    python3 quan-ly-bai.py --them Thơ/trich-dan-moi.json   # thêm bài từ file JSON

File JSON để thêm là một danh sách; mỗi bài gồm:
  id, title, kind ("Thơ" | "Ca dao" | "Trích dẫn"), author, text (các dòng cách nhau bằng \\n),
  hook (câu mở đầu), mood (nho-que | doi-cho | tinh-yeu | co-don | thu-hoai-niem | binh-yen | nghi-luc | biet-on | me | tung-trai),
  voice ("Nữ" | "Nam" | "Cả hai"), note (nhãn ngắn), source (đường dẫn nguồn, không bắt buộc).
  tts (kịch bản có tag riêng), voice_why (chỉ dẫn giọng đọc) là tùy chọn.
Sau khi thêm bài mới: lồng tiếng bằng elevenlabs-tts.py --ids <id>.
"""
import argparse, csv, json, re, sys
from pathlib import Path

R = Path(__file__).resolve().parent
sys.path.insert(0, str(R))
TH = R / "Thơ"

MOOD_FOLDERS = {   # thư mục video gợi ý theo mood: (chính, thêm)
    "binh-yen": (["19_Suong-mu", "Chill_100_9x16/04_Phong_canh", "Chill_100_9x16/03_Suoi"], ["01_Thien-nhien"]),
    "tung-trai": (["14_Co-don-tram-lang", "13_Mua-cua-so", "05_Dem-thanh-pho"], ["16_Nguoi-gia-ky-uc", "Chill_100_9x16/05_Co_don"]),
    "biet-on": (["07_Ca-phe-tra", "20_Cafe-sach-vang"], ["16_Nguoi-gia-ky-uc"]),
    "me": (["16_Nguoi-gia-ky-uc", "13_Mua-cua-so", "14_Co-don-tram-lang"], ["07_Ca-phe-tra", "20_Cafe-sach-vang", "17_Tau-hoa-ga"]),
    "thu-hoai-niem": (["15_Mua-thu", "19_Suong-mu"], ["16_Nguoi-gia-ky-uc"]),
    "nho-que": (["14_Co-don-tram-lang", "04_Hoang-hon-troi-may", "16_Nguoi-gia-ky-uc"], ["17_Tau-hoa-ga"]),
    "tinh-yeu": (["08_Lang-man-tinh-yeu", "Chill_100_9x16/02_Hoa", "02_Bien-song-nuoc"], ["13_Mua-cua-so", "18_Binh-minh-hoang-hon"]),
    "doi-cho": (["14_Co-don-tram-lang", "13_Mua-cua-so", "17_Tau-hoa-ga"], ["05_Dem-thanh-pho", "Chill_100_9x16/01_Mua", "Chill_100_9x16/05_Co_don"]),
    "co-don": (["14_Co-don-tram-lang", "05_Dem-thanh-pho"], ["13_Mua-cua-so"]),
    "nghi-luc": (["09_Hanh-trinh-duong-xa", "01_Thien-nhien"], ["18_Binh-minh-hoang-hon"]),
}


def syl(s):
    return max(1, len(re.findall(r"\w+", s)))


def hookfmt(h):
    h = h.replace("!", ".").strip().rstrip(":.")
    h = re.sub(r",\s*", ", ", h)
    return "[softly] " + h + ". [long pause]"


def fmt(text):
    """Ngắt dòng và đặt tag nhịp theo mẫu B (nhẹ, tâm tình, không nhấn mạnh)."""
    out = []
    for st in text.strip().split("\n\n"):
        ls = [x.strip() for x in st.split("\n") if x.strip()]
        for i, l in enumerate(ls):
            end = l[-1]
            core = l.rstrip(",;:.!…").replace("!", ",")
            core = re.sub(r",\s*", ", [short pause] ", core).replace("[short pause] ,", "[short pause]")
            e = "," if end in ",;" else ("?" if end == "?" else ".")
            if end == "?":
                core = core.rstrip("?")
            out.append(core + e + " " + ("[long pause]" if i == len(ls) - 1 else "[pause]"))
    return re.sub(r" \[long pause\]$", "", "\n".join(out).rstrip())


def fmt_quote(text):
    """Nhịp đọc trích dẫn như lời tự sự: nhẹ, đều và không đổi tông giữa bài."""
    lines = [x.strip() for x in text.strip().split("\n") if x.strip()]
    out = []
    for i, line in enumerate(lines):
        pause = "[long pause]" if i == 1 else "[pause]"
        if i == len(lines) - 1:
            pause = ""
        prefix = "[softly] " if i == 0 else ""
        out.append(prefix + line + (f" {pause}" if pause else ""))
    return "\n".join(out)


def load_html():
    f = R / "GHEP_THO_VIDEO.html"
    t = f.read_text(encoding="utf-8")
    j = t.find("const D=") + 8
    D, end = json.JSONDecoder().raw_decode(t[j:])
    return f, t[:j], D, t[j + end:]


def jload(p, default):
    return json.load(open(p, encoding="utf-8")) if Path(p).exists() else default


def jsave(p, d):
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def read_csv():
    f = R / "GHEP_THO_VIDEO.csv"
    return list(csv.reader(open(f, encoding="utf-8-sig"))) if f.exists() else []


def write_csv(rows):
    csv.writer(open(R / "GHEP_THO_VIDEO.csv", "w", encoding="utf-8-sig", newline=""), lineterminator="\n").writerows(rows)


def md_remove_section(path, ids):
    """Bỏ các mục '## ID. ...' (kịch bản) và dòng '| ID |' (bảng câu mở đầu)."""
    f = Path(path)
    if not f.exists():
        return
    lines = f.read_text(encoding="utf-8").split("\n")
    out, skip = [], False
    for l in lines:
        m = re.match(r"^## (\w+)\. ", l)
        if m:
            skip = m.group(1) in ids
        elif l.startswith("## "):
            skip = False
        if skip:
            continue
        m2 = re.match(r"^\| (\w+) \|", l)
        if m2 and m2.group(1) in ids:
            continue
        out.append(l)
    f.write_text("\n".join(out), encoding="utf-8")


def tidy_ui(head, rest):
    rest = rest.replace(",'Truyện ngắn']", "]")          # bỏ chip lọc "Truyện ngắn"
    return head, rest


def xoa(ids):
    ids = set(ids)
    f, head, D, rest = load_html()
    before = len(D["poems"])
    D["poems"] = [p for p in D["poems"] if p["id"] not in ids]
    head, rest = tidy_ui(head, rest)
    f.write_text(head + json.dumps(D, ensure_ascii=False) + rest, encoding="utf-8")
    for name in ("bai-chinh-thuc.json", "elevenlabs-script.json"):
        d = jload(TH / name, [])
        jsave(TH / name, [x for x in d if x["id"] not in ids])
    for name in ("template-bai.json", "da-long-tieng.json"):
        d = jload(TH / name, {})
        jsave(TH / name, {k: v for k, v in d.items() if k not in ids})
    rows = read_csv()
    if rows:
        write_csv([rows[0]] + [r for r in rows[1:] if r[0] not in ids])
    md_remove_section(TH / "elevenlabs-script.md", ids)
    md_remove_section(TH / "cau-mo-dau-duyet.md", ids)
    print(f"Đã xóa {before - len(D['poems'])} bài khỏi trang; còn {len(D['poems'])} bài.")


def them(file):
    import tao_video as T
    items = json.load(open(file, encoding="utf-8"))
    f, head, D, rest = load_html()
    have = {p["id"] for p in D["poems"]}
    rows = read_csv()
    bct = jload(TH / "bai-chinh-thuc.json", [])
    els = jload(TH / "elevenlabs-script.json", [])
    keys = jload(TH / "template-bai.json", {})
    md_script, md_hook = [], []
    n_new = 0
    D["moods"]["tung-trai"] = "Trích dẫn · từng trải"
    morning_folder = "Vid/hello_morning"
    morning_root = R / morning_folder
    if morning_root.is_dir():
        D["folders"][morning_folder] = sorted(
            p.name for p in morning_root.glob("*.mp4") if not p.name.startswith(".")
        )
    for it in items:
        if it["id"] in have:
            print("bỏ qua (đã có):", it["id"]); continue
        mood = it["mood"]
        if it["kind"] == "Trích dẫn Ngày mới" and morning_folder in D["folders"]:
            fo, ex = [morning_folder], []
        else:
            fo, ex = MOOD_FOLDERS.get(mood, MOOD_FOLDERS["binh-yen"])
        fo = [x for x in fo if x in D["folders"]]; ex = [x for x in ex if x in D["folders"]]
        hook = it.get("hook", "")
        est = round(syl(it["text"]) / 2.8 + (10 if hook else 3.5))      # có lời mở: +10s; không: 0,5s đầu + 3s cuối
        if it["kind"].startswith("Trích dẫn") and not hook:
            tts = fmt_quote(it["text"])
        else:
            tts = (hookfmt(hook) + "\n" if hook else "[softly] ") + fmt(it["text"])
        tts = it.get("tts") or tts
        voice_why = it.get("voice_why") or "giọng đọc gợi ý"
        D["poems"].append(dict(id=it["id"], kind=it["kind"], title=it["title"], text=it["text"], author=it["author"],
                               note=it.get("note", ""), mood=mood, folders=fo, extra=ex, exact=None, files=None,
                               url=it.get("source"), vnote=it.get("vnote"), voice=it["voice"],
                               voice_why=voice_why, audio=[], est=est, hook=hook, tts=tts))
        label = D["moods"].get(mood, mood)
        like = next((r for r in rows[1:] if len(r) > 7 and r[3] == label), None)
        row = [it["id"], it["kind"], it["title"], label, it.get("note", ""), " | ".join(fo), " | ".join(ex),
               like[7] if like else "", it["voice"], voice_why, str(est), hook, tts]
        if rows:
            hdr = rows[0]
            row += [""] * (len(hdr) - len(row))
            rows.append(row[:max(len(hdr), len(row))])
        bct.append(dict(id=it["id"], title=it["title"], kind=it["kind"], mood=label, voice=it["voice"],
                        author=it["author"], hook=hook, text=it["text"], tts=tts, est=est))
        els.append(dict(id=it["id"], title=it["title"], voice=it["voice"], hook=hook, tts=tts))
        if it.get("template"):         # bài chỉ định sẵn template (vd: trích dẫn văn xuôi chạy chữ 2 trang)
            nl = len([x for x in it["text"].split("\n") if x.strip()])
            k, per, why = it["template"], it.get("per_page") or -(-nl // 2), "chỉ định khi thêm bài"
        else:
            k, per, why = T.auto_template(dict(id=it["id"], kind=it["kind"], text=it["text"]))
        keys.setdefault(it["id"], dict(template=k, per_page=per, ghi_chu=why, tieu_de=it["title"]))
        md_script.append(f"## {it['id']}. {it['title']}  \nGiọng: {it['voice']}\n```\n{tts}\n```\n")
        if hook:
            md_hook.append(f"| {it['id']} | {it['title']} | {hook} |")
        n_new += 1
    head, rest = tidy_ui(head, rest)
    f.write_text(head + json.dumps(D, ensure_ascii=False) + rest, encoding="utf-8")
    jsave(TH / "bai-chinh-thuc.json", bct); jsave(TH / "elevenlabs-script.json", els); jsave(TH / "template-bai.json", keys)
    if rows:
        write_csv(rows)
    with open(TH / "elevenlabs-script.md", "a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(md_script))
    with open(TH / "cau-mo-dau-duyet.md", "a", encoding="utf-8") as fh:
        fh.write("\n".join(md_hook) + "\n")
    print(f"Đã thêm {n_new} bài; trang có {len(D['poems'])} bài.")


def main():
    ap = argparse.ArgumentParser(description="Thêm / xóa bài ở mọi file")
    ap.add_argument("--xoa", nargs="+", metavar="ID")
    ap.add_argument("--them", metavar="FILE.json")
    a = ap.parse_args()
    if not a.xoa and not a.them:
        ap.print_help(); return
    if a.xoa:
        xoa(a.xoa)
    if a.them:
        them(a.them)
    import importlib.util
    spec = importlib.util.spec_from_file_location("dd", R / "danh-dau-long-tieng.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.main()   # cập nhật nhãn đã lồng tiếng, template


if __name__ == "__main__":
    main()
