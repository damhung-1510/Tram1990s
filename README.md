# Tram1990s – Hướng dẫn A–Z tạo video thơ

Luồng làm việc: **thơ → giọng đọc ElevenLabs → chọn clip + nhạc nền → Concat dựng theo template → file mp4 trong `Vid_completed/`**.
Mọi lệnh chạy trong thư mục dự án: `cd /đường/dẫn/Tram1990s`.

Nếu chuyển sang Mac Intel, xem mục **Chuyển dự án sang Mac Intel** ở cuối tài liệu. Bản `concat-cli` ARM trên máy M1 không dùng được trên Intel; phải build lại bản `x86_64`.

## Bước 0. Chuẩn bị máy (làm một lần)

| Cần | Cách có |
|---|---|
| macOS, Python 3.9 trở lên và Pillow để dàn chữ | `python3 --version`, `python3 -m pip install --target .tools/python Pillow` |
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
Sáu template (`Thơ Hoài Cổ`, `… Chạy Chữ 2 Trang`, `… Chạy Chữ Nhiều Trang`, `Trích Dẫn Không Chữ`, `Trích dẫn`, `Ảnh Thơ Giấy Hoài Cổ`) đã đi kèm trong thư mục `templates/`. Khi tạo nội dung, bạn có thể đổi template ngay trên thanh công cụ.

## Bước 1. Lấy API key và voice ID ElevenLabs

1. elevenlabs.io → **API Keys** → tạo key. Nếu key có **Credit limit**, đặt cao hơn số credit định dùng (mỗi bài khoảng 150–250 credit, tính ~0,4 credit mỗi ký tự với model v4).
2. Lưu key vào file riêng để mọi terminal dùng được (gõ key, không hiện lên màn hình):
   ```bash
   mkdir -p ~/.config/elevenlabs && chmod 700 ~/.config/elevenlabs && read -s K && echo "$K" > ~/.config/elevenlabs/key && chmod 600 ~/.config/elevenlabs/key && unset K
   ```
   (Hoặc `export ELEVENLABS_API_KEY=...` trong đúng tab terminal sẽ chạy lệnh.)
3. **Voice ID**: Voices → My Voices → bấm giọng → chép ID. Giọng phải nằm trong My Voices.

## Bước 2. Lồng tiếng (giọng đọc gồm câu mở đầu + bài thơ; riêng **trích dẫn** không có lời mở, chỉ đọc nội dung)

Trên giao diện, bài chưa có file âm thanh ở máy này có nút **Lồng tiếng** và
lựa chọn **Giọng thơ / Giọng trích dẫn**. Xem kịch bản rồi bấm **Tạo giọng đọc**
để gửi tới ElevenLabs bằng model `eleven_v4` (dùng credit tài khoản).
Khi xong, giọng đọc tự xuất hiện trong thẻ bài và bài được chọn để ghép video.
Dấu đã lồng tiếng từ Git không thay thế file MP3: nếu thiếu file, nút vẫn hiện.

```bash
python3 elevenlabs-tts.py --voice-id MÃ_GIỌNG --ids Q044 L10 --dry-run   # chỉ đếm ký tự, không tốn credit
python3 elevenlabs-tts.py --voice-id MÃ_GIỌNG --ids Q044 L10             # tạo thật
python3 elevenlabs-tts.py --voice-id MÃ_GIỌNG --top10                    # 10 bài tình yêu đã chọn sẵn
```
- File mp3 vào `Long-tieng/elevenlabs/<mã>_<tên>.mp3`. Model mặc định `eleven_v4` (đổi bằng `--model`).
- Bài nào xong được ghi vào `Thơ/da-long-tieng.json` và đánh dấu "✅ Đã lồng tiếng" trong trang HTML. Chạy lại sẽ bỏ qua bài đã xong (`--force` để làm lại).
- Kịch bản đọc (câu mở đầu + thơ + nhịp ngắt) nằm trong `Thơ/elevenlabs-script.md` và `Thơ/bai-chinh-thuc.json`.

## Bước 3. Template tự chọn theo bài

