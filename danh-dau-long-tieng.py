#!/usr/bin/env python3
"""Đánh dấu bài đã lồng tiếng ElevenLabs trong các file tổng hợp, đọc từ Thơ/da-long-tieng.json.

    python3 danh-dau-long-tieng.py          # chạy lại bất cứ lúc nào, không bị đánh dấu trùng
elevenlabs-tts.py tự gọi file này sau mỗi bài tạo thành công.
Cập nhật: GHEP_THO_VIDEO.html (nhãn xanh), GHEP_THO_VIDEO.csv (cột "Đã lồng tiếng"),
Thơ/bai-chinh-thuc.json, Thơ/elevenlabs-script.json và .md. Dựng lại HTML/CSV bằng script khác thì chạy lại file này.
"""
import csv, json, re
from pathlib import Path

R = Path(__file__).resolve().parent
STATE = R / "Thơ" / "da-long-tieng.json"
KEYS = R / "Thơ" / "template-bai.json"
LABELS = {"tho-hoai-co": "Thơ Hoài Cổ", "tho-hoai-co-chay-chu-2-trang": "Chạy Chữ 2 Trang",
          "tho-hoai-co-chay-chu-nhieu-trang": "Chạy Chữ Nhiều Trang"}
TPL_BADGE = "${p.tpl?`<span class=\"tag\" style=\"background:transparent;border:1px solid var(--acc)\">📄 ${p.tpl}</span>`:''}"
BADGE = "${p.done?`<span class=\"tag\" style=\"background:#2f7d4f;color:#fff\">✅ Đã lồng tiếng</span>`:''}"


def load_state():
    return json.load(open(STATE, encoding="utf-8")) if STATE.exists() else {}


def tpl_label(pid):
    k = json.load(open(KEYS, encoding="utf-8")).get(pid) if KEYS.exists() else None
    return LABELS.get(k["template"], "") if k else ""


def label(st):
    return f"ElevenLabs {st['voice_id']} · {st['date']}" if st else ""


def ensure_ui(head, rest):
    """Tab "Đã lồng tiếng" + xếp bài đã lồng tiếng lên đầu (chạy nhiều lần không bị trùng)."""
    head = head.replace('<button class="tab" data-t="bo">Bộ ghép ≥30s</button>', '')   # bỏ tab Bộ ghép
    if 'data-t="dub"' not in head:
        old = '<button class="tab" data-t="nhac">'
        assert old in head, "không thấy thanh tab"
        head = head.replace(old, '<button class="tab" data-t="dub">✅ Đã lồng tiếng</button>' + old, 1)
    if "tab!='dub'" not in rest:
        a = ".filter(p=>(!mood||p.mood==mood)"
        assert a in rest, "không thấy bộ lọc"
        rest = rest.replace(a, ".filter(p=>(tab!='dub'||p.done)&&(!mood||p.mood==mood)", 1)
        b = "(!q||(p.text+p.title+p.note).toLowerCase().includes(q)));"
        assert b in rest
        rest = rest.replace(b, "(!q||(p.text+p.title+p.note).toLowerCase().includes(q))).sort((x,y)=>(y.done?1:0)-(x.done?1:0));", 1)
        c = "D.poems.filter(p=>p.mood==k).length"
        if c in rest:
            rest = rest.replace(c, "D.poems.filter(p=>p.mood==k&&(tab!='dub'||p.done)).length")
    if "tab=='dub'" not in rest:
        rest = rest.replace("tab=='tho'", "(tab=='tho'||tab=='dub')")
    if "[data-t=dub]" not in rest:
        rest = rest.replace("function render(){", "function render(){const dn=document.querySelector('[data-t=dub]');if(dn)dn.textContent='✅ Đã lồng tiếng ('+D.poems.filter(p=>p.done).length+')';", 1)
    return head, rest


def main():
    state = load_state()
    # bai-chinh-thuc.json, elevenlabs-script.json
    for name in ("bai-chinh-thuc.json", "elevenlabs-script.json"):
        f = R / "Thơ" / name
        if f.exists():
            d = json.load(open(f, encoding="utf-8"))
            for x in d:
                x["da_long_tieng"] = state.get(x["id"])
                x["template"] = (json.load(open(KEYS, encoding="utf-8")).get(x["id"]) or {}).get("template") if KEYS.exists() else None
            json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # elevenlabs-script.md
    f = R / "Thơ" / "elevenlabs-script.md"
    if f.exists():
        out = []
        for line in f.read_text(encoding="utf-8").split("\n"):
            m = re.match(r"^## (\w+)\. (.*?)(  ✅ ĐÃ LỒNG TIẾNG.*)?$", line)
            if m:
                st = state.get(m.group(1))
                line = f"## {m.group(1)}. {m.group(2)}" + (f"  ✅ ĐÃ LỒNG TIẾNG ({st['date']})" if st else "")
            out.append(line)
        f.write_text("\n".join(out), encoding="utf-8")
    # CSV
    f = R / "GHEP_THO_VIDEO.csv"
    if f.exists():
        rows = list(csv.reader(open(f, encoding="utf-8-sig")))
        if "Đã lồng tiếng" in rows[0]:
            k = rows[0].index("Đã lồng tiếng")
        else:
            rows[0].append("Đã lồng tiếng"); k = len(rows[0]) - 1
        if "Template" in rows[0]:
            kt = rows[0].index("Template")
        else:
            rows[0].append("Template"); kt = len(rows[0]) - 1
        for r in rows[1:]:
            while len(r) <= max(k, kt):
                r.append("")
            r[k] = label(state.get(r[0]))
            r[kt] = tpl_label(r[0])
        csv.writer(open(f, "w", encoding="utf-8-sig", newline="")).writerows(rows)
    # HTML
    f = R / "GHEP_THO_VIDEO.html"
    t = f.read_text(encoding="utf-8")
    j = t.find("const D=") + 8
    D, end = json.JSONDecoder().raw_decode(t[j:])
    for p in D["poems"] + D["combos"]:
        p["done"] = state.get(p["id"])
        p["tpl"] = tpl_label(p["id"])
    rest = t[j + end:]
    if BADGE not in rest:
        old = '<span class="id">${p.id}</span>'
        assert old in rest, "không thấy chỗ chèn nhãn"
        rest = rest.replace(old, old + BADGE, 1)
    if TPL_BADGE not in rest:
        rest = rest.replace(BADGE, BADGE + TPL_BADGE, 1)
    head, rest = ensure_ui(t[:j], rest)
    f.write_text(head + json.dumps(D, ensure_ascii=False) + rest, encoding="utf-8")
    print(f"Đã đánh dấu {len(state)} bài lồng tiếng.")


if __name__ == "__main__":
    main()
