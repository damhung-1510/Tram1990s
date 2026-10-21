#!/usr/bin/env python3
"""Máy chủ cục bộ cho GHEP_THO_VIDEO.html: chọn thơ + giọng đọc + clip + nhạc nền rồi bấm "Tạo video".

    python3 tao_video.py            # mở http://127.0.0.1:8787/
    python3 tao_video.py --port 9000

Mỗi video: dựng template "Hoài Cổ - Mở Mờ" (tao-template-hoai-co.py) với dòng thơ chạy theo giọng đọc,
tên tác giả, clip đã chọn, giọng đọc + nhạc nền, rồi xuất bằng concat-cli vào Vid_completed/.
"""
import argparse, importlib.util, json, math, mimetypes, os, re, shutil, subprocess, sys, tempfile, textwrap
import threading, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import hashlib
import urllib.request
import urllib.error
import traceback
import queue

ROOT = Path(__file__).resolve().parent
_LOCAL_PYTHON = ROOT / ".tools/python"
if _LOCAL_PYTHON.is_dir():
    sys.path.insert(0, str(_LOCAL_PYTHON))
    os.environ["PYTHONPATH"] = str(_LOCAL_PYTHON) + os.pathsep + os.environ.get("PYTHONPATH", "")
_LOCAL_BIN = ROOT / ".tools/ffmpeg/bin"
if _LOCAL_BIN.is_dir():
    os.environ["PATH"] = str(_LOCAL_BIN) + os.pathsep + os.environ.get("PATH", "")
OUT = ROOT / "Vid_completed"
WORK = ROOT / ".tao-video-tmp"
def find_cli():
    """concat-cli: biến môi trường CONCAT_CLI, rồi PATH, rồi các chỗ build mặc định."""
    cands = [os.environ.get("CONCAT_CLI"), shutil.which("concat-cli"),
             str(ROOT / ".tools/Concat/src/target/quick/concat-cli"),
             "/Volumes/Volume/movie_creator/ConCat/concat/src/target/quick/concat-cli",
             "/Volumes/Volume/movie_creator/ConCat/concat/src/target/debug/concat-cli"]
    return next((p for p in cands if p and os.path.isfile(p) and os.access(p, os.X_OK)), None)


CLI = find_cli()
_APP_TEMPLATES = Path.home() / "Library" / "Application Support" / "app.concat.editor" / "templates"
TEMPLATES = ROOT / "templates" if (ROOT / "templates").is_dir() else _APP_TEMPLATES   # template đi kèm dự án
USE_EDITED = False        # templates của bạn đã có màu/mờ, nên dùng clip gốc; đặt True để ưu tiên clip *_edited

MUSIC_BELOW_VOICE_DB = float(os.environ.get("MUSIC_BELOW_DB", 15))   # nhạc nền nhỏ hơn giọng đọc bao nhiêu dB
LEAD, TAIL = 0.5, 3.0     # giọng đọc bắt đầu sau 0.5s; template thường kết thúc 3s sau giọng đọc
REELS_TAIL = 4.0           # Reels dành 4s cho phần kết tên bài + tác giả
_dur_cache = {}
_music_cache_lock = threading.Lock()
_music_cache_sig = None
_music_cache_data = None


def edited(path):
    """Clip đã xuất theo template của bạn (đuôi _edited) nếu có; không có thì dùng clip gốc."""
    p = Path(path)
    e = p.with_name(p.stem + "_edited" + p.suffix)
    return (e, True) if e.exists() else (p, False)


def duration(path):
    path = str(path)
    if path not in _dur_cache:
        o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                           capture_output=True, text=True).stdout.strip()
        _dur_cache[path] = float(o) if o else 0.0
    return _dur_cache[path]


_lufs_cache = {}


def lufs(path):
    """Độ lớn tích hợp (LUFS) của một file âm thanh, đo một lần rồi nhớ lại."""
    path = str(path)
    if path not in _lufs_cache:
        o = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", o)
        _lufs_cache[path] = float(m[-1]) if m else -23.0
    return _lufs_cache[path]


def music_gain(voice, music, user=1.0):
    """Hệ số âm lượng (tuyến tính) để nhạc nền thấp hơn giọng đọc MUSIC_BELOW_VOICE_DB; user = thanh chỉnh trong giao diện."""
    db = (lufs(voice) - MUSIC_BELOW_VOICE_DB) - lufs(music)
    return round(min(10 ** (db / 20), 1.5) * max(0.0, min(float(user), 1.0)), 4), round(db, 1)


def slug(s):
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:40] or "video"


def syllables(s):
    return max(1, len(re.findall(r"\w+", s)))


# ───────────────────────── dữ liệu cho giao diện ─────────────────────────

def load_poems():
    return {p["id"]: p for p in json.loads((ROOT / "Thơ" / "bai-chinh-thuc.json").read_text(encoding="utf-8"))}


def list_audio():
    """{poem_id: [{file, label, hook, dur}]} — giọng đọc đã có."""
    out = {}
    for f in sorted((ROOT / "Long-tieng").glob("*.mp3")):
        m = re.match(r"([A-Z]\d+)_.*?_([A-Za-z\-]+)\.mp3$", f.name)
        if m:
            out.setdefault(m.group(1), []).append(dict(file=str(f.relative_to(ROOT)), label=m.group(2).replace("-", " ") + " (chỉ thơ)",
                                                       hook=False, dur=round(duration(f), 1)))
    for f in sorted((ROOT / "Long-tieng" / "elevenlabs").glob("*.mp3")):
        m = re.match(r"([A-Z]\d+)_", f.name)
        if m:
            out.setdefault(m.group(1), []).append(dict(file=str(f.relative_to(ROOT)), label="ElevenLabs (mở đầu + thơ)",
                                                       hook=True, dur=round(duration(f), 1)))
    return out


def list_clips():
    """Video và ảnh nền có thể chọn trong cửa sổ media."""
    out = {}
    for f in sorted((ROOT / "Videos").rglob("*.mp4")):
        if "Ban_goc" in f.parts or f.stem.endswith("_edited") or f.name.startswith("."):
            continue
        out.setdefault("Video / " + str(f.parent.relative_to(ROOT / "Videos")), []).append(
            dict(file=str(f.relative_to(ROOT)), name=f.stem.replace("TramCamXuc_", ""), kind="video"))
    image_root = ROOT / "Ảnh nền"
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        for f in sorted(image_root.rglob(ext)):
            if f.name.startswith("."):
                continue
            folder = str(f.parent.relative_to(image_root))
            out.setdefault("Ảnh nền" + (" / " + folder if folder != "." else ""), []).append(
                dict(file=str(f.relative_to(ROOT)), name=f.stem, kind="image"))
    return out


