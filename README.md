# Tram1990s: video thơ hoài cổ

Tạo video thơ (giọng đọc ElevenLabs + clip dọc + nhạc nền) bằng template Concat. **Đọc `HUONG_DAN.md` để làm từ A đến Z.**

Repo này chỉ chứa mã nguồn, dữ liệu thơ, 3 template Concat và hướng dẫn. **Không có** các thư mục nặng, bạn tự chuẩn bị:

| Thư mục | Nội dung | Ghi chú |
|---|---|---|
| `Videos/` | clip dọc 1080×1920 (nguồn Pexels, giấy phép miễn phí) | chia theo chủ đề; chạy `kiem-tra-moi-truong.py` để biết thiếu gì |
| `Nhạc nền/` | file `.mp3` nhạc nền | Kevin MacLeod (CC BY, ghi nguồn), Pixabay |
| `Long-tieng/elevenlabs/` | giọng đọc tạo từ `elevenlabs-tts.py` | cần API key và voice ID của riêng bạn |

Bắt đầu nhanh: `python3 kiem-tra-moi-truong.py`, rồi `python3 tao_video.py` và mở http://127.0.0.1:8787/.
