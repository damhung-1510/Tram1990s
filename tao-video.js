// Thanh "Tạo video" cho GHEP_THO_VIDEO.html. Cần chạy qua máy chủ: python3 tao_video.py → http://127.0.0.1:8787/
(() => {
  const S = { poem: null, voice: '', videos: [], music: '', vol: 1.0, busy: false, note: '' };
  let audio = {}, music = [], online = false;
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const base = p => p.split('/').pop();

  const style = document.createElement('style');
  style.textContent = `
  #tv{position:fixed;left:0;right:0;bottom:0;z-index:50;background:var(--card);border-top:2px solid var(--acc);padding:8px 14px;font-size:13px;box-shadow:0 -4px 18px rgba(0,0,0,.18)}
  #tv .r{display:flex;gap:10px;flex-wrap:wrap;align-items:center;max-width:960px;margin:0 auto 4px}
  #tv b{color:var(--acc)} #tv select{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:2px 6px;max-width:260px}
  #tv .go{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:6px 16px;font-weight:700;cursor:pointer;margin-left:auto}
  #tv .go:disabled{opacity:.35;cursor:not-allowed}
  #tv .bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden;max-width:960px;margin:2px auto}
  #tv .bar i{display:block;height:100%;width:0;background:var(--acc);transition:width .4s}
  #tv .vl{display:inline-flex;gap:4px;flex-wrap:wrap}
  #tv .vl span{background:var(--accbg);color:var(--acc);border-radius:6px;padding:1px 6px;cursor:pointer}
  #tv .msg{max-width:960px;margin:0 auto;color:var(--mut)} #tv .err{color:#d33}
  .tv-pick{border:1px solid var(--acc);background:var(--accbg);color:var(--acc);border-radius:8px;padding:1px 9px;cursor:pointer;font-size:12px}
  .tv-pick.on{background:var(--acc);color:#fff}
  .tv-cb{cursor:pointer;margin-right:6px;color:var(--acc)}
  .w{padding-bottom:150px}
  #tvM2{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center}
  #tvM2 .box{background:var(--card);border-radius:12px;width:min(960px,96vw);height:min(86vh,800px);display:flex;flex-direction:column;padding:12px 14px;box-shadow:0 8px 40px rgba(0,0,0,.4)}
  #tvM2 .top{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}
  #tvM2 select,#tvM2 input{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:3px 8px}
  #tvM2 .grid{overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));gap:8px;flex:1;align-content:start}
  #tvM2 .it{position:relative;cursor:pointer;border:2px solid transparent;border-radius:8px;overflow:hidden;background:var(--line)}
  #tvM2 .it.on{border-color:var(--acc)} #tvM2 .it img{display:block;width:100%;aspect-ratio:9/16;object-fit:cover}
  #tvM2 .it i{position:absolute;top:4px;left:4px;background:rgba(0,0,0,.65);color:#fff;border-radius:6px;padding:0 6px;font-style:normal;font-size:12px}
  #tvM2 .it .nm{font-size:10px;padding:2px 4px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  #tvM2 .it a{position:absolute;top:4px;right:4px;background:rgba(0,0,0,.65);color:#fff;border-radius:6px;padding:0 6px;font-size:12px;text-decoration:none}`;
  document.head.appendChild(style);

  const panel = document.createElement('div');
  panel.id = 'tv';
  panel.innerHTML = `
   <div class="r"><span>🎬 <b>Thơ:</b> <span id="tvP">chưa chọn</span></span>
     <span>🎙 <b>Giọng:</b> <select id="tvV"><option value="">—</option></select></span>
     <span>📄 <b>Template:</b> <span id="tvT">—</span></span>
     <span>🎞 <b>Clip:</b> <span class="vl" id="tvC">chưa chọn</span> <button class="tv-pick" id="tvAll">＋ Tất cả clip</button></span></div>
   <div class="r"><span>🎵 <b>Nhạc nền:</b> <select id="tvM"><option value="">— chọn nhạc —</option></select>
       <button class="tv-pick" id="tvMP">▶ nghe</button>
       <label>nhỏ <input type="range" id="tvVol" min="0.3" max="1.6" step="0.1" value="1"> to</label></span>
     <button class="tv-pick" id="tvReset" title="Bỏ chọn bài, giọng, clip, nhạc và đưa mọi thứ về mặc định" style="margin-left:auto">↺ Reset</button>
     <button class="go" id="tvGo" disabled style="margin-left:6px">Tạo video</button></div>
   <div class="bar"><i id="tvBar"></i></div><div class="msg" id="tvMsg">Chọn thơ, giọng đọc, clip và nhạc nền để bật nút Tạo video.</div>`;
  document.body.appendChild(panel);
  const prev = new Audio();

  function ready() {
    const miss = [];
    if (!S.poem) miss.push('thơ'); else if (!S.voice) miss.push('giọng đọc');
    if (!S.videos.length) miss.push('clip');
    if (!S.music) miss.push('nhạc nền');
    return miss;
  }
  function refresh() {
    const p = S.poem && findP(x => x.id === S.poem);
    $('#tvP').textContent = p ? `${p.id} · ${p.title}` : 'chưa chọn';
    const vs = S.poem ? (audio[S.poem] || []) : [];
    $('#tvV').innerHTML = vs.length ? vs.map(v => `<option value="${esc(v.file)}"${v.file === S.voice ? ' selected' : ''}>${esc(v.label)} · ${v.dur}s</option>`).join('')
      : `<option value="">${S.poem ? 'chưa có giọng đọc cho bài này' : '—'}</option>`;
    $('#tvC').innerHTML = S.videos.length ? S.videos.map((v, i) => `<span data-tvrm="${i}" title="Bấm để bỏ">${esc(base(v).replace(/^TramCamXuc_/, '').slice(0, 28))} ✕</span>`).join('') : 'chưa chọn';
    if (S.poem !== S.tplFor) {
      S.tplFor = S.poem; $('#tvT').textContent = S.poem ? '...' : '—';
      if (S.poem) fetch('/api/template?poemId=' + encodeURIComponent(S.poem)).then(r => r.json()).then(j => {
        $('#tvT').textContent = j.label ? `${j.label} (${j.why})${j.ok ? '' : ' ⚠ thiếu trong Concat'}` : '—'; }).catch(() => {});
    }
    const miss = ready();
    $('#tvGo').disabled = S.busy || !online || miss.length > 0;
    $('#tvReset').disabled = S.busy;
    if (!S.busy && S.note) { $('#tvMsg').className = 'msg'; $('#tvMsg').innerHTML = S.note; }
    else if (!S.busy) {
      $('#tvMsg').className = 'msg';
      $('#tvMsg').textContent = !online ? 'Chưa kết nối máy chủ: chạy python3 tao_video.py rồi mở http://127.0.0.1:8787/'
        : miss.length ? 'Còn thiếu: ' + miss.join(', ') : 'Sẵn sàng. Bấm Tạo video, file lưu vào Vid_completed.';
    }
    document.querySelectorAll('.tv-pick[data-tv-poem]').forEach(b => b.classList.toggle('on', b.dataset.tvPoem === S.poem));
    document.querySelectorAll('.tv-cb').forEach(c => { const w = S.videos.includes(c.dataset.path) ? '☑' : '☐'; if (c.textContent !== w) c.textContent = w; });
  }

  function decorate() {
    document.querySelectorAll('#list .card').forEach(card => {
      const id = card.querySelector('.id')?.textContent;
      const hd = card.querySelector('.hd');
      if (id && hd && !hd.querySelector('.tv-pick')) {
        const b = document.createElement('button');
        b.className = 'tv-pick'; b.dataset.tvPoem = id; b.textContent = '🎬 Chọn bài này';
        hd.insertBefore(b, hd.querySelector('label'));
      }
      card.querySelectorAll('.cl div[data-copy]').forEach(d => {
        if (!d.querySelector('.tv-cb')) {
          const s = document.createElement('span');
          s.className = 'tv-cb'; s.dataset.path = d.dataset.copy; s.textContent = '☐';
          d.prepend(s);
        }
      });
      card.querySelectorAll('.pick').forEach(d => {
        if (!d.querySelector('.tv-cb')) {
          const s = document.createElement('span');
          s.className = 'tv-cb'; s.dataset.path = d.textContent.trim(); s.textContent = '☐';
          d.prepend(s);
        }
      });
    });
    refresh();
  }

  document.addEventListener('click', e => {
    const t = e.target.closest('.tv-pick[data-tv-poem],.tv-cb,[data-tvrm]');
    if (!t) return;
    e.preventDefault(); e.stopPropagation(); S.note = '';
    if (t.dataset.tvPoem) {
      S.poem = t.dataset.tvPoem;
      const vs = audio[S.poem] || [];
      S.voice = (vs.find(v => v.hook) || vs[0] || {}).file || '';
    } else if (t.classList.contains('tv-cb')) {
      const i = S.videos.indexOf(t.dataset.path);
      if (i >= 0) S.videos.splice(i, 1); else S.videos.push(t.dataset.path);
    } else if (t.dataset.tvrm !== undefined) S.videos.splice(+t.dataset.tvrm, 1);
    refresh();
  }, true);

  $('#tvV').onchange = e => { S.voice = e.target.value; refresh(); };
  $('#tvM').onchange = e => { S.music = e.target.value; prev.pause(); refresh(); };
  $('#tvVol').oninput = e => { S.vol = +e.target.value; };
  $('#tvMP').onclick = () => {
    if (!S.music) return;
    if (!prev.paused) { prev.pause(); $('#tvMP').textContent = '▶ nghe'; return; }
    prev.src = encodeURI('/' + S.music); prev.play(); $('#tvMP').textContent = '⏸ dừng';
  };
  prev.onended = () => { $('#tvMP').textContent = '▶ nghe'; };

  $('#tvReset').onclick = () => {
    if (S.busy) return;          // đang tạo video thì không reset
    prev.pause(); $('#tvMP').textContent = '▶ nghe';
    Object.assign(S, { poem: null, voice: '', videos: [], music: '', vol: 1.0, note: '', tplFor: null });
    $('#tvM').value = ''; $('#tvVol').value = '1'; $('#tvT').textContent = '—';
    $('#tvBar').style.width = '0';
    refresh();
  };

  $('#tvGo').onclick = async () => {
    S.busy = true; refresh();
    const msg = $('#tvMsg'); msg.className = 'msg'; msg.textContent = 'Gửi yêu cầu...'; $('#tvBar').style.width = '1%';
    try {
      const r = await fetch('/api/render', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ poemId: S.poem, voice: S.voice, videos: S.videos, music: S.music, musicVolume: S.vol }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || 'lỗi');
      for (;;) {
        await new Promise(res => setTimeout(res, 1500));
        const s = await (await fetch('/api/job/' + j.job)).json();
        $('#tvBar').style.width = (s.pct || 0) + '%';
        msg.textContent = `${s.message || ''} ${s.pct || 0}%`;
        if (s.status === 'done') {
          S.note = `✅ Xong: <a href="/${encodeURI(s.output)}" target="_blank">${esc(s.output)}</a> (đã lưu trong thư mục Vid_completed)`;
          break;
        }
        if (s.status === 'error') throw new Error(s.message);
      }
    } catch (err) { msg.className = 'msg err'; msg.textContent = 'Lỗi: ' + err.message; $('#tvBar').style.width = '0'; }
    S.busy = false; refresh();
  };

  // ── cửa sổ chọn clip từ tất cả thư mục ──
  let allClips = null, folderSel = '', qSel = '';
  const modal = document.createElement('div');
  modal.id = 'tvM2';
  modal.innerHTML = `<div class="box"><div class="top"><b>🎞 Chọn clip từ tất cả thư mục</b>
      <select id="tvF"></select><input id="tvQ" type="search" placeholder="Tìm tên clip…" style="flex:1;min-width:140px">
      <span id="tvN" style="color:var(--mut)"></span><button class="tv-pick" id="tvDone">Xong</button></div>
    <div class="grid" id="tvG"></div></div>`;
  document.body.appendChild(modal);
  function drawGrid() {
    if (!allClips) return;
    const q = qSel.toLowerCase(), items = [];
    for (const [f, L] of Object.entries(allClips)) if (!folderSel || f === folderSel)
      for (const c of L) if (!q || c.name.toLowerCase().includes(q)) items.push(c);
    $('#tvN').textContent = `${items.length} clip · đã chọn ${S.videos.length}`;
    $('#tvG').innerHTML = items.map(c => `<div class="it${S.videos.includes(c.file) ? ' on' : ''}" data-file="${esc(c.file)}">
      <img loading="lazy" src="/api/thumb?path=${encodeURIComponent(c.file)}" alt=""><i>${S.videos.includes(c.file) ? '☑ ' + (S.videos.indexOf(c.file) + 1) : '☐'}</i>
      <a href="/${encodeURI(c.file)}" target="_blank" data-tvprev title="Xem clip">▶</a><div class="nm" title="${esc(c.name)}">${esc(c.name)}</div></div>`).join('');
  }
  $('#tvAll').onclick = async () => {
    modal.style.display = 'flex';
    if (!allClips) {
      allClips = await (await fetch('/api/clips')).json();
      $('#tvF').innerHTML = '<option value="">Tất cả thư mục</option>' + Object.entries(allClips).map(([f, L]) => `<option value="${esc(f)}">${esc(f)} (${L.length})</option>`).join('');
    }
    drawGrid();
  };
  $('#tvF').onchange = e => { folderSel = e.target.value; drawGrid(); };
  $('#tvQ').oninput = e => { qSel = e.target.value; drawGrid(); };
  $('#tvDone').onclick = () => { modal.style.display = 'none'; };
  modal.addEventListener('click', e => {
    if (e.target === modal) { modal.style.display = 'none'; return; }
    if (e.target.closest('[data-tvprev]')) return;            // ▶ mở clip ở tab mới
    const it = e.target.closest('.it'); if (!it) return;
    const f = it.dataset.file, i = S.videos.indexOf(f);
    if (i >= 0) S.videos.splice(i, 1); else S.videos.push(f);
    S.note = ''; refresh(); drawGrid();
  });

  (async () => {
    try {
      online = (await fetch('/api/ping')).ok;
      audio = await (await fetch('/api/audio')).json();
      music = await (await fetch('/api/music')).json();
      const groups = {};
      music.forEach(m => (groups[m.folder] = groups[m.folder] || []).push(m));
      $('#tvM').innerHTML = '<option value="">— chọn nhạc —</option>' + Object.entries(groups).map(([g, ms]) =>
        `<optgroup label="${esc(g)}">${ms.map(m => `<option value="${esc(m.file)}">${esc(m.name.replace(/^Pixabay_/, '').slice(0, 44))} · ${m.dur}s</option>`).join('')}</optgroup>`).join('');
    } catch (e) { online = false; }
    new MutationObserver(decorate).observe($('#list'), { childList: true, subtree: true });
    decorate();
  })();
})();
