# Hướng dẫn A–Z: tạo một video thơ hoàn chỉnh từ thư mục Tram1990s

Luồng làm việc: **thơ → giọng đọc ElevenLabs → chọn clip + nhạc nền → Concat dựng theo template → file mp4 trong `Vid_completed/`**.
Mọi lệnh chạy trong thư mục dự án: `cd /đường/dẫn/Tram1990s`.

## Bước 0. Chuẩn bị máy (làm một lần)

| Cần | Cách có |
|---|---|
| macOS, Python 3.9 trở lên (không cần cài thư viện nào) | `python3 --version` |
| ffmpeg và ffprobe | `brew install ffmpeg` |
| **Concat CLI** (`concat-cli`, bản 0.2.7 trở lên) | build từ mã nguồn Concat (cần Rust, xem README của Concat). Trên máy gốc nó nằm ở `…/ConCat/concat/src/target/quick/concat-cli`, build bằng profile `quick` |
| Tài khoản ElevenLabs có API key | elevenlabs.io → API Keys |

Nếu `concat-cli` nằm chỗ khác, báo đường dẫn cho các script:
```bash
export CONCAT_CLI=/đường/dẫn/tới/concat-cli
```

Kiểm tra mọi thứ một lần (báo ✅ ❌ ⚠️ kèm cách sửa):
```bash
python3 kiem-tra-moi-truong.py
```
Ba template Concat (`Thơ Hoài Cổ`, `… Chạy Chữ 2 Trang`, `… Chạy Chữ Nhiều Trang`) đã đi kèm trong thư mục `templates/`, không cần cài vào app.

## Bước 1. Lấy API key và voice ID ElevenLabs

1. elevenlabs.io → **API Keys** → tạo key. Nếu key có **Credit limit**, đặt cao hơn số credit định dùng (mỗi bài khoảng 150–250 credit, tính ~0,4 credit mỗi ký tự với model v4).
2. Lưu key vào file riêng để mọi terminal dùng được (gõ key, không hiện lên màn hình):
   ```bash
   mkdir -p ~/.config/elevenlabs && chmod 700 ~/.config/elevenlabs && read -s K && echo "$K" > ~/.config/elevenlabs/key && chmod 600 ~/.config/elevenlabs/key && unset K
   ```
   (Hoặc `export ELEVENLABS_API_KEY=...` trong đúng tab terminal sẽ chạy lệnh.)
3. **Voice ID**: Voices → My Voices → bấm giọng → chép ID. Giọng phải nằm trong My Voices.

## Bước 2. Lồng tiếng (giọng đọc gồm câu mở đầu + bài thơ)

```bash
python3 elevenlabs-tts.py --voice-id MÃ_GIỌNG --ids Q044 L10 --dry-run   # chỉ đếm ký tự, không tốn credit
python3 elevenlabs-tts.py --voice-id MÃ_GIỌNG --ids Q044 L10             # tạo thật
python3 elevenlabs-tts.py --voice-id MÃ_GIỌNG --top10                    # 10 bài tình yêu đã chọn sẵn
```
- File mp3 vào `Long-tieng/elevenlabs/<mã>_<tên>.mp3`. Model mặc định `eleven_v4` (đổi bằng `--model`).
- Bài nào xong được ghi vào `Thơ/da-long-tieng.json` và đánh dấu "✅ Đã lồng tiếng" trong trang HTML. Chạy lại sẽ bỏ qua bài đã xong (`--force` để làm lại).
- Kịch bản đọc (câu mở đầu + thơ + nhịp ngắt) nằm trong `Thơ/elevenlabs-script.md` và `Thơ/bai-chinh-thuc.json`.

## Bước 3. Template tự chọn theo bài

Mỗi bài có một **khóa template** trong `Thơ/template-bai.json` (sửa tay được). Quy tắc gắn sẵn:
- ≤ 7 dòng → **Thơ Hoài Cổ** (chữ tĩnh 1 trang);
- đúng 8 dòng → **Chạy Chữ 2 Trang** (2 trang × 4 dòng);
- hơn 8 dòng → **Chạy Chữ Nhiều Trang** (mỗi trang 6 dòng); truyện ngắn: mỗi trang 2 câu.

Bài mới thêm vào, hoặc muốn gắn lại tất cả: `python3 gan-template.py` (thêm `--reset` để ghi đè khóa cũ).

## Bước 4. Tạo video

