"""Lồng tiếng thơ bằng VieNeu (v3 Turbo), giảm tốc 0.9 sau khi tạo.
Chạy:  /Volumes/Volume/movie_creator/VieNeu-Voice/VieNeu-TTS/.venv/bin/python long-tieng.py [nam|nu|all]
- Nam: giọng preset "Quốc Tuấn".
- Nữ: Hà My / Ái Chi / Kim Chi được clone từ file mẫu 3–8s đặt trong Long-tieng/_giong-mau/ (Ha-My.wav, Ai-Chi.wav, Kim-Chi.wav).
- Gán giọng nữ cho từng bài: Long-tieng/_phan-giong-nu.json. File mp3 đã có sẽ được bỏ qua."""
import sys,os,json,re,subprocess,unicodedata,glob
sys.path.insert(0,'/Volumes/Volume/movie_creator/VieNeu-Voice/VieNeu-TTS/src')
import numpy as np, soundfile as sf
from vieneu import Vieneu
ROOT=os.path.dirname(os.path.abspath(__file__)); OUT=ROOT+'/Long-tieng'; SPEED=0.9
RAW=ROOT+'/Long-tieng/_tho_raw'; os.makedirs(RAW,exist_ok=True)
slug=lambda s:re.sub(r'[^A-Za-z0-9]+','-',''.join(c for c in unicodedata.normalize('NFD',s.replace('đ','d').replace('Đ','D')) if unicodedata.category(c)!='Mn')).strip('-')[:40]
mode=sys.argv[1] if len(sys.argv)>1 else 'all'
P=json.load(open(ROOT+'/Thơ/tat-ca-tho.json'))
vm={}
if mode in('nam','all'): vm.update({p['id']:'Quốc Tuấn' for p in P if p['voice'] in('Nam','Cả hai')})
if mode in('nu','all'): vm.update(json.load(open(OUT+'/_phan-giong-nu.json'))['phan_giong'])
v=Vieneu(mode="v3turbo")
SAMPLES={'Hà My':'Ha-My','Ái Chi':'Ai-Chi','Kim Chi':'Kim-Chi'}
for name,base in SAMPLES.items():
    if name in vm.values():
        f=(glob.glob(f'{OUT}/_giong-mau/{base}.*') or [None])[0]
        if not f: sys.exit(f'Thiếu file giọng mẫu cho {name}: {OUT}/_giong-mau/{base}.wav')
        v.add_voice(name,f)
man={}
for p in P:
    if p['id'] not in vm: continue
    voice=vm[p['id']]; fn=f"{p['id']}_{slug(p['title'])}_{slug(voice)}.mp3"; dst=f'{OUT}/{fn}'
    if not os.path.exists(dst):
        raw=f"{RAW}/{p['id']}_{slug(voice)}.wav"; sf.write(raw,np.asarray(v.infer(p['text'],voice=voice)),v.sample_rate)
        subprocess.run(['ffmpeg','-v','error','-y','-i',raw,'-af',f'atempo={SPEED}','-ar','48000','-b:a','192k','-map_metadata','-1',dst],check=True)
        print('ok',fn,flush=True)
# làm mới danh sách
man={}
for f in sorted(glob.glob(OUT+'/*.mp3')):
    b=os.path.basename(f); d=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]))
    man.setdefault(b.split('_')[0],[]).append({'file':'Long-tieng/'+b,'voice':re.sub(r'^.*_','',b[:-4]).replace('-',' '),'dur':round(d,1)})
json.dump(man,open(OUT+'/_danh-sach-tong.json','w'),ensure_ascii=False,indent=1)
