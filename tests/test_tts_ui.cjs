// Run: node tests/test_tts_ui.cjs /path/to/node_modules/jsdom
const { JSDOM } = require(process.argv[2] || 'jsdom');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(condition) {
  for (let i = 0; i < 100; i++) {
    if (condition()) return;
    await wait(20);
  }
  throw new Error('UI did not reach expected state');
}

(async () => {
  let audio = {}, outcome = 'error', sent, renderRequest;
  const templates = [{ id: 'tho-hoai-co', label: 'Thơ Hoài Cổ', ok: true },
    { id: 'tho-hoai-co-chay-chu-2-trang', label: 'Hai trang', ok: true },
    { id: 'tho-hoai-co-chay-chu-nhieu-trang', label: 'Nhiều trang', ok: true }];
  const voices = [{ id: 'qn4pQo7kIjvZ1a7SowZE', name: 'Giọng thơ' },
    { id: 'O4GJDPajhRb6MxWUMf7V', name: 'Giọng trích dẫn' }];
  const ids = JSON.parse(fs.readFileSync(path.join(root, 'Thơ/bai-chinh-thuc.json'))).map(p => p.id);
  const dom = new JSDOM(fs.readFileSync(path.join(root, 'GHEP_THO_VIDEO.html'), 'utf8'), {
    url: 'http://127.0.0.1:8787/', runScripts: 'dangerously',
    beforeParse(w) {
      w.HTMLMediaElement.prototype.pause = function () {};
      w.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
      w.HTMLDialogElement.prototype.close = function () { this.open = false; };
      const timeout = w.setTimeout.bind(w);
      w.setTimeout = (fn, ms) => timeout(fn, Math.min(ms, 5));
      w.fetch = async (url, options) => {
        let data;
        if (url === '/api/ping') data = { ok: true };
        else if (url === '/api/audio') data = audio;
        else if (url === '/api/music') data = [{ file: 'music.mp3', folder: 'Nhạc', name: 'Nhạc thử', dur: 20 }];
        else if (url.startsWith('/api/clips')) data = { 'Test': [{ file: 'Videos/test.mp4', name: 'Clip thử', kind: 'video' }] };
        else if (url === '/api/dub/voices') data = { voices, poems: ids, configured: true };
        else if (url === '/api/templates') data = templates.map(t => ({ ...t, template: t.id }));
        else if (url.startsWith('/api/template')) data = { label: 'Nhiều trang', template: templates[2].id };
        else if (url.startsWith('/api/mixinfo')) data = { gain: 0.1, below_db: 20 };
        else if (url === '/api/render') { renderRequest = JSON.parse(options.body); data = { job: 'render-test' }; }
        else if (url === '/api/job/render-test') data = { status: 'error', message: 'End render test' };
        else if (url === '/api/dub') { sent = JSON.parse(options.body); data = { job: 'test' }; }
        else if (url === '/api/dub/job/test') {
          data = { status: outcome, message: outcome === 'error' ? 'Lỗi thử nghiệm' : 'Đã xong' };
          if (outcome === 'done') audio[sent.poemId] = [{ file: 'Long-tieng/elevenlabs/test.mp3', label: 'ElevenLabs', dur: 12 }];
        } else throw new Error('Unexpected request: ' + url);
        return { ok: true, json: async () => data };
      };
    }
  });
  const w = dom.window, d = w.document;
  w.eval(fs.readFileSync(path.join(root, 'tao-video.js'), 'utf8'));
  await until(() => d.querySelectorAll('[data-tts]').length === ids.length);
  assert.equal(d.querySelectorAll('[data-tts]').length, ids.length, 'All missing files, including stale done records, need buttons');
  assert.equal(d.querySelector('[data-t=dub]').textContent, '✅ Đã lồng tiếng (0)');
  const button = d.querySelector('[data-tts="Q040"]');
  const select = button.closest('.tv-tts').querySelector('select');
  select.value = voices[1].id;
  button.click();
  assert.ok(d.querySelector('#tvSpeechText').textContent.replace(/\[[^\]]*\]/g, '').replace(/\s+/g, ' ').includes('Nước non nặng một lời thề'));
  d.querySelector('#tvSpeechGo').click();
  await until(() => d.querySelector('#tvSpeechStatus').textContent.includes('Lỗi thử nghiệm'));
  assert.equal(sent.voiceId, voices[1].id, 'Selected voice must reach the API');
  assert.match(d.querySelector('#tvSpeechStatus').textContent, /Lỗi thử nghiệm/);
  assert.equal(d.querySelector('#tvSpeechGo').disabled, false, 'Failure can be retried');
  outcome = 'done';
  d.querySelector('#tvSpeechGo').click();
  await until(() => d.querySelector('[data-tts="Q040"]') === null);
  assert.equal(d.querySelector('[data-tts="Q040"]'), null, 'Completed poem no longer needs a button');
  assert.match(d.querySelector('#tvP').textContent, /Q040/);
  assert.equal(d.querySelector('#tvV').value, 'Long-tieng/elevenlabs/test.mp3');
  await until(() => d.querySelector('#tvT').options.length === templates.length);
  d.querySelector('#tvT').value = templates[1].id;
  d.querySelector('#tvT').dispatchEvent(new w.Event('change'));
  d.querySelector('#tvM').value = 'music.mp3';
  d.querySelector('#tvM').dispatchEvent(new w.Event('change'));
  assert.equal(d.querySelector('#tvT').value, templates[1].id, 'Selection survives refresh');
  d.querySelector('#tvAll').click();
  await until(() => d.querySelector('#tvG .it'));
  d.querySelector('#tvG .it').click();
  d.querySelector('#tvGo').click();
  await until(() => renderRequest);
  assert.equal(renderRequest.template, templates[1].id, 'Render request uses selected template');
  await until(() => !d.querySelector('#tvReset').disabled);
  assert.match(d.querySelector('#tvMsg').textContent, /End render test/, 'Render error must survive refresh');
  assert.ok(d.querySelector('#tvMsg').classList.contains('err'));
  d.querySelector('#tvReset').click();
  assert.equal(d.querySelector('#tvP').textContent, 'chưa chọn', 'Reset clears the selected poem');
  d.querySelector('[data-t=dub]').click();
  await wait(20);
  assert.equal(d.querySelectorAll('#list .card').length, 1);
  assert.ok(d.querySelector('#list audio'), 'New audio can be previewed');
  dom.window.close();
  console.log('PASS: speech flow, template selection, render payload, reset and voiced tab');
})().catch(error => { console.error(error); process.exit(1); });
