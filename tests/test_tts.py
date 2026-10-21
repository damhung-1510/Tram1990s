import io
import json
import sys
import tempfile
import unittest
import urllib.error
import queue
from email.message import Message
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tao_video as app


class SpeechTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.root_patch = patch.object(app, 'ROOT', self.root)
        self.root_patch.start()
        self.poem = dict(id='Q035', title='Buồn trông', tts='Kịch bản thử')
        self.voice = next(iter(app.DUB_VOICES))
        app.DUB_JOBS['test'] = dict(status='queued')

    def tearDown(self):
        self.root_patch.stop()
        self.tmp.cleanup()

    def run_worker(self, response=None, error=None, audio=None):
        app.DUB_LOCK.acquire()
        with patch.object(app, 'tts_key', return_value='test-secret'), \
             patch.object(app, 'list_audio', side_effect=audio or [{}, {'Q035': [dict(file='voice.mp3')]}]), \
             patch.object(app, 'duration', return_value=2), \
             patch.object(app.urllib.request, 'urlopen', side_effect=error, return_value=response) as request:
            app.dub('test', self.poem, self.voice)
        self.assertFalse(app.DUB_LOCK.locked())
        return request

    def test_success_saves_audio_and_replaces_stale_state(self):
        state = self.root / 'Thơ/da-long-tieng.json'
        state.parent.mkdir()
        state.write_text(json.dumps({'Q035': {'file': 'missing.mp3'}, 'Q040': {'file': 'keep.mp3'}}))
        response = Mock()
        response.__enter__ = Mock(return_value=io.BytesIO(b'test-audio'))
        response.__exit__ = Mock(return_value=False)
        request = self.run_worker(response=response)
        self.assertEqual(app.DUB_JOBS['test']['status'], 'done')
        saved = json.loads(state.read_text())
        self.assertEqual(saved['Q035']['voice_id'], self.voice)
        self.assertEqual(saved['Q040']['file'], 'keep.mp3')
        self.assertTrue((self.root / saved['Q035']['file']).is_file())
        body = json.loads(request.call_args.args[0].data)
        self.assertEqual(body['text'], self.poem['tts'])
        self.assertEqual(body['model_id'], 'eleven_v4')

    def test_api_error_does_not_mark_done_or_expose_key(self):
        error = urllib.error.HTTPError('https://api.elevenlabs.io', 401, 'error', {},
                                      io.BytesIO(b'{"detail":{"status":"quota_exceeded"}}'))
        self.run_worker(error=error)
        self.assertEqual(app.DUB_JOBS['test']['status'], 'error')
        self.assertIn('credit', app.DUB_JOBS['test']['message'])
        self.assertNotIn('test-secret', str(app.DUB_JOBS['test']))
        self.assertFalse((self.root / 'Thơ/da-long-tieng.json').exists())
        self.assertFalse(list(self.root.rglob('*.mp3')))

    def test_existing_audio_avoids_paid_request(self):
        request = self.run_worker(audio=[{'Q035': [dict(file='existing.mp3')]},
                                         {'Q035': [dict(file='existing.mp3')]}])
        request.assert_not_called()
        self.assertEqual(app.DUB_JOBS['test']['status'], 'done')

    def test_empty_audio_is_rejected(self):
        response = Mock()
        response.__enter__ = Mock(return_value=io.BytesIO(b''))
        response.__exit__ = Mock(return_value=False)
        self.run_worker(response=response)
        self.assertEqual(app.DUB_JOBS['test']['status'], 'error')
        self.assertFalse(list(self.root.rglob('*.mp3')))

    def test_endpoint_rejects_unknown_voice_and_duplicate_work(self):
        handler = app.Handler.__new__(app.Handler)
        handler.path = '/api/dub'
        handler.headers = Message()
        handler.headers['Content-Type'] = 'application/json'
        handler.send_json = Mock()
        for voice, busy, expected in [('unknown', False, 400), (self.voice, True, 409)]:
            body = json.dumps(dict(poemId='Q035', voiceId=voice)).encode()
            if 'Content-Length' in handler.headers:
                handler.headers.replace_header('Content-Length', str(len(body)))
            else:
                handler.headers['Content-Length'] = str(len(body))
            handler.rfile = io.BytesIO(body)
            if busy:
                app.DUB_LOCK.acquire()
            try:
                with patch.object(app, 'load_poems', return_value={'Q035': self.poem}), \
                     patch.object(app, 'list_audio', return_value={}), \
                     patch.object(app, 'tts_key', return_value='test-secret'):
                    handler.do_POST()
                self.assertEqual(handler.send_json.call_args.args[1], expected)
            finally:
                if busy:
                    app.DUB_LOCK.release()


class ApiEventTests(unittest.TestCase):
    def test_export_result_before_response_is_not_lost(self):
        api = app.Api.__new__(app.Api)
        api._lines = queue.Queue()
        api._events = []
        api.send = Mock(return_value=1)
        event = dict(method='export.failed', params=dict(error='test'))
        api._lines.put(json.dumps(event))
        api._lines.put(json.dumps(dict(id=1, result=dict(job='j1'))))
        self.assertEqual(api.call('export.run', {})['job'], 'j1')
        self.assertEqual(api.wait_event(('export.done', 'export.failed'), timeout=0), event)

    def test_silent_cli_times_out(self):
        api = app.Api.__new__(app.Api)
        api._lines = queue.Queue()
        with self.assertRaises(TimeoutError):
            api._receive(0.01)


class RenderErrorTests(unittest.TestCase):
    def test_render_failure_is_reported_and_saved_to_log(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(app, 'ROOT', Path(folder)), \
             patch.object(app, 'load_poems', side_effect=RuntimeError('test export failure')), \
             patch('sys.stderr', new=io.StringIO()) as stderr:
            app.JOBS['test-render'] = dict(status='queued')
            app.RENDER_LOCK.acquire()
            app.render('test-render', {})
            self.assertEqual(app.JOBS['test-render']['status'], 'error')
            self.assertIn('test export failure', app.JOBS['test-render']['message'])
            self.assertIn('test export failure', stderr.getvalue())
            self.assertIn('test export failure', (Path(folder) / '.tao-video-logs/test-render.log').read_text())
            self.assertFalse(app.RENDER_LOCK.locked())


if __name__ == '__main__':
    unittest.main()
