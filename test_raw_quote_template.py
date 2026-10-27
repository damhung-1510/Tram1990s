"""Trích Dẫn Không Chữ: hình sạch, giọng đọc, nhạc tùy chọn."""
import json
import unittest

import tao_video as video


class RawQuoteTemplateTests(unittest.TestCase):
    def build(self, music=False):
        audio = [dict(path='voice.mp3', name='voice', duration=42, lane='A', start=0, dur=42)]
        if music:
            audio.append(dict(path='music.mp3', name='music', duration=45, lane='A.2',
                              start=0, dur=45, volume=0.1))
        return video.build_from_template(
            video.TEMPLATES / video.RAW_VIDEO_TEMPLATE, 45,
            [(20, 0.7), (25, 0.8)], [('Không hiển thị', 0, 42)],
            'Không hiển thị tiêu đề', 'Không hiển thị tác giả', audio)[0]

    def test_saved_template_has_clean_video_and_page_name(self):
        doc = json.loads((video.TEMPLATES / video.RAW_VIDEO_TEMPLATE / 'template.json').read_text())
        self.assertEqual(len(doc['clips']), 2)
        self.assertEqual(doc['clips'][0]['trackId'], 'FG')
        self.assertEqual(doc['clips'][0]['kind'], 'video')

    def test_no_music_build_has_only_video_and_narration(self):
        doc = self.build()
        self.assertEqual([c['kind'] for c in doc['clips']], ['text', 'video', 'video', 'audio'])
        visuals = [c for c in doc['clips'] if c['kind'] == 'video']
        for clip in visuals:
            self.assertEqual(clip['videoEffects'], [])
            self.assertEqual(clip['filters'], [])
            self.assertEqual(clip['keys'], [])
            self.assertEqual((clip['scale'], clip['opacity'], clip['volume']), (1, 1, 0))
            self.assertNotIn('transitionIn', clip)
        self.assertEqual([c['speed'] for c in visuals], [0.7, 0.8])
        self.assertEqual(max(c['start'] + c['duration'] for c in doc['clips']), 45)
        self.assertEqual(doc['clips'][-1]['duration'], 42)

    def test_page_name_stays_top_right_for_full_video(self):
        labels = [c for c in self.build()['clips'] if c['kind'] == 'text']
        self.assertEqual(len(labels), 1)
        label = labels[0]
        self.assertEqual(label['text']['content'], 'TRẠM 1990s')
        self.assertEqual((label['start'], label['duration']), (0, 45))
        self.assertGreater(label['offsetX'], 0.2)
        self.assertLess(label['offsetY'], -0.4)
        self.assertLess(0.5 + label['offsetX'] + label['text']['maxWidth'] / 2, 1)
        self.assertEqual(label['videoEffects'], [])

    def test_music_still_supported_when_selected(self):
        audio = [c for c in self.build(music=True)['clips'] if c['kind'] == 'audio']
        self.assertEqual([c['trackId'] for c in audio], ['A', 'A.2'])
        self.assertEqual(audio[1]['volume'], 0.1)

    def test_optional_music_is_scoped_to_raw_video_and_still_image(self):
        self.assertFalse(video.requires_music(video.RAW_VIDEO_TEMPLATE))
        self.assertFalse(video.requires_music(video.IMAGE_TEMPLATE))
        for template in video.LABELS:
            if template not in (video.RAW_VIDEO_TEMPLATE, video.IMAGE_TEMPLATE):
                self.assertTrue(video.requires_music(template), template)


if __name__ == '__main__':
    unittest.main()