Khi chọn một bài, hệ thống **gợi ý template theo phân loại**:
- ≤ 7 dòng → **Thơ Hoài Cổ** (chữ tĩnh 1 trang);
- đúng 8 dòng → **Chạy Chữ 2 Trang** (2 trang × 4 dòng);
- hơn 8 dòng → **Chạy Chữ Nhiều Trang** (mỗi trang 6 dòng);
- **Trích dẫn** (loại "Trích dẫn") → **Trích dẫn**: hình ảnh trong, chỉ làm mờ khi mở bài; không có màu vintage, lớp warm, film grain hay vignette. Template vẫn giữ giọng đọc, nhạc nền và dòng nhỏ **TRẠM 1990s**; không hiện tên bài, tác giả hay nội dung.

Đây chỉ là gợi ý ban đầu. Nếu bạn chọn template khác trong danh sách trước khi bấm **Tạo video**, hệ thống luôn dùng template bạn đã chọn. Các khóa gợi ý được lưu trong `Thơ/template-bai.json`; bài mới thêm vào có thể cập nhật bằng `python3 gan-template.py` (thêm `--reset` để phân loại lại tất cả).

## Bước 4. Tạo video

**Cách A, có giao diện** (nên dùng):
```bash
python3 tao_video.py
```
Mở **http://127.0.0.1:8787/** (phải mở qua địa chỉ này, mở file HTML trực tiếp thì nút Tạo video không chạy). Trong trang:
1. Tab **✅ Đã lồng tiếng** (hoặc tab Thơ, bài đã lồng tiếng nằm đầu): bấm **🎬 Chọn bài này**.
2. Panel dưới cùng hiện **Giọng** và **Template** được gợi ý theo phân loại. Bạn có thể đổi template; lựa chọn của bạn được ưu tiên khi tạo video.
3. Chọn **Clip**: bấm "Thư mục video gợi ý" ở thẻ bài, tick ☐ một hoặc nhiều clip dọc.
4. Chọn **Nhạc nền** trong hộp chọn (có nút nghe thử, chỉnh to nhỏ).
5. Đủ bốn thứ thì nút **Tạo video** sáng lên. Bấm rồi chờ khoảng 1–2 phút. Link mở video hiện khi xong.

Template **Thơ Reels · Đọc Nhanh** dành cho thử nghiệm giữ chân: tự hiện câu mở đầu ngay,
chia thơ thành 4–5 dòng/trang, căn trái trong vùng an toàn và chỉ hiện tên bài–tác giả ở đoạn kết.
Ở cả Reels Đọc Nhanh và Reels Ảnh Mờ, mỗi câu xuất hiện trọn vẹn trên một lớp riêng
và giữ nguyên đến hết khổ; câu mới không làm mờ hoặc dời các câu trước.
Khối thơ có lề 8% hai bên.
Lời mở và dòng thơ đầu dùng chung điểm bắt đầu ở góc trái phía trên của khối chữ;
lời mở kết thúc đúng lúc dòng thơ đầu xuất hiện để chuyển đổi liền mạch.

**Cách B, dòng lệnh** (không cần mở trang):
```bash
python3 tao_video.py --make Q044 \
  --videos "Videos/14_Co-don-tram-lang/TramCamXuc_14_V002_silhouetted-figure-walking-at-sunset-outdoors.mp4" \
  --music "Nhạc nền/Quốc tế (Kevin MacLeod - CC BY)/Almost_Bliss.mp3"
```
Giọng đọc mặc định là bản ElevenLabs của bài đó (đổi bằng `--voice`). Có thể truyền nhiều clip sau `--videos`.

**Kết quả** nằm ở `Vid_completed/<mã>_<tên>_<ngày-giờ>.mp4`, khổ 1080×1920.

### Xuất ảnh thơ giấy hoài cổ 4K

Trong **Ghép Thơ Video**, chọn template **Ảnh Thơ Giấy Hoài Cổ · PNG 4K**. Giao diện tự chuyển sang chế độ **Ghép ảnh**; không cần chọn giọng, clip hoặc nhạc. Ảnh dọc 2160×3840, 300 dpi nhận tối đa 10 dòng và tự điền tác giả cùng tên trang **TRẠM 1990s**.

Cũng có thể xuất bằng dòng lệnh:

```bash
python3 tao-anh-tho.py --id Q038
```