THUMBS = ROOT / ".thumbs"


def thumb(rel):
    """Ảnh xem trước (JPEG, tạo một lần rồi lưu cache) hoặc None."""
    f = (ROOT / rel).resolve()
    allowed = (ROOT / "Videos") in f.parents or (ROOT / "Ảnh nền") in f.parents
    if not allowed or not f.is_file():
        return None
    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        return f
    THUMBS.mkdir(exist_ok=True)
    out = THUMBS / (hashlib.md5(str(f).encode()).hexdigest() + ".jpg")
    if not out.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", str(f), "-frames:v", "1",
                        "-vf", "scale=180:-2", "-q:v", "5", str(out)], capture_output=True)
        if not out.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f), "-frames:v", "1", "-vf", "scale=180:-2",
                            "-q:v", "5", str(out)], capture_output=True)
    return out if out.exists() else None


def list_music():
    global _music_cache_sig, _music_cache_data
    music_root = ROOT / "Nhạc nền"
    files = []
    for f in sorted(music_root.rglob("*.mp3")):
        rel_parts = f.relative_to(music_root).parts
        if any(part.startswith("_") for part in rel_parts[:-1]):
            continue
        files.append(f)
    sig = tuple((str(f), f.stat().st_mtime_ns, f.stat().st_size) for f in files)
    with _music_cache_lock:
        if sig == _music_cache_sig and _music_cache_data is not None:
            return _music_cache_data
        with ThreadPoolExecutor(max_workers=min(8, max(1, len(files)))) as pool:
            durations = list(pool.map(duration, files))
        out = []
        for f, dur in zip(files, durations):
            rel_parts = f.relative_to(music_root).parts
            folder = " / ".join(rel_parts[:-1])
            out.append(dict(file=str(f.relative_to(ROOT)), name=f.stem, folder=folder, dur=round(dur, 1)))
        _music_cache_sig, _music_cache_data = sig, out
        return out


# ───────────────────────── nhãn và thời gian ─────────────────────────

def author_label(p):
    a = (p.get("author") or "").strip()
    low = a.lower()
    kind = (p.get("kind") or "")
    if low.startswith("tự biên"):
        return "Tự biên"
    if not a or ("không rõ" in low and "dân gian" not in low):
        return "Không rõ"
    if "dân gian" in low or low.startswith("ca dao"):
        return "Trích dẫn dân gian" if kind in ("Tục ngữ", "Trích dẫn") or "tục ngữ" in low else "Thơ dân gian"
    return re.split(r"[(,;]", a)[0].strip() or "Không rõ"


