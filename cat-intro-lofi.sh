#!/bin/bash
# Cắt đoạn intro (bỏ khoảng lặng đầu bài) của nhạc lofi, fade in/out, chuẩn hoá -26 LUFS để làm nhạc nền cho thơ.
# Dùng: ./cat-intro-lofi.sh [độ dài giây=36] [thư mục vào] [thư mục ra]
B="$(cd "$(dirname "$0")" && pwd)/Nhạc nền"; LEN=${1:-36}; IN="${2:-$B/Lofi (tải vào đây)}"; OUT="${3:-$B/Lofi intro}"
mkdir -p "$IN" "$OUT"; shopt -s nullglob nocaseglob
for f in "$IN"/*.{mp3,wav,m4a}; do
  n=$(basename "$f"); n="${n%.*}"; o="$OUT/$n.mp3"
  [ -s "$o" ] && continue
  ffmpeg -v error -y -i "$f" -t $((LEN+10)) \
    -af "silenceremove=start_periods=1:start_threshold=-45dB,atrim=0:$LEN,afade=t=in:d=1.5,afade=t=out:st=$((LEN-4)):d=4,loudnorm=I=-26:TP=-6:LRA=7" \
    -ar 44100 -b:a 192k -map_metadata -1 "$o" && echo "ok $n"
done
