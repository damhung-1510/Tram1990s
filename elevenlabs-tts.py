#!/usr/bin/env python3
"""Tạo giọng đọc ElevenLabs từ Thơ/bai-chinh-thuc.json.

Cách dùng:
  export ELEVENLABS_API_KEY=...            # đặt trong terminal của bạn, không dán vào chat
  python3 elevenlabs-tts.py --voice-id ID --ids C02 N01 T02 --dry-run   # chỉ đếm ký tự
  python3 elevenlabs-tts.py --voice-id ID --ids C02 N01 T02             # gọi API thật
  python3 elevenlabs-tts.py --voice-id ID --voice Nữ                    # tất cả bài giọng nữ
"""
import argparse, json, os, re, sys, time, unicodedata, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(ROOT, 'Thơ', 'da-long-tieng.json')

def load_state():
    return json.load(open(STATE, encoding='utf-8')) if os.path.exists(STATE) else {}

def save_state(st):
    json.dump(st, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def mark_summaries():
    import importlib.util
    spec = importlib.util.spec_from_file_location('dd', os.path.join(ROOT, 'danh-dau-long-tieng.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.main()
OUT = os.path.join(ROOT, 'Long-tieng', 'elevenlabs')

def slug(s):
    s = unicodedata.normalize('NFD', s.replace('đ', 'd').replace('Đ', 'D'))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-')[:40]

def main():
    a = argparse.ArgumentParser()
    a.add_argument('--voice-id', required=True)
    a.add_argument('--model', default='eleven_v4', help='eleven_v4 (mặc định), eleven_v4_turbo (nhanh), eleven_v3 hoặc eleven_multilingual_v2')
    a.add_argument('--ids', nargs='*', help='mã bài, ví dụ C02 N01 T02')
    a.add_argument('--voice', choices=['Nữ', 'Nam', 'Cả hai'], help='lọc theo giọng gợi ý')
    a.add_argument('--stability', type=float, default=0.5)
    a.add_argument('--top10', action='store_true', help='10 bài tình yêu đã chọn (Thơ/top10-tinh-yeu.json)')
    a.add_argument('--force', action='store_true', help='lồng tiếng lại cả bài đã đánh dấu')
    a.add_argument('--dry-run', action='store_true')
    args = a.parse_args()

    items = json.load(open(os.path.join(ROOT, 'Thơ', 'bai-chinh-thuc.json'), encoding='utf-8'))
    if args.top10:
        args.ids = [x['id'] for x in json.load(open(os.path.join(ROOT, 'Thơ', 'top10-tinh-yeu.json'), encoding='utf-8'))]
    state = load_state()
    if args.ids:
        items = [x for x in items if x['id'] in args.ids]
    if args.voice:
        items = [x for x in items if x['voice'] == args.voice]
    if not items:
        sys.exit('Không có bài nào khớp.')
    done = [x['id'] for x in items if x['id'] in state]
    if done and not args.force:
        print('Bỏ qua bài đã lồng tiếng:', ', '.join(done), '(thêm --force nếu muốn làm lại)')
        items = [x for x in items if x['id'] not in state]
    if not items:
        sys.exit('Không còn bài nào cần lồng tiếng.')

    total = sum(len(x['tts']) for x in items)
    print(f'{len(items)} bài, {total} ký tự (≈ {total} credit nếu 1 ký tự = 1 credit)')
    for x in items:
        print(f"  {x['id']:5} {len(x['tts']):4} ký tự  {x['title']}")
    if args.dry_run:
        return

    key = os.environ.get('ELEVENLABS_API_KEY')
    if not key:   # hoặc đặt key vào file ~/.config/elevenlabs/key (chmod 600) để mọi terminal đều dùng được
        kf = os.path.expanduser('~/.config/elevenlabs/key')
        if os.path.exists(kf):
            key = open(kf).read().strip()
    if not key:
        sys.exit('Thiếu biến môi trường ELEVENLABS_API_KEY.')
    os.makedirs(OUT, exist_ok=True)
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{args.voice_id}?output_format=mp3_44100_128'
    for x in items:
        path = os.path.join(OUT, f"{x['id']}_{slug(x['title'])}.mp3")
        if os.path.exists(path):
            print('bỏ qua (đã có file):', path)
            state.setdefault(x['id'], dict(voice_id=args.voice_id, model=args.model, chars=len(x['tts']), file=os.path.relpath(path, ROOT), date=time.strftime('%Y-%m-%d')))
            save_state(state); continue
        body = {'text': x['tts'], 'model_id': args.model, 'language_code': 'vi',
                'voice_settings': {'stability': args.stability, 'similarity_boost': 0.75}}
        req = urllib.request.Request(url, json.dumps(body).encode(), {
            'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                open(path, 'wb').write(r.read())
            print('đã tạo:', path)
            state[x['id']] = dict(voice_id=args.voice_id, model=args.model, chars=len(x['tts']), file=os.path.relpath(path, ROOT), date=time.strftime('%Y-%m-%d'))
            save_state(state); mark_summaries()
        except urllib.error.HTTPError as e:
            print(f"LỖI {x['id']}: HTTP {e.code} {e.read().decode(errors='ignore')[:300]}")
        time.sleep(1)

if __name__ == '__main__':
    main()
