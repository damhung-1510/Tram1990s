#!/usr/bin/env python3
"""Kiểm tra máy đã đủ điều kiện tạo video chưa:  python3 kiem-tra-moi-truong.py"""
import json, os, platform, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import tao_video as T  # cũng nhận PATH của bản FFmpeg cài riêng trong dự án
bad = 0


def ok(msg): print("  ✅", msg)
def warn(msg): print("  ⚠️ ", msg)
def fail(msg):
    global bad; bad += 1; print("  ❌", msg)


print("Kiểm tra môi trường Tram1990s")
v = sys.version_info
(ok if v >= (3, 9) else fail)(f"Python {v.major}.{v.minor}.{v.micro}" + ("" if v >= (3, 9) else " (cần 3.9 trở lên)"))
for tool in ("ffmpeg", "ffprobe"):
    (ok(f"{tool}: {shutil.which(tool)}") if shutil.which(tool) else fail(f"thiếu {tool}  →  brew install ffmpeg"))
try:
    import PIL
    ok(f"Pillow {PIL.__version__}")
except ImportError:
    fail("Thiếu Pillow → python3 -m pip install --target .tools/python Pillow")

if T.CLI:
    try:
        binary = subprocess.run(["file", T.CLI], capture_output=True, text=True, timeout=20).stdout.strip()
        arch = platform.machine()
        if arch not in binary and "universal binary" not in binary:
            fail(f"concat-cli sai kiến trúc: máy là {arch}, nhưng file là {binary}")
        ver = subprocess.run([T.CLI, "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
        ok(f"concat-cli: {T.CLI} ({ver})")
    except Exception as e:
        fail(f"concat-cli không chạy được: {e}")
else:
    fail("không thấy concat-cli. Build Concat (xem README.md, bước 1) hoặc đặt biến CONCAT_CLI=/đường/dẫn/concat-cli")

if sys.platform == "darwin":
    try:
        gpu = subprocess.run(["system_profiler", "SPDisplaysDataType"], capture_output=True, text=True, timeout=30).stdout
        (ok("GPU hỗ trợ Metal") if "Metal: Supported" in gpu else fail("GPU không báo Metal: Supported; Concat có thể không xuất được video"))
    except Exception as e:
        warn(f"không kiểm tra được Metal: {e}")

need = list(T.LABELS)
miss = [t for t in need if not (T.TEMPLATES / t / "template.json").exists()]
(ok(f"{len(need)} template trong {T.TEMPLATES}") if not miss else fail(f"thiếu template: {', '.join(miss)} (thư mục {T.TEMPLATES})"))
for f in ("Thơ/bai-chinh-thuc.json", "Thơ/template-bai.json", "GHEP_THO_VIDEO.html", "tao-video.js"):
    (ok(f) if (ROOT / f).exists() else fail(f"thiếu file {f}"))

clips = [p for p in (ROOT / "Videos").rglob("*.mp4") if "Ban_goc" not in p.parts]
(ok(f"{len(clips)} clip trong Videos/") if clips else fail("Videos/ chưa có clip .mp4 nào"))
music = [p for p in (ROOT / "Nhạc nền").glob("*/*.mp3") if not p.parent.name.startswith("_")]
(ok(f"{len(music)} bài nhạc nền") if music else fail("Nhạc nền/ chưa có file .mp3 nào"))
voices = list((ROOT / "Long-tieng" / "elevenlabs").glob("*.mp3"))
(ok(f"{len(voices)} bài đã có giọng đọc ElevenLabs") if voices else warn("chưa có giọng đọc nào: chạy elevenlabs-tts.py (bước 2)"))
key = os.environ.get("ELEVENLABS_API_KEY") or (Path.home() / ".config/elevenlabs/key").exists()
(ok("có API key ElevenLabs") if key else warn("chưa có API key ElevenLabs (chỉ cần khi lồng tiếng bài mới)"))
try:
    (ROOT / "Vid_completed").mkdir(exist_ok=True)
    ok("thư mục Vid_completed ghi được")
except Exception as e:
    fail(f"không tạo được Vid_completed: {e}")
print("\n" + ("Sẵn sàng. Làm theo README.md từ bước 3." if not bad else f"Còn {bad} lỗi ❌ cần sửa trước."))
sys.exit(1 if bad else 0)
