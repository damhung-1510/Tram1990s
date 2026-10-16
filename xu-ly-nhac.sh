#!/bin/bash
# Cắt nhạc trong "Nhạc nền/_Tải Pixabay vào đây" thành các đoạn ≤55s (fade in/out) -> "Nhạc nền/Việt Nam"
# Bài >=130s được cắt 2 đoạn (đầu bài + đoạn từ giây 60) để có nhiều lựa chọn hơn.
B="$(cd "$(dirname "$0")" && pwd)/Nhạc nền"; IN="$B/_Tải Pixabay vào đây"; OUT="$B/Việt Nam"; MAXD=${1:-55}
mkdir -p "$OUT"; shopt -s nullglob nocaseglob
cut() { # file start len out
  ffmpeg -v error -y -ss "$2" -i "$1" -t "$3" -af "afade=t=in:d=1,afade=t=out:st=$(( $3 - 4 )):d=4" -ar 44100 -b:a 192k -map_metadata -1 "$4" && echo "ok $(basename "$4")"
}
for f in "$IN"/*.{mp3,wav,m4a}; do
  n=$(basename "$f"); n="${n%.*}"
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"); d=${d%.*}
  t=$(( d < MAXD ? d : MAXD ))
  [ -s "$OUT/$n.mp3" ] || cut "$f" 0 $t "$OUT/$n.mp3"
  if [ "$d" -ge 130 ]; then [ -s "$OUT/${n}_p2.mp3" ] || cut "$f" 60 $MAXD "$OUT/${n}_p2.mp3"; fi
done
