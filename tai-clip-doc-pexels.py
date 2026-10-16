#!/usr/bin/env python3
"""Tải clip dọc 1080x1920 từ Pexels theo manifest, kiểm tra bằng ffprobe, ghi nguồn vào Videos/_nguon-pexels.csv."""
import csv, json, os, subprocess, sys, concurrent.futures as cf
R = '/Volumes/Volume/Tram1990s/Videos'
S = '/private/tmp/claude-501/-Volumes-Volume-Tram1990s/1ff9a4c9-2570-483e-ac10-a33f66bafb08/scratchpad/'
M = {**json.load(open(S + 'manifest1.json')), **json.load(open(S + 'manifest2.json'))}
UA = 'Mozilla/5.0'

def head_ok(u):
    return subprocess.run(['curl', '-sI', '-m', '20', '-o', '/dev/null', '-w', '%{http_code}', u], capture_output=True, text=True).stdout.strip() == '200'

def resolve(id_, fid, fps):
    if fid:
        return f'https://videos.pexels.com/video-files/{id_}/{fid}_1080_1920_{fps}fps.mp4'
    for f in (30, 25, 24, 50, 60):
        u = f'https://videos.pexels.com/video-files/{id_}/{id_}-hd_1080_1920_{f}fps.mp4'
        if head_ok(u):
            return u
    return None

def job(args):
    folder, n, line = args
    id_, fid, fps, dur, slug = line.split(',', 4)
    out = f'{R}/{folder}/TramCamXuc_{folder[:2]}_V{n:03d}_{slug}.mp4'
    if os.path.exists(out) and os.path.getsize(out) > 100000:
        return folder, id_, out, 'đã có', None
    u = resolve(id_, fid, fps)
    if not u:
        return folder, id_, out, 'KHÔNG TÌM THẤY LINK', None
    for attempt in range(3):
        r = subprocess.run(['curl', '-sL', '-m', '600', '-A', UA, '-o', out + '.part', u])
        if r.returncode == 0 and os.path.exists(out + '.part'):
            p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                '-of', 'csv=p=0', out + '.part'], capture_output=True, text=True).stdout.strip()
            if p and p.splitlines()[0].split(',')[:2] == ['1080', '1920']:
                os.rename(out + '.part', out)
                return folder, id_, out, 'ok', u
        if os.path.exists(out + '.part'):
            os.remove(out + '.part')
    return folder, id_, out, f'LỖI tải/kiểm tra ({u})', u

jobs = [(f, i + 1, l) for f, L in M.items() for i, l in enumerate(L)]
rows = []
with cf.ThreadPoolExecutor(4) as ex:
    for folder, id_, out, st, u in ex.map(job, jobs):
        print(st, '|', os.path.basename(out), flush=True)
        rows.append([folder, id_, os.path.basename(out), st, u or '', f'https://www.pexels.com/video/{id_}/'])
with open(R + '/_nguon-pexels.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['Thư mục', 'Pexels ID', 'File', 'Trạng thái', 'Link tải', 'Trang nguồn']); w.writerows(rows)
bad = [r for r in rows if r[3] not in ('ok', 'đã có')]
print('XONG', len(rows) - len(bad), '/', len(rows), 'lỗi:', len(bad))