Muốn đổi riêng tên bài trên ảnh mà không sửa dữ liệu gốc:

```bash
python3 tao-anh-tho.py --id Q038 --title "Vầng trăng ai xẻ làm đôi"
```

Ảnh được lưu trong `Anh_completed/`. Template nằm ở `templates/anh-tho-giay-hoai-co/template.json`.

Âm lượng nhạc nền tự cân theo giọng đọc: mỗi lần tạo video, script đo độ lớn (LUFS) của giọng và của bài nhạc rồi hạ nhạc xuống thấp hơn giọng khoảng **15 dB**, nên bài nhạc nào cũng vừa. Thanh to/nhỏ trong giao diện (và `--music-volume` ở dòng lệnh) chỉ giảm từ mức đó (1,0 = to nhất, mặc định; không vượt mức 15 dB dưới giọng). Muốn nhạc nhỏ hơn hoặc to hơn cho mọi video: `MUSIC_BELOW_DB=26 python3 tao_video.py` (số lớn = nhạc nhỏ hơn).

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

Lỗi xuất video được giữ trên giao diện, in trong Terminal và lưu chi tiết vào
`.tao-video-logs/<mã-tác-vụ>.log`. Nếu Concat không phản hồi, tác vụ sẽ báo hết thời gian chờ.

| Thông báo | Cách xử lý |
|---|---|
| `Thiếu biến môi trường ELEVENLABS_API_KEY` | làm bước 1.2, hoặc export key trong đúng tab đang chạy |
| `quota_exceeded` | nâng **Credit limit** của key (hạn mức đặt trên key, không phải số dư tài khoản) rồi chạy lại, bài đã xong được bỏ qua |
| `Bài … chưa có giọng đọc` | chạy bước 2 cho bài đó |
| `không thấy template …` | thư mục `templates/` thiếu một trong 6 template (xem bước 0) |
| `Không thấy concat-cli` | đặt `CONCAT_CLI` hoặc build Concat |
| `No module named 'PIL'` | cài `python3 -m pip install --target .tools/python Pillow`, rồi khởi động lại server |
| PNG báo `Decoder not found` | FFmpeg cần giải mã PNG; nếu tự build với `--disable-autodetect`, bổ sung `--enable-zlib` |
| Nút Tạo video xám | còn thiếu một trong: thơ, giọng, clip, nhạc. Panel ghi rõ còn thiếu gì |
| Không chọn được clip/bài mới trong trang | trang liệt kê clip và bài từ dữ liệu đã dựng sẵn. Xem ghi chú dưới |

## Thêm hoặc xóa bài

Dùng `quan-ly-bai.py`, nó cập nhật cùng lúc trang HTML, CSV, `bai-chinh-thuc.json`, kịch bản ElevenLabs, khóa template và câu mở đầu:
```bash
python3 quan-ly-bai.py --xoa K01 K02                    # xóa bài theo mã
python3 quan-ly-bai.py --them Thơ/trich-dan-moi.json    # thêm bài từ một file JSON (mẫu: Thơ/trich-dan-moi.json)
```
Mỗi bài trong file JSON gồm: `id, title, kind, author, text, hook, mood, voice, note, source`. Bài mới thêm xong thì lồng tiếng bằng `elevenlabs-tts.py --ids <mã>`.

## Các file quan trọng

- `tao_video.py`, `tao-video.js`, `GHEP_THO_VIDEO.html`: máy chủ, giao diện và trang chọn.
- `elevenlabs-tts.py`, `danh-dau-long-tieng.py`, `gan-template.py`: lồng tiếng, đánh dấu, gắn khóa template.
- `Thơ/bai-chinh-thuc.json` (danh sách bài + câu mở đầu + kịch bản), `Thơ/template-bai.json`, `Thơ/da-long-tieng.json`.
- `templates/` (6 template), `Videos/`, `Nhạc nền/`, `Long-tieng/elevenlabs/`, `Anh_completed/`, `Vid_completed/`.
- Không cần cho việc tạo video: `long-tieng.py` (giọng cũ, cần VieNeu-TTS riêng), `tai-clip-doc-pexels.py` (tải clip một lần, phụ thuộc file tạm), `_loai-bo/`.