def silences(path):
    o = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "silencedetect=noise=-38dB:d=0.3", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", o)]
    ends = [(float(a), float(b)) for a, b in re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", o)]
    segs = []
    for i, s in enumerate(starts):
        if i < len(ends):
            segs.append((s, ends[i][0]))
        else:
            segs.append((s, None))
    return segs


def timing(voice_path, has_hook, dur):
    """(poem_start, poem_end) tính bằng giây trong file giọng đọc."""
    segs = silences(voice_path)
    speech_start = segs[0][1] if segs and segs[0][0] < 0.15 and segs[0][1] else 0.0
    speech_end = dur
    if segs and segs[-1][1] is None:
        speech_end = segs[-1][0]
    poem_start = speech_start
    if has_hook:
        cands = [(e - s, e) for s, e in segs if e and s > 2.0 and e < 0.6 * dur]
        if cands:
            length, end = max(cands)
            if length >= 0.7:
                poem_start = end
    return poem_start, max(speech_end, poem_start + 1.0)


def plan_slots(vdurs, total):
    """Chia thời lượng cho từng clip; clip ngắn thì chạy chậm (tối đa 0.5x), thiếu thì lặp lại danh sách clip."""
    n = len(vdurs)
    lens = [total / n] * n
    caps = [d / 0.5 for d in vdurs]
    for _ in range(6):
        lens = [min(l, c) for l, c in zip(lens, caps)]
        left = total - sum(lens)
        room = [i for i in range(n) if lens[i] < caps[i] - 1e-6]
        if left < 0.05 or not room:
            break
        add = left / len(room)
        for i in room:
            lens[i] += add
    slots = list(zip(range(n), lens))
    left = total - sum(lens)
    k = 0
    while left > 0.05 and k < 12:
        i = k % n
        l = min(caps[i], left)
        slots.append((i, l)); left -= l; k += 1
    if left > 0.05 and slots:           # còn dư rất ít: kéo dài clip cuối
        i, l = slots[-1]; slots[-1] = (i, l + left)
    return [(i, l, min(1.0, vdurs[i] / l)) for i, l in slots]


# ───────────────────────── Concat API ─────────────────────────

class Api:
    def __init__(self):
        self._stderr = tempfile.TemporaryFile()
        try:
            self.p = subprocess.Popen([CLI, "api"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                                      text=True, bufsize=1)
        except Exception:
            self._stderr.close()
            raise
        self.n = 0
        self._lines = queue.Queue()
        self._events = []
        threading.Thread(target=self._read_output, daemon=True).start()

    def _read_output(self):
        try:
            for line in self.p.stdout:
                self._lines.put(line)
        finally:
            self._lines.put(None)

    def stderr_text(self):
        size = os.fstat(self._stderr.fileno()).st_size
        return os.pread(self._stderr.fileno(), min(size, 4000), max(0, size - 4000)).decode(errors="replace").strip()

    def _receive(self, timeout):
        try:
            line = self._lines.get(timeout=max(0, timeout))
        except queue.Empty:
            raise TimeoutError("Concat không phản hồi trong thời gian cho phép") from None
        if line is None:
            raise RuntimeError("concat-cli dừng đột ngột: " + (self.stderr_text() or f"exit={self.p.poll()}"))
        return json.loads(line)

    def send(self, method, params):
        self.n += 1
        self.p.stdin.write(json.dumps(dict(jsonrpc="2.0", id=self.n, method=method, params=params)) + "\n")
        self.p.stdin.flush()
        return self.n

    def call(self, method, params, on_event=None, timeout=180):
        i = self.send(method, params)
        deadline = time.monotonic() + timeout
        while True:
            m = self._receive(deadline - time.monotonic())
            if m.get("id") == i:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error'].get('message')}")
                return m["result"]
            if m.get("method") in ("export.done", "export.failed"):
                self._events.append(m)
            if on_event:
                on_event(m)

    def wait_event(self, names, on_event=None, timeout=3600):
        for i, event in enumerate(self._events):
            if event.get("method") in names:
                return self._events.pop(i)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            m = self._receive(deadline - time.monotonic())
            if on_event:
                on_event(m)
            if m.get("method") in names:
                return m
        raise TimeoutError("quá thời gian chờ xuất video")

    def close(self):
        try:
            self.p.stdin.close()
            self.p.terminate()
            self.p.wait(timeout=5)
        except Exception:
            try:
                self.p.kill()
            except Exception:
                pass
        finally:
            self._stderr.close()


# ───────────────────────── chọn template theo nội dung ─────────────────────────

def poem_lines(p):
    """Các dòng để hiện chữ: mỗi dòng thơ một dòng."""
    return [x.strip() for x in p["text"].split("\n") if x.strip()]


def reels_hook_text(hook):
    """Chia câu mở đầu thành tối đa bốn dòng ngắn, dễ đọc trên điện thoại."""
    return "\n".join(textwrap.wrap(hook.strip(), width=31, break_long_words=False,
                                    break_on_hyphens=False)[:4])


def reels_with_hook(pages, hook):
    """Lời mở kết thúc đúng lúc dòng thơ đầu xuất hiện, không chèn khung trống."""
    hook_start = 0.35
    if not pages or pages[0][1] <= hook_start:
        return pages
    return [(reels_hook_text(hook), hook_start, pages[0][1] - hook_start), *pages]


def reels_chunk_sizes(n):
    """Chia thơ thành các khổ 4–5 câu, cân đối nhất có thể."""
    if n <= 0:
        return []
    groups = max(1, round(n / 4.5))
    while groups > 1 and n / groups < 4:
        groups -= 1
    base, extra = divmod(n, groups)
    return [base + (1 if i < extra else 0) for i in range(groups)]


def reels_reveal_pages(lines, starts, finish):
    """Mỗi câu là một lớp giữ nguyên đến hết khổ, không thay cả khối chữ."""
    pages = []
    cursor = 0
    for count in reels_chunk_sizes(len(lines)):
        end = cursor + count
        stanza_end = starts[end] if end < len(lines) else finish
        for row in range(cursor, end):
            pages.append((lines[row], starts[row], stanza_end - starts[row]))
        cursor = end
    return pages


TEMPLATE_KEYS = ROOT / "Thơ" / "template-bai.json"      # khóa template gắn vào từng bài (sửa tay được)
LABELS = {"tho-hoai-co": "Thơ Hoài Cổ", "trich-dan-khong-chu": "Trích Dẫn Không Chữ",
          "trich-dan": "Trích dẫn",
          "tho-reels-doc-nhanh": "Thơ Reels · Đọc Nhanh",
          "tho-reels-anh-mo": "Thơ Reels · Ảnh Mờ",
          "tho-hoai-co-chay-chu-2-trang": "Thơ Hoài Cổ Chạy Chữ 2 Trang",
          "tho-hoai-co-chay-chu-nhieu-trang": "Thơ Hoài Cổ Chạy Chữ Nhiều Trang",
          "anh-tho-giay-hoai-co": "Ảnh Thơ Giấy Hoài Cổ · PNG 4K"}
IMAGE_TEMPLATE = "anh-tho-giay-hoai-co"
STILL_BG_TEMPLATE = "tho-reels-anh-mo"


def auto_template(p):
    """Gợi ý theo nội dung: (khóa, số dòng mỗi trang, ghi chú)."""
    n = len(poem_lines(p))
    if (p.get("kind") or "") == "Trích dẫn":
        return "trich-dan", 1, "trích dẫn: hình ảnh trong, chỉ làm mờ khi mở bài"
    if n <= 7:
        return "tho-hoai-co", max(n, 1), f"{n} dòng, chữ tĩnh 1 trang"
    if n == 8:
        return "tho-hoai-co-chay-chu-2-trang", 4, "8 dòng, 2 trang × 4 dòng"
    return "tho-hoai-co-chay-chu-nhieu-trang", 6, f"{n} dòng, mỗi trang 6 dòng"


def load_keys():
    return json.load(open(TEMPLATE_KEYS, encoding="utf-8")) if TEMPLATE_KEYS.exists() else {}


def choose_template(p):
    """Đọc khóa template đã gắn cho bài; chưa có hoặc khóa sai thì tự gợi ý. Trả về (khóa, tên, dòng/trang, ghi chú)."""
    k = load_keys().get(p["id"])
    if k and k.get("template") in LABELS:
        return k["template"], LABELS[k["template"]], int(k.get("per_page") or 1), k.get("ghi_chu") or "khóa đã gắn"
    slug_, per_page, why = auto_template(p)
    return slug_, LABELS[slug_], per_page, why + " (tự gợi ý, bài chưa có khóa)"


def template_per_page(name, p):
    """Số dòng mỗi trang phù hợp khi người dùng đổi template thủ công."""
    n = len(poem_lines(p))
    if name == "tho-hoai-co":
        return max(n, 1)
    if name == "tho-hoai-co-chay-chu-2-trang":
        return max(1, math.ceil(n / 2))
    if name == "tho-hoai-co-chay-chu-nhieu-trang":
        return 6
    if name in ("tho-reels-doc-nhanh", STILL_BG_TEMPLATE):
        return 4
    return 1


def resolve_template(p, requested_template=None):
    """Lấy template gợi ý theo phân loại, nhưng luôn ưu tiên lựa chọn của người dùng."""
    suggested_name, suggested_label, suggested_per_page, why = choose_template(p)
    if not requested_template:
        return suggested_name, suggested_label, suggested_per_page, why
    if requested_template not in LABELS:
        raise ValueError("Template không hợp lệ")
    return (requested_template, LABELS[requested_template],
            template_per_page(requested_template, p),
            f"do bạn chọn (gợi ý ban đầu: {suggested_label})")


# ───────────────────────── dựng project từ template của bạn ─────────────────────────

import copy

CLIP_DEFAULTS = dict(sourceStart=0.0, volume=1.0, fadeIn=0.0, fadeOut=0.0, scale=1.0, offsetX=0.0, offsetY=0.0,
                     rotation=0.0, opacity=1.0, speed=1.0, preservePitch=True, filters=[], videoEffects=[])


def layout_hoai_co(doc, clips):
    """Fit original verse lines, then reserve real space above and below them.

    Use one size/position for all pages so labels do not jump between stanzas.
    Font sizes and Y positions are fractions of frame height, widths of width.
    """
    from PIL import ImageFont

    poems = [c for c in clips if c.get("trackId") == "T2" and c.get("kind") == "text"]
    if not poems:
        return
    width, height = doc["video"]["width"], doc["video"]["height"]
    fonts = Path("/System/Library/Fonts/Supplemental")

    def metrics(c):
        style = c["text"]
        variant = (" Bold" if style.get("fontWeight", 400) >= 600 else "")
        variant += " Italic" if style.get("italic") else ""
        font = ImageFont.truetype(str(fonts / f"Georgia{variant}.ttf"), 1000)
        lines = style["content"].splitlines() or [""]
        # Match Concat: (rows - 1) * pitch + ascent + descent.
        unit_height = ((len(lines) - 1) * style.get("lineHeight", 1.2)
                       + sum(font.getmetrics()) / 1000)
        unit_width = max(font.getlength(line) / 1000 for line in lines)
        return unit_width, unit_height

    # Leave room for the brand/rule above and two footer labels below.
    top = max([0.22] + [0.5 + c.get("offsetY", 0) + 0.035
                       for c in clips if c.get("trackId") == "T1"
                       or c.get("name") == "page rule"])
    size = min(c["text"]["fontSize"] for c in poems)
    measurements = [metrics(c) for c in poems]
    for c, (unit_w, unit_h) in zip(poems, measurements):
        scale = c.get("scale", 1.0)
        # A little extra horizontal room protects italic overhangs/rounding.
        size = min(size, 0.92 * width / height * 0.96 / max(unit_w * scale, 0.001),
                   (0.82 - top) / (unit_h * scale))
    if size < 0.005:
        raise ValueError("Bài thơ quá dài cho một trang; hãy chọn template chia nhiều trang.")
    block_height = max(unit_h * size * c.get("scale", 1.0)
                       for c, (_, unit_h) in zip(poems, measurements))
    center = max(0.45, top + block_height / 2)
    for c in poems:
        c["text"].update(maxWidth=0.92, fontSize=size)
        c["offsetY"] = center - 0.5

    bottom = center + block_height / 2
    for track, gap in (("T3", 0.025), ("T3.2", 0.012)):
        labels = [c for c in clips if c.get("trackId") == track and c.get("kind") == "text"]
        for c in labels:
            _, unit_h = metrics(c)
            half = unit_h * c["text"]["fontSize"] * c.get("scale", 1.0) / 2
            y = max(0.5 + c.get("offsetY", 0), bottom + gap + half)
            c["offsetY"] = y - 0.5
            bottom = y + half


def layout_reels_doc_nhanh(doc, clips, total, page_items):
    """Giữ từng dòng thơ trên một dòng và dành đoạn kết riêng cho tên bài."""
    from PIL import ImageFont

    poems = [c for c in clips if c.get("trackId") == "T2" and c.get("kind") == "text"]
    if not poems:
        return
    width, height = doc["video"]["width"], doc["video"]["height"]
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", 1000)
    hook_pages = [c for c in poems if float(c.get("start", 1.0)) < 0.5]
    verse_pages = [c for c in poems if c not in hook_pages]
    line_units = [[font.getlength(line) / 1000 for line in c["text"]["content"].splitlines()]
                  for c in verse_pages]
    max_units = max((units for page in line_units for units in page), default=1.0)
    # Concat renders onto a full-frame canvas. For a left-aligned 84%-wide
    # box, its raster starts at 16%; shift by -8% to leave an 8% gutter.
    box_width, gutter = 0.84, 0.08
    offset_x = gutter - min(0.5, 1.0 - box_width)
    size = min(0.025, box_width * width / height * 0.97 / max(max_units, 0.001))

    def wrap_to_width(text, max_px):
        """Bẻ các câu quá dài theo pixel để Concat không cắt ở mép phải."""
        result = []
        for raw in text.splitlines():
            words = raw.split()
            if not words:
                result.append("")
                continue
            line = words[0]
            for word in words[1:]:
                candidate = f"{line} {word}"
                if font.getlength(candidate) / 1000 * size * height <= max_px:
                    line = candidate
                else:
                    result.append(line)
                    line = word
            result.append(line)
        return "\n".join(result)

    # Preserve the opening's current position, then anchor the first line of
    # every verse to its first line rather than centring each block separately.
    pitch = size * 1.38
    hook_rows = max((len(wrap_to_width(c["text"]["content"], box_width * width).splitlines())
                     for c in hook_pages), default=1)
    first_line_y = -0.06 - (hook_rows - 1) * pitch / 2
    positions = [row for count in reels_chunk_sizes(len(verse_pages)) for row in range(count)]
    for c, row in zip(verse_pages, positions):
        c["text"]["content"] = wrap_to_width(c["text"]["content"], box_width * width)
        c["text"].update(fontSize=size, maxWidth=box_width, align="left", italic=False,
                         lineHeight=1.38)
        # Separate lanes retain the exact same raster and position while the
        # following lines appear; no cumulative redraw or opacity animation.
        c.update(trackId=f"T2.line.{row}", offsetX=offset_x,
                 offsetY=first_line_y + row * pitch, scale=1.0,
                 keys=[], fadeIn=0.0, fadeOut=0.0, opacity=1.0)

    for c in hook_pages:
        # Mở đầu dùng cùng cỡ chữ với phần thơ và khổ rộng hơn trước.
        c["text"]["content"] = wrap_to_width(c["text"]["content"], box_width * width)
        c["text"].update(fontSize=size, maxWidth=box_width, align="left", italic=False,
                         lineHeight=1.38)
        rows = len(c["text"]["content"].splitlines())
        c.update(offsetX=offset_x, offsetY=first_line_y + (rows - 1) * pitch / 2, scale=1.0)

    # Tên bài và tác giả cũng dùng đúng cỡ chữ của phần thơ.
    for c in clips:
        if c.get("trackId") in ("T3", "T3.2") and c.get("kind") == "text":
            c["text"]["content"] = wrap_to_width(c["text"]["content"], box_width * width)
            c["text"].update(fontSize=size, maxWidth=box_width, align="center")
            c["offsetX"] = 0.0

    page_end = max((start + dur for _, start, dur in page_items), default=total - 2.7)
    outro_start = min(max(page_end + 0.12, total - REELS_TAIL), total - 1.1)
    # The ending card is the final four-second block; the fade overlay still
    # softens its last second without shortening the author display.
    outro_end = max(outro_start + 0.8, total)
    for c in clips:
        if c.get("trackId") == "T3":
            c.update(start=round(outro_start, 3), duration=round(outro_end - outro_start, 3),
                     offsetY=-0.015)
        elif c.get("trackId") == "T3.2":
            author_start = outro_start
            c.update(start=round(author_start, 3), duration=round(outro_end - author_start, 3),
                     offsetY=0.04)


def build_from_template(tdir, total, slots, pages, title, author, audio):
    """slots: [(duration, speed)]; pages: [(text, start, duration)]; audio: [dict(path,name,duration,lane,start,dur,volume,fade_in,fade_out)]."""
    doc = json.loads((Path(tdir) / "template.json").read_text(encoding="utf-8"))
    clips = doc["clips"]
    old_total = max(c["start"] + c["duration"] for c in clips)
    delta = total - old_total
    n = [0]
    def nid():
        n[0] += 1; return f"x{n[0]}"
    protos = {c["id"]: c for c in clips}
    visual_kinds = ("video", "image")
    bg0 = next(c for c in clips if c["trackId"] == "BG" and c["kind"] in visual_kinds)
    fg0 = next(c for c in clips if c["trackId"] == "FG" and c["kind"] in visual_kinds)
    page0 = next((c for c in clips if c["trackId"] == "T2" and c["kind"] == "text"), None)
    media0 = doc["media"][0]
    extra_media = list(doc["media"][1:])        # ô media khác ngoài clip video
    extra_fills = {}
    keep = []
    for c in clips:
        if c["trackId"] in ("BG", "FG") and c["kind"] in visual_kinds or (c["trackId"] == "T2" and c["kind"] == "text"):
            continue
        if c["name"] == "fade out":
            c["start"] = round(total - c["duration"], 3)
        elif c["start"] + c["duration"] >= old_total - 1.01:
            c["duration"] = round(max(c["duration"] + delta, 0.5), 3)
        if c["kind"] == "text" and c["name"].startswith("“"):
            c["name"] = c["text"]["content"] = f"“{title}”"
        if c["kind"] == "text" and c["trackId"] == "T3.2":
            c["name"] = c["text"]["content"] = author.upper()
        keep.append(c)
    doc["media"] = []
    t = 0.0
    for i, (seg, speed) in enumerate(slots):
        m = copy.deepcopy(media0); m.update(id=f"m{i+1}", name=f"Clip {i+1}", duration=round(seg, 3)); doc["media"].append(m)
        for proto in (bg0, fg0):
            c = copy.deepcopy(proto)
            c.update(id=nid(), mediaId=f"m{i+1}", start=round(t, 3), duration=round(seg, 3), speed=round(speed, 4))
            c["name"] = f"{proto['name'].split(' backdrop')[0].split(' nền')[0]} {i+1}" + (" backdrop" if proto is bg0 else "")
            if i > 0:
                c["transitionIn"] = dict(id="concat.dissolve", duration=0.8)
            keep.append(c)
        t += seg
    doc["media"].extend(extra_media)
    page_items = list(pages if page0 else [])
    # Chữ bài thơ phải nằm đúng trong cùng khung thời gian với tên page
    # (track T1: “TRẠM 1990s”) ở các template Thơ Hoài Cổ.
    if page_items and page0 and Path(tdir).name.startswith("tho-hoai-co"):
        page_name = next((c for c in keep if c.get("trackId") == "T1" and c.get("kind") == "text"), None)
        if page_name:
            window_start = float(page_name["start"])
            window_dur = max(float(page_name["duration"]), 1.0)
            weights = [max(float(dur), 1.0) for _, _, dur in page_items]
            scale = window_dur / sum(weights)
            t_page = window_start
            aligned = []
            for (txt, _, _), weight in zip(page_items, weights):
                dur = window_dur if len(page_items) == 1 else weight * scale
                aligned.append((txt, t_page, dur))
                t_page += dur
            page_items = aligned
    for txt, start, dur in page_items:
        c = copy.deepcopy(page0)
        is_reels = Path(tdir).name in ("tho-reels-doc-nhanh", STILL_BG_TEMPLATE)
        c.update(id=nid(), name=txt, start=round(start, 6),
                 duration=round(start + dur, 6) - round(start, 6) if is_reels else round(max(dur, 1.0), 3))
        if is_reels:
            # A new word must not fade the entire stanza out/in or overlap it.
            c.update(keys=[], fadeIn=0.0, fadeOut=0.0, opacity=1.0)
            c.pop("transitionIn", None)
            c.pop("transitionOut", None)
        c["text"]["content"] = txt
        keep.append(c)
    for k, a in enumerate(audio):
        mid = f"a{k+1}"
        doc["media"].append(dict(id=mid, path=a["path"], name=a["name"], duration=a["duration"], kind="audio",
                                 hasAudio=True, audioCodec="mp3"))
        c = dict(CLIP_DEFAULTS, filters=[], videoEffects=[], id=nid(), trackId=a["lane"], mediaId=mid, name=a["name"],
                 kind="audio", start=a["start"], duration=a["dur"])
        c.update(volume=a.get("volume", 1.0), fadeIn=a.get("fade_in", 0.0), fadeOut=a.get("fade_out", 0.0))
        keep.append(c)
    if Path(tdir).name.startswith("tho-hoai-co"):
        layout_hoai_co(doc, keep)
    elif Path(tdir).name in ("tho-reels-doc-nhanh", STILL_BG_TEMPLATE):
        layout_reels_doc_nhanh(doc, keep, total, page_items)
    doc["clips"] = keep
    lanes = {c["trackId"] for c in keep}
    have = {tr["id"] for tr in doc["tracks"]}
    for lane in sorted(lanes - have):
        index = (next(i for i, tr in enumerate(doc["tracks"]) if tr["id"] == "T2") + 1
                 if lane.startswith("T2.line.") else 0)
        doc["tracks"].insert(index, dict(id=lane, name=lane, visible=True, muted=False))
    return doc, extra_fills


# ───────────────────────── tạo video ─────────────────────────

JOBS = {}
RENDER_LOCK = threading.Lock()
DUB_JOBS = {}
DUB_LOCK = threading.Lock()
DUB_VOICES = {
    "qn4pQo7kIjvZ1a7SowZE": "Giọng thơ Nữ",
    "O4GJDPajhRb6MxWUMf7V": "Giọng trích dẫn Nam",
}


def dubbed_state():
    path = ROOT / "Thơ" / "da-long-tieng.json"
    return json.load(open(path, encoding="utf-8")) if path.exists() else {}


def validate_dub_request(poem_id, voice_id):
    if not isinstance(poem_id, str) or not isinstance(voice_id, str):
        return "Bài hoặc giọng đọc không hợp lệ", 400
    if poem_id not in load_poems():
        return "Không tìm thấy bài", 404
    if voice_id not in DUB_VOICES:
        return "Giọng đọc không hợp lệ", 400
    if not load_poems()[poem_id].get("tts"):
        return "Bài chưa có kịch bản lồng tiếng", 400
    if list_audio().get(poem_id):
        return "Bài này đã được lồng tiếng", 409
    if not tts_key():
        return "Chưa có API key ElevenLabs. Lưu key theo README.md.", 400
    return None


def tts_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    f = Path.home() / ".config/elevenlabs/key"
    return key or (f.read_text().strip() if f.is_file() else "")


def dub(jid, poem, voice_id):
    """Tạo một file giọng đọc; chỉ đánh dấu sau khi nhận đủ âm thanh."""
    tmp = None
    try:
        DUB_JOBS[jid].update(status="running", message="Đang tạo giọng đọc ElevenLabs…")
        key = tts_key()
        if not key:
            raise ValueError("Chưa có API key ElevenLabs. Lưu key theo README.md.")
        folder = ROOT / "Long-tieng/elevenlabs"
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / f"{poem['id']}_{slug(poem['title'])}.mp3"
        # Kiểm tra lại để không gọi API hai lần cho cùng một bài.
        if not list_audio().get(poem["id"]):
            req = urllib.request.Request(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
                data=json.dumps(dict(text=poem["tts"], model_id="eleven_v4", language_code="vi",
                                     voice_settings=dict(stability=0.5, similarity_boost=0.75))).encode(),
                headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
            with urllib.request.urlopen(req, timeout=120) as response:
                data = response.read()
            if not data:
                raise ValueError("ElevenLabs trả về âm thanh trống. Thử lại.")
            with tempfile.NamedTemporaryFile(dir=folder, suffix=".part", delete=False) as f:
                tmp = Path(f.name)
                f.write(data)
            if duration(tmp) <= 0:
                raise ValueError("File giọng đọc không hợp lệ. Thử lại.")
            tmp.replace(dest)
            state_file = ROOT / "Thơ/da-long-tieng.json"
            state = json.loads(state_file.read_text()) if state_file.is_file() else {}
            state[poem["id"]] = dict(voice_id=voice_id, model="eleven_v4", chars=len(poem["tts"]),
                                     file=str(dest.relative_to(ROOT)), date=time.strftime("%Y-%m-%d"))
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_tmp = state_file.with_suffix(".json.part")
            state_tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
            state_tmp.replace(state_file)
        DUB_JOBS[jid].update(status="done", pct=100, message="Đã lồng tiếng", audio=list_audio().get(poem["id"], []))
    except urllib.error.HTTPError as e:
        messages = {401: "API key thiếu quyền Text to Speech hoặc không hợp lệ.",
                    403: "Key chưa được phép dùng giọng hoặc model này.",
                    402: "Không đủ credit ElevenLabs.", 429: "ElevenLabs đang giới hạn yêu cầu. Thử lại sau."}
        try:
            detail = json.loads(e.read()).get("detail", {})
            quota = isinstance(detail, dict) and detail.get("status") == "quota_exceeded"
        except (ValueError, OSError):
            quota = False
        DUB_JOBS[jid].update(status="error", message=f"ElevenLabs HTTP {e.code}: " +
                         ("Đã hết hạn mức credit của key ElevenLabs." if quota else
                          messages.get(e.code, "Không tạo được giọng; kiểm tra giọng, model và hạn mức key.")))
    except Exception as e:
        # Không đưa chi tiết request hoặc key vào thông báo cho trình duyệt.
        message = str(e) if isinstance(e, ValueError) else "Không tạo được giọng đọc. Kiểm tra kết nối và thử lại."
        DUB_JOBS[jid].update(status="error", message=message)
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)
        DUB_LOCK.release()


def render(job_id, req):
    job = JOBS[job_id]
    def upd(**kw):
        job.update(kw)
    work = None
    api = None
    try:
        poems = load_poems()
        p = poems[req["poemId"]]
        tname, tlabel, per_page, why = resolve_template(p, req.get("template"))
        tdir = TEMPLATES / tname
        if not (tdir / "template.json").exists():
            raise FileNotFoundError(f"không thấy template '{tlabel}'")
        if tname == IMAGE_TEMPLATE:
            image_out = ROOT / "Anh_completed" / f"{p['id']}_{slug(p['title'])}_{time.strftime('%Y%m%d-%H%M%S')}.png"
            upd(status="running", pct=10, message=f"Đang ghép ảnh · {tlabel}")
            result = subprocess.run(
                [sys.executable, str(ROOT / "tao-anh-tho.py"), "--id", p["id"], "--output", str(image_out)],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
            if result.returncode or not image_out.exists():
                detail = "\n".join(x.strip() for x in (result.stdout, result.stderr) if x.strip())
                raise RuntimeError(detail[-600:] or "Không xuất được ảnh")
            upd(status="done", pct=100, message=f"Xong · {tlabel}",
                output=str(image_out.relative_to(ROOT)))
            return
        voice = ROOT / req["voice"]
        vids = [edited(ROOT / v)[0] if USE_EDITED else ROOT / v for v in req["videos"]]
        if tname == STILL_BG_TEMPLATE:
            image_root = (ROOT / "Ảnh nền").resolve()
            if len(vids) != 1 or image_root not in vids[0].resolve().parents \
                    or vids[0].suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                raise ValueError("Template Ảnh Mờ cần đúng một ảnh trong thư mục Ảnh nền")
        music = ROOT / req["music"] if req.get("music") else None
        for f in [voice, *vids] + ([music] if music else []):
            if not f.exists():
                raise FileNotFoundError(str(f.relative_to(ROOT)))
        upd(status="running", pct=1, message=f"Template: {tlabel} ({why})")
        has_hook = "/elevenlabs/" in str(voice) and bool(p.get("hook"))
        vdur = duration(voice)
        tail = REELS_TAIL if tname in ("tho-reels-doc-nhanh", STILL_BG_TEMPLATE) else TAIL
        total = round(LEAD + vdur + tail, 2)       # mọi thứ cắt theo thời lượng giọng đọc
        ps, pe = timing(voice, has_hook, vdur)
        ps, pe = ps + LEAD, pe + LEAD
        # thời điểm từng dòng theo giọng đọc (chia theo số âm tiết), rồi gom thành trang
        lines = poem_lines(p)
        w = [syllables(x) for x in lines]
        span = max(pe - ps + 0.1, 1.0)
        starts, c = [], 0
        for x in w:
            starts.append(max(0.0, ps - 0.1) + span * c / sum(w)); c += x
        pages = []
        if tname in ("tho-reels-doc-nhanh", STILL_BG_TEMPLATE):
            # Mỗi câu đã đọc vẫn nằm trên màn hình; câu mới xuất hiện bên dưới.
            # Khi đủ một khổ 4–5 câu, chuyển sang khổ mới và lặp lại cách hiển thị.
            pages = reels_reveal_pages(lines, starts, min(total - tail, pe + 0.1))
        else:
            for k in range(0, len(lines), per_page):
                chunk = lines[k:k + per_page]
                s0 = starts[k]
                e0 = starts[k + per_page] if k + per_page < len(lines) else min(total - 0.5, pe + 0.8)
                pages.append(("\n".join(chunk), round(s0, 2), round(e0 - s0, 2)))
        if tname in ("tho-reels-doc-nhanh", STILL_BG_TEMPLATE) and has_hook and p.get("hook"):
            pages = reels_with_hook(pages, p["hook"])
        # clip video
        if tname == STILL_BG_TEMPLATE:
            plan = [(0, total, 1.0)]
        else:
            vd = [duration(v) for v in vids]
            plan = plan_slots(vd, total)
        slots = [(l, sp) for _, l, sp in plan]
        audio = [dict(path=str(voice), name=voice.stem, duration=vdur, lane="A", start=LEAD, dur=round(vdur, 2),
                      volume=1.0, fade_in=0.05, fade_out=0.3)]
        if music:
            md = duration(music); t = 0.0; k = 0
            mvol, mdb = music_gain(voice, music, req.get("musicVolume", 1.0))
            while t < total - 0.1 and k < 6:
                seg = min(md, total - t)
                audio.append(dict(path=str(music), name=music.stem, duration=md, lane="A.2", start=round(t, 2),
                                  dur=round(seg, 2), volume=mvol,
                                  fade_in=1.5 if k == 0 else 0.0, fade_out=3.0 if t + seg >= total - 0.1 else 0.0))
                t += seg; k += 1
        doc, extra = build_from_template(tdir, float(total), slots, pages, p["title"], author_label(p), audio)
        WORK.mkdir(exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="job-", dir=WORK))
        (work / "tpl" / "assets").mkdir(parents=True)
        (work / "tpl" / "template.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        fills = [dict(mediaId=f"m{n+1}", file=str(vids[i])) for n, (i, _, _) in enumerate(plan)]
        fills += [dict(mediaId=k, file=v) for k, v in extra.items()]
        upd(pct=3, message="Dựng project trong Concat")
        api = Api()
        res = api.call("template.instantiate", dict(template=str(work / "tpl"), location=str(work / "proj"), name="v", fills=fills))
        proj = res.get("path") or str(work / "proj" / "v")
        tmp_out = str(work / "out.mp4")
        def on_event(m):
            if m.get("method") == "export.progress":
                pr = m["params"]; upd(pct=min(97, 5 + int(92 * pr["frame"] / max(pr["total"], 1))), message=f"Đang xuất video · {tlabel}")
        api.call("export.run", dict(path=proj, output=tmp_out, width=1080, height=1920, crf=26, preset="medium"), on_event)
        ev = api.wait_event(("export.done", "export.failed"), on_event)
        if ev["method"] == "export.failed":
            raise RuntimeError("Xuất video lỗi: " + json.dumps(ev["params"], ensure_ascii=False)[:300])
        OUT.mkdir(exist_ok=True)
        name = f"{p['id']}_{slug(p['title'])}_{time.strftime('%Y%m%d-%H%M%S')}.mp4"
        shutil.move(tmp_out, OUT / name)
        upd(status="done", pct=100, message=f"Xong · {tlabel}", output=f"Vid_completed/{name}")
    except Exception as e:
        message = f"{type(e).__name__}: {e}"
        print(f"LỖI xuất {job_id}: {message}", file=sys.stderr, flush=True)
        try:
            log_dir = ROOT / ".tao-video-logs"
            log_dir.mkdir(exist_ok=True)
            log = log_dir / f"{job_id}.log"
            detail = traceback.format_exc()
            if api:
                detail += "\nConcat stderr:\n" + api.stderr_text()
            log.write_text(detail, encoding="utf-8")
            message += f" · Log: {log.relative_to(ROOT)}"
        except OSError:
            pass
        upd(status="error", message=message)
    finally:
        if api:
            api.close()
        if work:
            shutil.rmtree(work, ignore_errors=True)
        RENDER_LOCK.release()


# ───────────────────────── HTTP ─────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = "TaoVideo/1.0"

    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        u = urlparse(self.path); path = unquote(u.path)
        if path == "/api/ping":
            return self.send_json(dict(ok=True, cli=bool(CLI)))
        if path == "/api/root":
            return self.send_json(dict(root=str(ROOT)))
        if path == "/api/audio":
            return self.send_json(list_audio())
        if path == "/api/dub/voices":
            return self.send_json(dict(voices=[dict(id=k, name=v) for k, v in DUB_VOICES.items()],
                                       configured=bool(tts_key()), poems=list(load_poems())))
        if path == "/api/template":
            pid = (u.query.split("poemId=")[-1] if "poemId=" in u.query else "")
            p = load_poems().get(unquote(pid))
            if not p:
                return self.send_json(dict(error="không có bài"), 404)
            tname, tlabel, per_page, why = choose_template(p)
            return self.send_json(dict(template=tname, label=tlabel, why=why,
                                       ok=(TEMPLATES / tname / "template.json").exists()))
        if path == "/api/templates":
            return self.send_json([
                dict(template=name, label=label, kind="image" if name == IMAGE_TEMPLATE else "video",
                     ok=(TEMPLATES / name / "template.json").exists())
                for name, label in LABELS.items()
            ])
        if path == "/api/mixinfo":
            q = parse_qs(u.query)
            v = ROOT / unquote(q.get("voice", [""])[0]); m = ROOT / unquote(q.get("music", [""])[0])
            ok_ = all(ROOT in x.resolve().parents and x.is_file() for x in (v, m))
            if not ok_:
                return self.send_json(dict(error="không có file"), 404)
            gain, db = music_gain(v, m, 1.0)
            return self.send_json(dict(gain=gain, db=db, below_db=MUSIC_BELOW_VOICE_DB,
                                       voice_lufs=lufs(v), music_lufs=lufs(m)))
        if path == "/api/clips":
            return self.send_json(list_clips())
        if path == "/api/thumb":
            t = thumb(unquote(parse_qs(u.query).get("path", [""])[0]))
            if not t:
                self.send_response(404); self.end_headers(); return
            b = t.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "max-age=86400")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b); return
        if path == "/api/music":
            return self.send_json(list_music())
        if path.startswith("/api/job/"):
            j = JOBS.get(path.split("/")[-1])
            return self.send_json(j or dict(status="error", message="không có job"), 200 if j else 404)
        if path.startswith("/api/dub/job/"):
            j = DUB_JOBS.get(path.split("/")[-1])
            return self.send_json(j or dict(status="error", message="không có tác vụ lồng tiếng"), 200 if j else 404)
        self.static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/render", "/api/dub"):
            return self.send_json(dict(error="not found"), 404)
        if path == "/api/dub":
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).netloc != self.headers.get("Host"):
                return self.send_json(dict(error="Yêu cầu phải gửi từ giao diện trên máy này"), 403)
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.send_json(dict(error="Yêu cầu JSON không hợp lệ"), 400)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if not 0 < n <= 10000:
                raise ValueError()
            req = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(req, dict):
                raise ValueError()
        except (ValueError, TypeError):
            return self.send_json(dict(error="Dữ liệu JSON không hợp lệ"), 400)
        if path == "/api/dub":
            poem_id, voice_id = req.get("poemId"), req.get("voiceId")
            invalid = validate_dub_request(poem_id, voice_id)
            if invalid:
                return self.send_json(dict(error=invalid[0]), invalid[1])
            if not DUB_LOCK.acquire(blocking=False):
                return self.send_json(dict(error="Đang lồng tiếng một bài khác, hãy chờ hoàn tất"), 409)
            jid = "dub-" + str(int(time.time() * 1000))
            DUB_JOBS[jid] = dict(status="queued", message="Chuẩn bị lồng tiếng", poemId=poem_id,
                                 voiceId=voice_id, voiceName=DUB_VOICES[voice_id])
            threading.Thread(target=dub, args=(jid, load_poems()[poem_id], voice_id), daemon=True).start()
            return self.send_json(dict(job=jid))
        template = req.get("template")
        if template not in LABELS:
            return self.send_json(dict(error="Template không hợp lệ"), 400)
        is_image = template == IMAGE_TEMPLATE
        required = ("poemId",) if is_image else ("poemId", "voice", "videos")
        miss = [k for k in required if not req.get(k)]
        if not is_image and not req.get("music"):
            miss.append("music")
        if miss:
            return self.send_json(dict(error="Thiếu: " + ", ".join(miss)), 400)
        if not is_image and not CLI:
            return self.send_json(dict(error="Không thấy concat-cli"), 500)
        if not RENDER_LOCK.acquire(blocking=False):
            return self.send_json(dict(error="Đang tạo một video hoặc ảnh khác, chờ xong rồi thử lại"), 409)
        jid = str(int(time.time() * 1000))
        JOBS[jid] = dict(status="queued", pct=0, message="Bắt đầu", output=None)
        threading.Thread(target=render, args=(jid, req), daemon=True).start()
        self.send_json(dict(job=jid))

    def static(self, path):
        rel = "GHEP_THO_VIDEO.html" if path in ("/", "") else path.lstrip("/")
        f = (ROOT / rel).resolve()
        if ROOT not in f.parents and f != ROOT or not f.is_file() or ".tao-video-tmp" in f.parts or ".thumbs" in f.parts:
            self.send_response(404); self.end_headers(); return
        size = f.stat().st_size
        ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        start, end, code = 0, size - 1, 200
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    if m.group(2): end = min(int(m.group(2)), size - 1)
                elif m.group(2):
                    start = max(0, size - int(m.group(2)))
                code = 206
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            with open(f, "rb") as fh:
                fh.seek(start); left = end - start + 1
                while left > 0:
                    b = fh.read(min(1 << 20, left))
                    if not b: break
                    self.wfile.write(b); left -= len(b)
        except (BrokenPipeError, ConnectionResetError):
            pass


