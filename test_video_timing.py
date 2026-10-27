"""Kiểm tra khớp giọng + 3 giây, giới hạn slow và clip ngắn/multi-clip."""
import math
import random
import unittest

import tao_video as video


class VideoTimingTests(unittest.TestCase):
    def test_quotes_end_three_seconds_after_voice(self):
        for kind in ('Trích dẫn', 'Trích dẫn Ngày mới'):
            for template in ('trich-dan', 'tho-reels-doc-nhanh', 'tho-hoai-co'):
                lead, tail, total = video.render_timing({'kind': kind}, template, 42.237)
                self.assertEqual((lead, tail), (0, 3))
                self.assertAlmostEqual(total, 45.237)
        self.assertEqual(video.render_timing({'kind': 'Thơ'}, 'tho-reels-doc-nhanh', 40), (0.5, 4, 44.5))

    def test_short_clip_is_not_looped_for_quotes(self):
        with self.assertRaisesRegex(ValueError, 'Chọn thêm clip'):
            video.plan_slots([7.533333], 47, repeat=False, max_speed=0.85)
        with self.assertRaises(ValueError):
            video.plan_slots([23], 46.01, repeat=False, max_speed=0.85)
        self.assertEqual(video.plan_slots([23], 46, repeat=False, max_speed=0.85), [(0, 46, 0.5)])

    def test_short_clip_can_be_combined_with_another(self):
        plan = video.plan_slots([7, 20], 49, repeat=False, max_speed=0.85)
        self.assertEqual([i for i, _, _ in plan], [0, 1])
        self.assertAlmostEqual(sum(length for _, length, _ in plan), 49)
        self.assertEqual(plan[0], (0, 14, 0.5))
        self.assertGreaterEqual(plan[1][2], 0.5)

    def test_long_clip_is_slowed_and_trimmed(self):
        self.assertEqual(video.plan_slots([60], 48, repeat=False, max_speed=0.85), [(0, 48, 0.85)])

    def test_feasible_multi_clip_plans_do_not_overrun_media(self):
        rng = random.Random(2026)
        for _ in range(100):
            durations = [rng.uniform(0.2, 80) for _ in range(rng.randint(1, 15))]
            target = rng.uniform(0.01, sum(durations) * 2)
            plan = video.plan_slots(durations, target, repeat=False, max_speed=0.85)
            self.assertEqual(len(plan), len(durations))
            self.assertAlmostEqual(sum(length for _, length, _ in plan), target)
            for i, length, speed in plan:
                self.assertGreaterEqual(speed + 1e-9, 0.5)
                self.assertLessEqual(speed, 0.85)
                self.assertLessEqual(length * speed, durations[i] + 1e-8)

    def test_invalid_media_fails_before_planning(self):
        for durations, target in (([], 40), ([0], 40), ([-1], 40), ([math.nan], 40), ([10], math.inf)):
            with self.assertRaises(ValueError):
                video.plan_slots(durations, target, repeat=False)

    def test_template_preserves_full_voice_and_slow_speed(self):
        voice_duration = 42.237
        lead, tail, total = video.render_timing({'kind': 'Trích dẫn Ngày mới'}, 'trich-dan', voice_duration)
        plan = video.plan_slots([34.866667], total, repeat=False, max_speed=0.85)
        audio = [dict(path='voice.mp3', name='voice', duration=voice_duration, lane='A',
                      start=lead, dur=voice_duration)]
        doc, _ = video.build_from_template(video.TEMPLATES / 'trich-dan', total,
                                           [(length, speed) for _, length, speed in plan],
                                           [('Lời đọc', 0, voice_duration)], 'Ngày mới', 'Tự biên', audio)
        self.assertAlmostEqual(max(c['start'] + c['duration'] for c in doc['clips']), total, places=3)
        voice = next(c for c in doc['clips'] if c['kind'] == 'audio')
        self.assertEqual(voice['duration'], voice_duration)
        self.assertAlmostEqual(total - voice['start'] - voice['duration'], 3)
        for clip in [c for c in doc['clips'] if c['kind'] == 'video']:
            self.assertEqual(clip['speed'], plan[0][2])


if __name__ == '__main__':
    unittest.main()