## Giới hạn cần biết

- Bài thêm hoặc xóa bằng `quan-ly-bai.py` hiện ngay trong trang. Clip mới tải vào `Videos/` sẽ mặc định được quét lại và hiện trong giao diện mỗi lần mở nút **＋ Tất cả clip** (không cần cập nhật danh sách thủ công), hoặc có thể truyền trực tiếp bằng cách B (`--videos`).
- Nhạc trong các thư mục con được máy chủ tự quét. Sau khi thêm hoặc cắt nhạc trong `Nhạc nền/Piano radio 40s/`, chạy `python3 cap-nhat-nhac.py` để đồng bộ tab Nhạc nền trong `GHEP_THO_VIDEO.html`.
- Đã thử trọn luồng trên một máy macOS (Apple M1). Chưa kiểm tra trên máy khác hoặc Windows.

## Chuyển dự án sang Mac Intel

Máy Intel phải tự biên dịch `concat-cli` cho kiến trúc `x86_64`. File `concat-cli` trên máy M1 hiện tại là bản `arm64`, nên chép file đó sang sẽ không chạy.

### 1. Chép dữ liệu từ máy hiện tại

Chép nguyên thư mục `Tram1990s`, tối thiểu phải có `Videos/`, `Nhạc nền/`, `Long-tieng/`, `Thơ/`, `templates/` và các file `.py`, `.js`, `.html` ở thư mục gốc.

Có thể bỏ `_loai-bo/`, `.git/`, `.thumbs/`, `.tao-video-tmp/`, `__pycache__/` và `Vid_completed/`. Phần cần dùng để dựng video hiện khoảng 5,2 GB.

Chép cả mã nguồn Concat nhưng bỏ thư mục build `src/target/`, vì thư mục này chứa bản ARM và chiếm khoảng 22 GB.

Ví dụ khi ổ chép dữ liệu được gắn tại `/Volumes/USB`:

```bash
rsync -a --exclude .git --exclude _loai-bo --exclude .thumbs \
  --exclude .tao-video-tmp --exclude __pycache__ --exclude Vid_completed \
  /Volumes/Volume/Tram1990s/ /Volumes/USB/Tram1990s/

rsync -a --exclude .git --exclude src/target \
  /Volumes/Volume/movie_creator/ConCat/concat/ /Volumes/USB/Concat/
```

### 2. Cài công cụ trên Mac Intel

```bash
xcode-select --install
brew install ffmpeg cmake pkg-config
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustup toolchain install 1.93.0
rustup default 1.93.0
```

Kiểm tra máy có Metal:

```bash
system_profiler SPDisplaysDataType | grep -A2 Metal
```

Kết quả phải có `Metal: Supported`. Concat cần GPU/Metal để xuất hình.

### 3. Build concat-cli bản Intel

Giả sử đã chép mã nguồn Concat vào `~/Concat`:

```bash
cd ~/Concat/src
cargo build --profile quick -p concat-cli
file target/quick/concat-cli
./target/quick/concat-cli --version
```

Lệnh `file` phải hiện `x86_64`; phiên bản CLI cần từ `0.2.7`.

Lưu đường dẫn để các Terminal mới tự nhận:

```bash
echo 'export CONCAT_CLI="$HOME/Concat/src/target/quick/concat-cli"' >> ~/.zshrc
source ~/.zshrc
```

### 4. Kiểm tra và chạy

```bash
cd ~/Tram1990s
python3 kiem-tra-moi-truong.py
python3 tao_video.py
```

Sau đó mở [http://127.0.0.1:8787/](http://127.0.0.1:8787/). Video xuất vào `~/Tram1990s/Vid_completed/`.

API key ElevenLabs chỉ cần nếu muốn lồng tiếng mới. Chép key sang máy Intel hoặc tạo lại:

```bash
mkdir -p ~/.config/elevenlabs
chmod 700 ~/.config/elevenlabs
read -s K
echo "$K" > ~/.config/elevenlabs/key
chmod 600 ~/.config/elevenlabs/key
unset K
```

Nếu chỉ ghép video bằng các file giọng đã có trong `Long-tieng/elevenlabs/`, không cần API key.