def make_cli(a):
    """Tạo video không cần giao diện: python3 tao_video.py --make Q044 --videos a.mp4 b.mp4 --music nhac.mp3"""
    poems = load_poems()
    if a.make not in poems:
        sys.exit(f"Không có bài {a.make}")
    voice = a.voice
    if not voice:
        found = sorted((ROOT / "Long-tieng" / "elevenlabs").glob(f"{a.make}_*.mp3"))
        if not found:
            sys.exit(f"Bài {a.make} chưa có giọng đọc. Chạy elevenlabs-tts.py --ids {a.make} trước.")
        voice = str(found[0].relative_to(ROOT))
    rel = lambda x: str(Path(x).resolve().relative_to(ROOT)) if Path(x).is_absolute() else x
    req = dict(poemId=a.make, voice=rel(voice), videos=[rel(v) for v in a.videos], music=rel(a.music),
               template=a.template,
               musicVolume=a.music_volume)
    if not a.videos or not a.music:
        sys.exit("Cần --videos (một hoặc nhiều clip) và --music")
    if not CLI:
        sys.exit("Không thấy concat-cli (đặt biến CONCAT_CLI)")
    RENDER_LOCK.acquire()
    JOBS["cli"] = dict(status="queued", pct=0, message="", output=None)
    t = threading.Thread(target=render, args=("cli", req)); t.start()
    last = ""
    while t.is_alive():
        j = JOBS["cli"]; line = f"{j['pct']:3}%  {j['message']}"
        if line != last:
            print(line, flush=True); last = line
        time.sleep(1)
    j = JOBS["cli"]
    print(("XONG → " + str(ROOT / j["output"])) if j["status"] == "done" else "LỖI: " + j["message"])
    sys.exit(0 if j["status"] == "done" else 1)