**Cách A, có giao diện** (nên dùng):
```bash
python3 tao_video.py
```
Mở **http://127.0.0.1:8787/** (phải mở qua địa chỉ này, mở file HTML trực tiếp thì nút Tạo video không chạy). Trong trang:
1. Tab **✅ Đã lồng tiếng** (hoặc tab Thơ, bài đã lồng tiếng nằm đầu): bấm **🎬 Chọn bài này**.
2. Panel dưới cùng hiện **Giọng** và **Template** đã chọn theo khóa.
3. Chọn **Clip**: bấm "Thư mục video gợi ý" ở thẻ bài, tick ☐ một hoặc nhiều clip dọc.
4. Chọn **Nhạc nền** trong hộp chọn (có nút nghe thử, chỉnh to nhỏ).
5. Đủ bốn thứ thì nút **Tạo video** sáng lên. Bấm rồi chờ khoảng 1–2 phút. Link mở video hiện khi xong.

**Cách B, dòng lệnh** (không cần mở trang):
```bash
python3 tao_video.py --make Q044 \
  --videos "Videos/14_Co-don-tram-lang/TramCamXuc_14_V002_silhouetted-figure-walking-at-sunset-outdoors.mp4" \
  --music "Nhạc nền/Quốc tế (Kevin MacLeod - CC BY)/Almost_Bliss.mp3"
```
Giọng đọc mặc định là bản ElevenLabs của bài đó (đổi bằng `--voice`). Có thể truyền nhiều clip sau `--videos`.

**Kết quả** nằm ở `Vid_completed/<mã>_<tên>_<ngày-giờ>.mp4`, khổ 1080×1920.

Quy tắc thời lượng: video dài **0,5 giây + giọng đọc + 3 giây**. Giọng đọc bắt đầu ở giây 0,5, nhạc và clip bị cắt đúng mốc này (nhạc ngắn thì lặp lại, clip ngắn thì chạy chậm). Tên bài, tên tác giả (hoặc "Thơ dân gian", "Trích dẫn dân gian", "Không rõ", "Tự biên") và chữ chạy theo giọng đều tự điền vào template.

## Bước 5. Thêm nhạc nền (tuỳ chọn)

Các script xử lý nhạc (chạy từ thư mục dự án):
```bash
./xu-ly-nhac.sh            # cắt nhạc trong "Nhạc nền/_Tải Pixabay vào đây" thành đoạn ≤ 55 giây vào "Nhạc nền/Việt Nam"
./giam-am-luong.sh         # chuẩn hoá âm lượng nhạc về -26 LUFS (nhỏ hơn giọng đọc)
./cat-intro-lofi.sh        # cắt intro ~36 giây của nhạc lofi bỏ vào "Nhạc nền/Lofi (tải vào đây)" → "Nhạc nền/Lofi intro"
```
Nhạc mới hiện trong hộp chọn nhạc sau khi tải lại trang. Thư mục bắt đầu bằng `_` bị bỏ qua.

## Lỗi thường gặp

| Thông báo | Cách xử lý |
|---|---|
| `Thiếu biến môi trường ELEVENLABS_API_KEY` | làm bước 1.2, hoặc export key trong đúng tab đang chạy |
| `quota_exceeded` | nâng **Credit limit** của key (hạn mức đặt trên key, không phải số dư tài khoản) rồi chạy lại, bài đã xong được bỏ qua |
| `Bài … chưa có giọng đọc` | chạy bước 2 cho bài đó |
| `không thấy template …` | thư mục `templates/` thiếu một trong 3 template (xem bước 0) |
| `Không thấy concat-cli` | đặt `CONCAT_CLI` hoặc build Concat |
| Nút Tạo video xám | còn thiếu một trong: thơ, giọng, clip, nhạc. Panel ghi rõ còn thiếu gì |
| Không chọn được clip/bài mới trong trang | trang liệt kê clip và bài từ dữ liệu đã dựng sẵn. Xem ghi chú dưới |

## Các file quan trọng

- `tao_video.py`, `tao-video.js`, `GHEP_THO_VIDEO.html`: máy chủ, giao diện và trang chọn.
- `elevenlabs-tts.py`, `danh-dau-long-tieng.py`, `gan-template.py`: lồng tiếng, đánh dấu, gắn khóa template.
- `Thơ/bai-chinh-thuc.json` (40 bài + câu mở đầu + kịch bản), `Thơ/template-bai.json`, `Thơ/da-long-tieng.json`.
- `templates/` (3 template), `Videos/`, `Nhạc nền/`, `Long-tieng/elevenlabs/`, `Vid_completed/`.
- Không cần cho việc tạo video: `long-tieng.py` (giọng cũ, cần VieNeu-TTS riêng), `tai-clip-doc-pexels.py` (tải clip một lần, phụ thuộc file tạm), `_loai-bo/`.

## Giới hạn cần biết

- Danh sách bài và clip trong trang HTML là dữ liệu dựng sẵn. Thêm clip mới vào `Videos/` thì dùng được ngay bằng cách B (`--videos`), còn để hiện trong giao diện thì cần dựng lại trang; script dựng lại chưa được đóng gói trong thư mục này.
- Đã thử trọn luồng trên một máy macOS (Apple M1). Chưa kiểm tra trên máy khác hoặc Windows.
