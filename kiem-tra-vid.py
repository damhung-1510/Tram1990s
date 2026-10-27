#!/usr/bin/env python3
"""Đo Vid/ và các thư mục con; ghi báo cáo, không chỉnh sửa video gốc.

    python3 kiem-tra-vid.py

Nếu bài đã có audio, dùng thời lượng file giọng đọc + 3s.
Nếu chưa, dùng est của bài (đã gồm lời chào và phần kết), không cộng 3s lần nữa.
"""
import json
from datetime import datetime
from pathlib import Path

import tao_video as video


def main():
    root = video.ROOT
    poems = [p for p in video.load_poems().values() if p.get('kind') == 'Trích dẫn Ngày mới']
    if not poems:
        raise ValueError('Chưa có bài Trích dẫn Ngày mới để so sánh')
    recordings = video.list_audio()
    targets = []
    for p in poems:
        audio = next((a for a in recordings.get(p['id'], []) if a.get('hook')), None)
        if audio:
            seconds = video.render_timing(p, 'trich-dan', video.duration(root / audio['file']))[2]
        else:
            seconds = float(p['est'])
        targets.append(dict(id=p['id'], title=p['title'], seconds=seconds,
                            estimated=audio is None, voice=audio['file'] if audio else None))
    shortest, longest = min(t['seconds'] for t in targets), max(t['seconds'] for t in targets)
    results = []
    for file in sorted((root / 'Vid').rglob('*.mp4')):
        if file.name.startswith('.') or file.stem.endswith('_edited') or 'Ban_goc' in file.parts:
            continue
        entry = dict(file=file.relative_to(root).as_posix())
        try:
            info = video.video_info(file)
            capacity = info['dur'] / video.MIN_VIDEO_SPEED
            eligible = [t['id'] for t in targets if capacity + 1e-8 >= t['seconds']]
            entry.update(info, capacity=capacity, eligible_poems=eligible,
                         status='du' if len(eligible) == len(targets) else 'tuy_bai' if eligible else 'qua_ngan')
            entry['speeds'] = {t['id']: min(video.QUOTE_VIDEO_SPEED, info['dur'] / t['seconds'])
                               for t in targets if t['id'] in eligible}
        except (ValueError, OSError, video.subprocess.TimeoutExpired) as error:
            entry.update(status='loi', error=str(error), eligible_poems=[])
        results.append(entry)

    counts = {status: sum(c['status'] == status for c in results)
              for status in ('du', 'tuy_bai', 'qua_ngan', 'loi')}
    report = dict(checked_at=datetime.now().astimezone().isoformat(timespec='seconds'),
                  min_speed=video.MIN_VIDEO_SPEED, max_speed=video.QUOTE_VIDEO_SPEED,
                  target_seconds=[shortest, longest], targets=targets, counts=counts, clips=results)
    report_json = root / 'Vid' / 'kiem-tra-thoi-luong.json'
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    estimated = sum(t['estimated'] for t in targets)
    lines = [
        '# Kiểm tra thời lượng video mới', '',
        f"Đã đo {len(results)} video trong `Vid/` và các thư mục con. Cập nhật: {report['checked_at']}.", '',
        f"Kết quả: **{counts['qua_ngan']} quá ngắn**, **{counts['tuy_bai']} tùy bài**, **{counts['du']} đủ thời lượng**, {counts['loi']} lỗi.", '',
        f"So sánh với {len(targets)} bài Ngày mới, đích hiện tại **{shortest:g}–{longest:g} giây**. "
        f"{estimated} bài chưa có giọng đọc nên dùng ước tính đã gồm lời chào và phần kết. "
        'Khi có giọng đọc, thời lượng chính xác là toàn bộ file giọng đọc (cả lời chào) + 3 giây; không cộng dư lần nữa.', '',
        'Quy tắc: tốc độ = min(0,85; thời lượng clip / thời lượng cần). Không giảm dưới 0,5×. '
        'Clip dài được cắt phần dư. Clip quá ngắn vẫn giữ để ghép nhiều cảnh, nhưng không chọn dùng riêng hoặc tự lặp cảnh.', '',
        'Đây là kiểm tra thời lượng. Clip có ít khung hình/giây có thể thấy giật khi làm chậm; chưa áp dụng nội suy khung hình. '
        'Các file video gốc được giữ nguyên, tốc độ được áp dụng lúc dựng bài.', '',
    ]
    groups = [('qua_ngan', 'Clip quá ngắn — cần ghép thêm'), ('tuy_bai', 'Clip đủ cho một số bài'),
              ('du', 'Clip đủ cho cả khoảng thời lượng'), ('loi', 'Clip không đọc được')]
    for status, heading in groups:
        entries = [c for c in results if c['status'] == status]
        if not entries:
            continue
        lines += ['## ' + heading, '', '| Clip | Gốc | FPS | Tối đa ở 0,5× | Ghi chú |',
                  '|---|---:|---:|---:|---|']
        for c in entries:
            label = c['file'].removeprefix('Vid/')
            link = f"[{label}](<{root / c['file']}>)"
            if status == 'loi':
                lines.append(f"| {link} | — | — | — | {c['error']} |")
                continue
            speeds = list(c['speeds'].values())
            note = (f"Thiếu ít nhất {shortest - c['capacity']:.1f}s; ghép thêm clip"
                    if status == 'qua_ngan' else
                    f"Đủ {len(c['eligible_poems'])}/{len(targets)} bài; slow {min(speeds):.2f}–{max(speeds):.2f}×")
            lines.append(f"| {link} | {c['dur']:.2f}s | {c['fps']:g} | {c['capacity']:.2f}s | {note} |")
        lines.append('')
    lines += ['Chạy lại sau khi tải clip hoặc tạo giọng đọc mới: `python3 kiem-tra-vid.py`.', '']
    report_md = root / 'Vid' / 'KIEM_TRA_THOI_LUONG.md'
    report_md.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(counts, ensure_ascii=False))
    print(report_md)


if __name__ == '__main__':
    main()
