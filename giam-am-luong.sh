#!/bin/bash
# Chuẩn hoá nhạc nền về -26 LUFS (nhỏ hơn giọng đọc ~10dB), đè trực tiếp lên file trong các thư mục nhạc đã cắt.
B="$(cd "$(dirname "$0")" && pwd)/Nhạc nền"; LUFS=${1:--26}
find "$B/Việt Nam" "$B/Quốc tế (Kevin MacLeod - CC BY)" -name '*.mp3' -print0 | xargs -0 -P4 -I{} bash -c '
f="$1"; t="${f%.mp3}.tmp.mp3"
ffmpeg -v error -y -i "$f" -af "loudnorm=I='"$LUFS"':TP=-6:LRA=7" -ar 44100 -b:a 192k -map_metadata -1 "$t" && mv "$t" "$f" || rm -f "$t"' _ {}
