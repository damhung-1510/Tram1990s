// Thanh "Tạo video" cho GHEP_THO_VIDEO.html. Cần chạy qua máy chủ: python3 tao_video.py → http://127.0.0.1:8787/
(() => {
  const S = { poem: null, voice: '', videos: [], music: '', template: '', suggestedTemplate: '', vol: 1.0, busy: false, note: '' };
  let audio = {}, music = [], templates = [], online = false;
  let ttsVoices = [], ttsPoems = new Set(), ttsConfigured = false, ttsBusy = false, ttsTarget = null;
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const base = p => p.split('/').pop();
  const isImage = () => S.template === 'anh-tho-giay-hoai-co';
  const isStillBackground = () => S.template === 'tho-reels-anh-mo';
  const isRawVideo = () => S.template === 'trich-dan-khong-chu';
  const isQuote = p => (p || (S.poem && findP(S.poem)))?.kind?.startsWith('Trích dẫn');
  const clipMeta = new Map();
  const seconds = n => n.toLocaleString('vi-VN', { maximumFractionDigits: 1 });
  function clipTarget(p) {
    p = p || (S.poem && findP(S.poem));
    const recording = p && (audio[p.id] || []).find(v => v.file === S.voice);
    if (recording) return { seconds: recording.dur + (isQuote(p) ? 3 : 0.5 + (['tho-reels-doc-nhanh', 'tho-reels-anh-mo'].includes(S.template) ? 4 : 3)), estimated: false };
    return { seconds: p?.est || Math.max(1, ...D.poems.filter(p => p.kind === 'Trích dẫn Ngày mới').map(p => p.est || 0)), estimated: true };
  }
  function clipAssessment(file, p) {
    const c = clipMeta.get(file);
    if (!c) return null;
    if (c.error) return { short: true, text: '⚠ Không đọc được clip', title: c.error };
    if (!Number.isFinite(c.dur) || c.dur <= 0) return null;
    const target = clipTarget(p), capacity = c.dur / c.min_speed;
    const short = capacity + 1e-8 < target.seconds;
    const speed = Math.min(c.max_speed, c.dur / target.seconds);
    const text = short ? `⚠ ${seconds(c.dur)}s · quá ngắn dùng riêng`
      : `${seconds(c.dur)}s · slow ${speed.toFixed(2)}× → ${target.estimated ? '≈ ' : ''}${seconds(target.seconds)}s`;
    return { short, text, title: short
      ? `Ở ${c.min_speed}× chỉ được ${seconds(capacity)}s; ${target.estimated ? 'ước tính cần' : 'cần'} ${seconds(target.seconds)}s. Có thể ghép thêm clip.`
      : `${target.estimated ? 'Ước tính; sẽ tính lại theo file giọng đọc.' : 'Theo giọng đọc đã chọn.'} Phần hình dư sẽ được cắt.` };
  }
  window.tvClipUsable = (file, p) => !clipAssessment(file, p)?.short;
  function updateTimingNote() {
    const el = $('#tvTiming');
    const visible = S.poem && isQuote() && !isImage() && !isStillBackground();
    el.hidden = !visible;
    if (!visible) return;
    const target = clipTarget();
    let text = `${target.estimated ? 'Dự kiến' : 'Giọng đọc + 3s'}: ${seconds(target.seconds)}s. Tự slow 0,5–0,85×; clip dư sẽ cắt vừa đủ.`;
    const known = S.videos.map(f => clipMeta.get(f));
    if (known.length && known.every(c => Number.isFinite(c?.dur))) {
      const capacity = known.reduce((n, c) => n + c.dur / c.min_speed, 0);
      if (capacity < target.seconds) text += ` ⚠ Các clip đã chọn chỉ kéo được ${seconds(capacity)}s; cần ghép thêm clip.`;
    }
    if (target.estimated) text += ' Chưa có giọng đọc; sẽ tính lại khi lồng tiếng xong.';
    if (el.textContent !== text) el.textContent = text;
  }
  function markVideoDone() {
    if (isImage() || !S.poem) return;
    try {
      if (typeof used === 'object') {
        used[S.poem] = true;
        if (typeof save === 'function') save();
        if (typeof render === 'function') render();
      }
    } catch (e) {}
  }

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
  .w{padding-bottom:210px}
  #tvM2{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center}
  #tvM2 .box{background:var(--card);border-radius:12px;width:min(960px,96vw);height:min(86vh,800px);display:flex;flex-direction:column;padding:12px 14px;box-shadow:0 8px 40px rgba(0,0,0,.4)}
  #tvM2 .top{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}
  #tvM2 select,#tvM2 input{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:3px 8px}
  #tvM2 .grid{overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));gap:8px;flex:1;align-content:start}
  #tvM2 .it{position:relative;cursor:pointer;border:2px solid transparent;border-radius:8px;overflow:hidden;background:var(--line)}
  #tvM2 .it.on{border-color:var(--acc)} #tvM2 .it img{display:block;width:100%;aspect-ratio:9/16;object-fit:cover}
  #tvM2 .it i{position:absolute;top:4px;left:4px;background:rgba(0,0,0,.65);color:#fff;border-radius:6px;padding:0 6px;font-style:normal;font-size:12px}
  #tvM2 .it .nm{font-size:10px;padding:2px 4px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  #tvM2 .it .fit,.tv-fit{font-size:11px;color:var(--mut)}
  #tvM2 .it .fit{padding:3px 4px;line-height:1.3}
  #tvM2 .it .fit.short,.tv-fit.short{color:var(--acc);font-weight:600}
  .tv-fit{margin-left:8px;font-family:system-ui,sans-serif}
  #tvTiming{max-width:960px;margin:3px auto;font-size:12px;color:var(--mut)}
  #tvM2 .it a{position:absolute;top:4px;right:4px;background:rgba(0,0,0,.65);color:#fff;border-radius:6px;padding:0 6px;font-size:12px;text-decoration:none}
  .tv-tts{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0;font-size:13px}
  .tv-tts select{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:4px}
  .tv-tts button:disabled{opacity:.5;cursor:wait}
  #tvSpeech{color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:12px;width:min(620px,94vw);max-height:85vh}
  #tvSpeech::backdrop{background:rgba(0,0,0,.6)}
  #tvSpeech pre{white-space:pre-wrap;max-height:40vh;overflow:auto;font:inherit;padding:12px;background:var(--bg)}
  #tvSpeech .actions{display:flex;gap:10px;justify-content:flex-end}`;
  document.head.appendChild(style);

  const panel = document.createElement('div');
  panel.id = 'tv';
  panel.innerHTML = `
   <div class="r"><span>🎬 <b>Thơ:</b> <span id="tvP">chưa chọn</span></span>
     <span id="tvVoiceGroup">🎙 <b>Giọng:</b> <select id="tvV"><option value="">—</option></select></span>
     <span>📄 <b>Template:</b> <select id="tvT"><option value="">—</option></select></span>
     <span id="tvClipGroup">🎞 <b id="tvMediaLabel">Clip:</b> <span class="vl" id="tvC">chưa chọn</span> <button class="tv-pick" id="tvAll">＋ Tất cả clip</button></span></div>
   <div class="r"><span id="tvMusicGroup">🎵 <b id="tvMusicLabel">Nhạc nền:</b> <select id="tvM"><option value="">— chọn nhạc —</option></select>
       <button class="tv-pick" id="tvMP">▶ nghe nhạc</button>
       <label>nhỏ <input type="range" id="tvVol" min="0.05" max="1" step="0.05" value="1"> to nhất (≈ 15 dB dưới giọng)</label>
       <span id="tvDb" style="color:var(--mut)"></span></span>
     <span id="tvPreviewGroup"><button class="tv-pick" id="tvVP">▶ nghe giọng</button> <button class="tv-pick" id="tvMix">🎧 Nghe thử giọng + nhạc</button></span>
     <button class="tv-pick" id="tvReset" title="Bỏ chọn bài, giọng, clip, nhạc và đưa mọi thứ về mặc định" style="margin-left:auto">↺ Reset</button>
     <button class="go" id="tvGo" disabled style="margin-left:6px">Tạo video</button></div>
   <div id="tvTiming" hidden></div><div class="bar"><i id="tvBar"></i></div><div class="msg" id="tvMsg">Chọn thơ, giọng đọc, clip và nhạc nền để bật nút Tạo video.</div>`;
  document.body.appendChild(panel);
  const prev = new Audio(), vA = new Audio(), mA = new Audio();
  const speech = document.createElement('dialog');
  speech.id = 'tvSpeech';
  speech.innerHTML = `<h3>Lồng tiếng ElevenLabs</h3><p id="tvSpeechInfo"></p><pre id="tvSpeechText"></pre>
    <p>Nội dung trên sẽ được gửi tới ElevenLabs và dùng credit của tài khoản.</p>
    <p id="tvSpeechStatus" role="status" aria-live="polite"></p>
    <div class="actions"><button class="tv-pick" id="tvSpeechClose">Đóng</button>
    <button class="act" id="tvSpeechGo">Tạo giọng đọc</button></div>`;
  document.body.appendChild(speech);

  function syncAudio() {
    D.poems.concat(D.combos).forEach(p => {
      const items = audio[p.id] || [];
      p.done = items.length > 0;
      p.audio = items.map(a => ({ file: a.file, voice: a.label, dur: a.dur }));
    });
    render();
  }
  function decorateSpeech(card, id) {
    const needed = ttsPoems.has(id) && !(audio[id] || []).length;
    let row = card.querySelector('.tv-tts');
    if (!needed) { row?.remove(); return; }
    if (!row) {
      row = document.createElement('div'); row.className = 'tv-tts';
      const p = findP(id), preferred = p?.kind?.includes('Trích dẫn') ? 'O4GJDPajhRb6MxWUMf7V' : 'qn4pQo7kIjvZ1a7SowZE';
      row.innerHTML = `<label>Giọng lồng <select aria-label="Giọng lồng tiếng cho ${esc(id)}">${ttsVoices.map(v =>
        `<option value="${esc(v.id)}"${v.id === preferred ? ' selected' : ''}>${esc(v.name)}</option>`).join('')}</select></label>
        <button class="act" data-tts="${esc(id)}">🎙 Lồng tiếng</button><span class="tv-tts-note"></span>`;
      card.querySelector('.hd').after(row);
    }
    row.querySelector('button').disabled = !online || !ttsConfigured || ttsBusy;
    const note = row.querySelector('.tv-tts-note');
    const message = !ttsConfigured ? 'Chưa lưu API key ElevenLabs' : ttsBusy ? 'Đang lồng tiếng…' : '';
    if (note.textContent !== message) note.textContent = message;
  }
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-tts]');
    if (!b || ttsBusy) return;
    e.preventDefault();
    const p = findP(b.dataset.tts), voiceId = b.closest('.tv-tts').querySelector('select').value;
    ttsTarget = { poemId: p.id, voiceId };
    $('#tvSpeechInfo').textContent = `${p.id} · ${p.title} · ${ttsVoices.find(v => v.id === voiceId)?.name} · ${p.tts.length} ký tự`;
    $('#tvSpeechText').textContent = p.tts;
    $('#tvSpeechStatus').textContent = '';
    $('#tvSpeechGo').disabled = false;
    speech.showModal();
  });
  $('#tvSpeechClose').onclick = () => speech.close();
  $('#tvSpeechGo').onclick = async () => {
    if (ttsBusy || !ttsTarget) return;
    const target = { ...ttsTarget };
    ttsBusy = true; $('#tvSpeechGo').disabled = true; decorate();
    const status = $('#tvSpeechStatus');
    status.textContent = 'Đang gửi yêu cầu…';
    try {
      const r = await fetch('/api/dub', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(target) });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || 'Không gửi được yêu cầu');
      for (;;) {
        await new Promise(resolve => setTimeout(resolve, 1500));
        const response = await fetch('/api/dub/job/' + j.job);
        const job = await response.json();
        if (!response.ok || job.status === 'error') throw new Error(job.message || 'Không đọc được trạng thái');
        status.textContent = job.message;
        if (job.status === 'done') {
          audio = await (await fetch('/api/audio')).json();
          if (S.poem !== target.poemId) S.template = '';
          S.poem = target.poemId;
          S.voice = (audio[target.poemId] || [])[0]?.file || '';
          syncAudio(); refresh();
          status.textContent = 'Đã lồng tiếng. Bài đã được chọn để ghép video.';
          break;
        }
      }
    } catch (err) { status.textContent = 'Lỗi: ' + err.message; }
    finally { ttsBusy = false; $('#tvSpeechGo').disabled = false; decorate(); }
  };


  let info = null, mixing = false, startT = null, fadeT = null;
  const effGain = () => (info ? info.gain : 0.1) * S.vol;
  function showDb() {
    $('#tvDb').textContent = info ? `≈ ${Math.round(info.below_db - 20 * Math.log10(S.vol))} dB dưới giọng` : '';
  }
  async function loadInfo() {
    if (!S.voice || !S.music) { info = null; showDb(); return; }
    const key = S.voice + '|' + S.music;
    if (info && info.key === key) return;
    try {
      const j = await (await fetch('/api/mixinfo?voice=' + encodeURIComponent(S.voice) + '&music=' + encodeURIComponent(S.music))).json();
      info = j.error ? null : { key, ...j };
    } catch (e) { info = null; }
    showDb();
  }
  function stopAll() {
    [prev, vA, mA].forEach(a => a.pause());
    clearTimeout(startT); clearInterval(fadeT); stopMix();
    $('#tvMP').textContent = '▶ nghe nhạc'; $('#tvVP').textContent = '▶ nghe giọng'; $('#tvMix').textContent = '🎧 Nghe thử giọng + nhạc';
  }
  $('#tvVP').onclick = () => {
    if (!vA.paused && !mixing) { stopAll(); return; }
    stopAll();
    if (!S.voice) { $('#tvMsg').textContent = 'Chọn bài và giọng đọc trước.'; return; }
    vA.src = encodeURI('/' + S.voice); vA.currentTime = 0; vA.volume = 1; vA.play(); $('#tvVP').textContent = '⏸ dừng giọng';
    vA.onended = stopAll;
  };
  // Nghe thử giọng + nhạc bằng Web Audio: chạy được ngay khi bấm, chỉnh to nhỏ trực tiếp, không bị trình duyệt chặn
  let ac = null, srcV = null, srcM = null, gM = null, mixEnd = 0, endT = null;
  const bufCache = {};
  async function getBuf(rel) {
    if (!bufCache[rel]) bufCache[rel] = ac.decodeAudioData(await (await fetch(encodeURI('/' + rel))).arrayBuffer());
    return bufCache[rel];
  }
  function stopMix() {
    clearTimeout(endT);
    for (const n of [srcV, srcM]) { try { n && n.stop(); } catch (e) {} }
    srcV = srcM = gM = null; mixing = false;
  }
  function applyMixGain() {            // đổi âm lượng nhạc ngay khi kéo thanh
    if (!mixing || !gM) return;
    const g = effGain(), now = ac.currentTime;
    gM.gain.cancelScheduledValues(now);
    gM.gain.setValueAtTime(g, now);
    if (now < mixEnd) { gM.gain.setValueAtTime(g, mixEnd); gM.gain.linearRampToValueAtTime(0, mixEnd + 3); }
  }
  window.TV_DEBUG = () => ({ state: ac && ac.state, mixing, t: ac && +ac.currentTime.toFixed(2), end: +mixEnd.toFixed(2), gain: gM ? +gM.gain.value.toFixed(4) : null, eff: +effGain().toFixed(4) });
  $('#tvMix').onclick = async () => {
    if (mixing) { stopAll(); return; }
    stopAll();
    if (!S.voice || !S.music) { $('#tvMsg').textContent = 'Chọn giọng đọc và nhạc nền để nghe thử cả hai.'; return; }
    ac = ac || new (window.AudioContext || window.webkitAudioContext)();
    ac.resume();                                            // phải gọi ngay trong lúc bấm
    $('#tvMix').textContent = '⏳ đang tải…'; mixing = true;
    try {
      const [bv, bm] = await Promise.all([getBuf(S.voice), getBuf(S.music), loadInfo()]);
      if (!mixing) return;                                  // người dùng đã bấm dừng trong lúc tải
      const t0 = ac.currentTime + 0.05;
      gM = ac.createGain(); gM.gain.value = effGain();
      srcM = ac.createBufferSource(); srcM.buffer = bm; srcM.loop = true; srcM.connect(gM); gM.connect(ac.destination); srcM.start(t0);
      const voiceLead = isQuote() ? 0 : 0.5;
      srcV = ac.createBufferSource(); srcV.buffer = bv; srcV.connect(ac.destination); srcV.start(t0 + voiceLead);
      mixEnd = t0 + voiceLead + bv.duration;
      gM.gain.setValueAtTime(effGain(), mixEnd); gM.gain.linearRampToValueAtTime(0, mixEnd + 3);               // 3 giây cuối nhạc nhỏ dần
      srcM.stop(mixEnd + 3);
      endT = setTimeout(stopAll, (mixEnd + 3.2 - ac.currentTime) * 1000);
      $('#tvMix').textContent = '⏸ dừng nghe thử';
    } catch (e) { stopAll(); $('#tvMsg').textContent = 'Không phát được: ' + e.message; }
  };

  function ready() {
    const miss = [];
    if (!S.poem) miss.push('thơ');
    if (!S.template) miss.push('template');
    if (isImage()) {
      const p = S.poem && findP(x => x.id === S.poem);
      const lines = p ? p.text.split('\n').filter(x => x.trim()).length : 0;
      if (lines > 10) miss.push(`bài có ${lines} dòng, ảnh chỉ nhận tối đa 10 dòng`);
      return miss;
    }
    if (S.poem && !S.voice) miss.push('giọng đọc');
    if (!S.videos.length) miss.push(isStillBackground() ? 'ảnh nền' : 'clip');
    if (isQuote() && !isStillBackground() && S.voice && S.videos.length) {
      const known = S.videos.map(f => clipMeta.get(f));
      if (known.some(c => c?.error)) miss.push('thay clip không đọc được');
      else if (known.every(c => Number.isFinite(c?.dur)) && known.reduce((n, c) => n + c.dur / c.min_speed, 0) < clipTarget().seconds)
        miss.push('clip dài hơn hoặc ghép thêm clip (không tự lặp cảnh)');
    }
    if (!S.music && !isRawVideo()) miss.push('nhạc nền');
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
      S.tplFor = S.poem; S.template = ''; S.suggestedTemplate = ''; $('#tvT').innerHTML = '<option value="">...</option>';
      const poemId = S.poem;
      if (poemId) fetch('/api/template?poemId=' + encodeURIComponent(poemId)).then(r => r.json()).then(j => {
        if (S.poem !== poemId) return;
        S.suggestedTemplate = j.template || '';
        S.template = S.suggestedTemplate;
        $('#tvT').innerHTML = templates.map(t => `<option value="${esc(t.template)}"${t.template === S.template ? ' selected' : ''}${t.ok ? '' : ' disabled'}>${esc(t.label)}${t.template === S.suggestedTemplate ? ' · Gợi ý' : ''}${t.ok ? '' : ' · thiếu template'}</option>`).join('');
        S.note = j.label ? `Template gợi ý: ${j.label} · ${j.why}. Bạn có thể đổi trong danh sách.` : '';
        refresh();
      }).catch(() => {});
    }
    loadInfo();
    const imageMode = isImage();
    const stillMode = isStillBackground();
    $('#tvMusicLabel').textContent = isRawVideo() ? 'Nhạc nền (tùy chọn):' : 'Nhạc nền:';
    $('#tvM').options[0].textContent = isRawVideo() ? '— không nhạc nền —' : '— chọn nhạc —';
    updateTimingNote();
    $('#tvMediaLabel').textContent = stillMode ? 'Ảnh nền:' : 'Clip:';
    $('#tvAll').textContent = stillMode ? '＋ Chọn ảnh' : '＋ Tất cả clip';
    const miss = ready();
    $('#tvGo').textContent = imageMode ? 'Ghép ảnh' : 'Tạo video';
    $('#pageTitle').textContent = imageMode ? 'Ghép Thơ – Ảnh' : 'Ghép Thơ – Video';
    $('#pageSub').textContent = imageMode
      ? 'Chọn một bài thơ tối đa 10 dòng và bấm Ghép ảnh để xuất PNG 4K.'
      : 'Chọn mood → chọn bài thơ → lấy clip gợi ý (🎲 ngẫu nhiên hoặc bấm tên thư mục để xem clip). Bấm vào đường dẫn để sao chép.';
    document.title = imageMode ? 'Ghép Thơ – Ảnh' : 'Ghép Thơ – Video';
    for (const id of ['#tvVoiceGroup', '#tvClipGroup', '#tvMusicGroup', '#tvPreviewGroup'])
      $(id).style.display = imageMode ? 'none' : '';
    for (const el of [$('#tvV'), $('#tvM'), $('#tvVol'), $('#tvAll'), $('#tvMP'), $('#tvVP'), $('#tvMix')]) el.disabled = imageMode || S.busy;
    $('#tvGo').disabled = S.busy || !online || miss.length > 0;
    $('#tvReset').disabled = S.busy;
    if (!S.busy && S.renderError) { $('#tvMsg').className = 'msg err'; $('#tvMsg').textContent = S.renderError; }
    else if (!S.busy && S.note) { $('#tvMsg').className = 'msg'; $('#tvMsg').innerHTML = S.note; }
    else if (!S.busy) {
      $('#tvMsg').className = 'msg';
      $('#tvMsg').textContent = !online ? 'Chưa kết nối máy chủ: chạy python3 tao_video.py rồi mở http://127.0.0.1:8787/'
        : miss.length ? 'Còn thiếu: ' + miss.join(', ')
        : imageMode ? 'Chế độ ghép ảnh 4K. Bấm Ghép ảnh, file lưu vào Anh_completed.'
        : 'Sẵn sàng. Bấm Tạo video, file lưu vào Vid_completed.';
    }
    document.querySelectorAll('.tv-pick[data-tv-poem]').forEach(b => b.classList.toggle('on', b.dataset.tvPoem === S.poem));
    document.querySelectorAll('.tv-cb').forEach(c => { const w = S.videos.includes(c.dataset.path) ? '☑' : '☐'; if (c.textContent !== w) c.textContent = w; });
  }

  function decorate() {
    document.querySelectorAll('#list .card').forEach(card => {
      const id = card.querySelector('.id')?.textContent;
      const hd = card.querySelector('.hd');
      if (id && hd) decorateSpeech(card, id);
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
      card.querySelectorAll('.cl div[data-copy],.pick').forEach(d => {
        const file = d.dataset.copy || d.querySelector('.tv-cb')?.dataset.path;
        const fit = file && clipAssessment(file, findP(id));
        let note = d.querySelector('.tv-fit');
        if (!fit) { note?.remove(); return; }
        if (!note) { note = document.createElement('span'); note.className = 'tv-fit'; d.appendChild(note); }
        if (note.textContent !== fit.text) note.textContent = fit.text;
        note.classList.toggle('short', fit.short); note.title = fit.title;
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
      if (isStillBackground()) { S.note = 'Template Ảnh Mờ: bấm “Chọn ảnh” để chọn một ảnh nền.'; refresh(); return; }
      const i = S.videos.indexOf(t.dataset.path);
      if (i >= 0) S.videos.splice(i, 1); else S.videos.push(t.dataset.path);
    } else if (t.dataset.tvrm !== undefined) S.videos.splice(+t.dataset.tvrm, 1);
    refresh();
  }, true);

  $('#tvV').onchange = e => { S.voice = e.target.value; decorate(); drawGrid(); };
  $('#tvT').onchange = e => {
    const wasStill = isStillBackground();
    S.template = e.target.value;
    if (wasStill !== isStillBackground()) S.videos = [];
    const chosen = templates.find(t => t.template === S.template);
    const suggested = templates.find(t => t.template === S.suggestedTemplate);
    S.note = S.template === S.suggestedTemplate
      ? `Đang dùng template gợi ý: ${chosen?.label || S.template}.`
      : `Đã chọn: ${chosen?.label || S.template}. Hệ thống sẽ dùng lựa chọn này thay cho gợi ý ${suggested?.label || S.suggestedTemplate}.`;
    refresh(); drawGrid();
  };
  $('#tvM').onchange = e => { S.music = e.target.value; stopAll(); refresh(); };
  $('#tvVol').oninput = e => { S.vol = +e.target.value; showDb(); applyMixGain(); };
  $('#tvMP').onclick = () => {
    if (!S.music) return;
    if (!prev.paused) { stopAll(); return; }
    stopAll(); prev.src = encodeURI('/' + S.music); prev.play(); $('#tvMP').textContent = '⏸ dừng nhạc';
  };
  prev.onended = stopAll;

  $('#tvReset').onclick = () => {
    if (S.busy) return;          // đang tạo video thì không reset
    stopAll();
    Object.assign(S, { poem: null, voice: '', videos: [], music: '', template: '', suggestedTemplate: '', vol: 1.0, note: '', renderError: '', tplFor: null });
    $('#tvM').value = ''; $('#tvVol').value = '1'; $('#tvT').innerHTML = '<option value="">—</option>'; info = null; showDb();
    $('#tvBar').style.width = '0';
    refresh();
  };

  $('#tvGo').onclick = async () => {
    S.busy = true; S.renderError = ''; S.note = ''; refresh();
    const msg = $('#tvMsg'); msg.className = 'msg'; msg.textContent = 'Gửi yêu cầu...'; $('#tvBar').style.width = '1%';
    try {
      const r = await fetch('/api/render', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ poemId: S.poem, voice: S.voice, videos: S.videos, music: S.music,
          template: S.template, musicVolume: S.vol }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || 'lỗi');
      for (;;) {
        await new Promise(res => setTimeout(res, 1500));
        const response = await fetch('/api/job/' + j.job);
        const s = await response.json();
        if (!response.ok) throw new Error(s.message || 'Không đọc được trạng thái xuất video');
        $('#tvBar').style.width = (s.pct || 0) + '%';
        msg.textContent = `${s.message || ''} ${s.pct || 0}%`;
        if (s.status === 'done') {
          const folder = isImage() ? 'Anh_completed' : 'Vid_completed';
          markVideoDone();
          S.note = `✅ Xong: <a href="/${encodeURI(s.output)}" target="_blank">${esc(s.output)}</a> (đã lưu trong thư mục ${folder})`;
          break;
        }
        if (s.status === 'error') throw new Error(s.message);
      }
    } catch (err) { S.renderError = 'Lỗi: ' + err.message; $('#tvBar').style.width = '0'; }
    S.busy = false; refresh();
  };

  // ── cửa sổ chọn clip từ tất cả thư mục ──
  let allClips = null, folderSel = '', qSel = '';
  async function loadClips() {
    const response = await fetch('/api/clips?refresh=' + Date.now());
    if (!response.ok) throw new Error('Không tải được danh sách clip');
    allClips = await response.json();
    clipMeta.clear();
    for (const items of Object.values(allClips)) for (const c of items) if (c.dur || c.error) clipMeta.set(c.file, c);
  }
  const modal = document.createElement('div');
  modal.id = 'tvM2';
  modal.innerHTML = `<div class="box"><div class="top"><b id="tvPickerTitle">🎞 Chọn clip từ tất cả thư mục</b>
      <select id="tvF"></select><input id="tvQ" type="search" placeholder="Tìm tên clip…" style="flex:1;min-width:140px">
      <span id="tvN" style="color:var(--mut)"></span><button class="tv-pick" id="tvDone">Xong</button></div>
    <div class="grid" id="tvG"></div></div>`;
  document.body.appendChild(modal);
  function drawGrid() {
    if (!allClips) return;
    const q = qSel.toLowerCase(), items = [], wanted = isStillBackground() ? 'image' : 'video';
    for (const [f, L] of Object.entries(allClips)) if (!folderSel || f === folderSel)
      for (const c of L) if (c.kind === wanted && (!q || c.name.toLowerCase().includes(q))) items.push(c);
    $('#tvN').textContent = `${items.length} ${wanted === 'image' ? 'ảnh' : 'clip'} · đã chọn ${S.videos.length}`;
    $('#tvG').innerHTML = items.map(c => `<div class="it${S.videos.includes(c.file) ? ' on' : ''}" data-file="${esc(c.file)}">
      <img loading="lazy" src="/api/thumb?path=${encodeURIComponent(c.file)}" alt=""><i>${S.videos.includes(c.file) ? '☑ ' + (S.videos.indexOf(c.file) + 1) : '☐'}</i>
      <a href="/${encodeURI(c.file)}" target="_blank" data-tvprev title="Xem clip">▶</a><div class="nm" title="${esc(c.name)}">${esc(c.name)}</div>${(() => {
        const fit = clipAssessment(c.file);
        return fit ? `<div class="fit${fit.short ? ' short' : ''}" title="${esc(fit.title)}">${esc(fit.text)}</div>` : '';
      })()}</div>`).join('');
  }
  $('#tvAll').onclick = async () => {
    modal.style.display = 'flex';
    // Quét lại Videos/ và Vid/ mỗi lần mở, tính theo bài/giọng đọc đang chọn.
    try { await loadClips(); }
    catch (err) { $('#tvG').textContent = err.message; return; }
    decorate();
    const wanted = isStillBackground() ? 'image' : 'video';
    $('#tvPickerTitle').textContent = wanted === 'image' ? '🖼 Chọn một ảnh nền' : '🎞 Chọn clip từ tất cả thư mục';
    $('#tvQ').placeholder = wanted === 'image' ? 'Tìm tên ảnh…' : 'Tìm tên clip…';
    const folders = Object.entries(allClips).map(([f, L]) => [f, L.filter(c => c.kind === wanted)]).filter(([, L]) => L.length);
    if (!folders.some(([f]) => f === folderSel)) folderSel = '';
    $('#tvF').innerHTML = '<option value="">Tất cả thư mục</option>' + folders.map(([f, L]) => `<option value="${esc(f)}">${esc(f)} (${L.length})</option>`).join('');
    $('#tvF').value = folderSel;
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
    if (isStillBackground()) S.videos = i >= 0 ? [] : [f];
    else if (i >= 0) S.videos.splice(i, 1); else S.videos.push(f);
    S.note = ''; refresh(); drawGrid();
  });

  (async () => {
    try {
      online = (await fetch('/api/ping')).ok;
      templates = await (await fetch('/api/templates')).json();
      audio = await (await fetch('/api/audio')).json();
      const tts = await (await fetch('/api/dub/voices')).json();
      ttsVoices = tts.voices || []; ttsConfigured = tts.configured; ttsPoems = new Set(tts.poems || []);
      syncAudio();
      music = await (await fetch('/api/music')).json();
      const groups = {};
      music.forEach(m => (groups[m.folder] = groups[m.folder] || []).push(m));
      $('#tvM').innerHTML = '<option value="">— chọn nhạc —</option>' + Object.entries(groups).map(([g, ms]) =>
        `<optgroup label="${esc(g)}">${ms.map(m => `<option value="${esc(m.file)}">${esc(m.name.replace(/^Pixabay_/, '').slice(0, 44))} · ${m.dur}s</option>`).join('')}</optgroup>`).join('');
    } catch (e) { online = false; }
    if (online) {
      try { await loadClips(); }
      catch (e) { S.note = 'Chưa tải được thời lượng clip; mở “Tất cả clip” để thử lại.'; }
    }
    new MutationObserver(decorate).observe($('#list'), { childList: true, subtree: true });
    decorate();
  })();
})();