def preload_thumbs():
    """Tạo sẵn ảnh xem trước của mọi clip ở nền để cửa sổ chọn clip mở lên là có ngay."""
    import concurrent.futures as cf
    files = [c["file"] for L in list_clips().values() for c in L]
    with cf.ThreadPoolExecutor(3) as ex:
        list(ex.map(thumb, files))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--make", metavar="ID_BAI", help="tạo video luôn, không mở giao diện")
    ap.add_argument("--voice", help="file giọng đọc (mặc định: bản ElevenLabs của bài)")
    ap.add_argument("--videos", nargs="*", default=[], help="một hoặc nhiều clip dọc")
    ap.add_argument("--music", help="file nhạc nền")
    ap.add_argument("--template", choices=LABELS, help="template dùng để tạo video")
    ap.add_argument("--music-volume", type=float, default=1.0)
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if a.make:
        make_cli(a)
    if not CLI:
        print("CẢNH BÁO: không thấy concat-cli, không tạo video được.")
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    except OSError as e:
        sys.exit(f"Cổng {a.port} đang được dùng ({e.strerror}). Máy chủ có thể đã chạy sẵn: mở http://127.0.0.1:{a.port}/ "
                 f"luôn, hoặc tắt nó bằng:  pkill -f tao_video.py  rồi chạy lại, hoặc dùng cổng khác: python3 tao_video.py --port 8788")
    threading.Thread(target=preload_thumbs, daemon=True).start()
    print(f"Mở http://127.0.0.1:{a.port}/  (Ctrl+C để dừng). Video lưu ở {OUT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
