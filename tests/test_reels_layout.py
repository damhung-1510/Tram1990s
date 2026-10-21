import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tao_video as app


class ReelsLayoutTests(unittest.TestCase):
    def test_opening_ends_exactly_at_first_verse_frame(self):
        pages = app.reels_with_hook([('Câu thơ đầu', 9.518237, 3)], 'Lời mở đầu')
        self.assertAlmostEqual(pages[0][1] + pages[0][2], pages[1][1])
        for template in ('tho-reels-doc-nhanh', 'tho-reels-anh-mo'):
            doc, _ = app.build_from_template(app.TEMPLATES / template, 16, [(16, 1)],
                                             pages, 'Tên bài', 'Tản Đà', [])
            opening = next(c for c in doc['clips'] if c['trackId'] == 'T2')
            first = next(c for c in doc['clips'] if c['trackId'] == 'T2.line.0')
            self.assertAlmostEqual(opening['start'] + opening['duration'], first['start'], places=6)

    def test_opening_and_verse_share_first_line_position(self):
        for template in ('tho-reels-doc-nhanh', 'tho-reels-anh-mo'):
            for rows in (1, 3, 4):
                with self.subTest(template=template, rows=rows):
                    hook = '\n'.join(['Một lời mở đầu'] * rows)
                    pages = [(hook, 0.35, 4.5), *app.reels_reveal_pages(
                        ['Nước non nặng một lời thề,', 'Nước đi đi mãi không về cùng non.'], [5, 8], 12)]
                    doc, _ = app.build_from_template(app.TEMPLATES / template, 16, [(16, 1)],
                                                     pages, 'Tên bài', 'Tản Đà', [])
                    opening = next(c for c in doc['clips'] if c['trackId'] == 'T2')
                    first = next(c for c in doc['clips'] if c['trackId'] == 'T2.line.0')
                    pitch = opening['text']['fontSize'] * opening['text']['lineHeight']
                    first_hook_line = opening['offsetY'] - (rows - 1) * pitch / 2
                    self.assertAlmostEqual(first_hook_line, first['offsetY'])
                    self.assertEqual(opening['offsetX'], first['offsetX'])
                    self.assertEqual(opening['text']['fontSize'], first['text']['fontSize'])

    def test_lines_persist_until_stanza_end(self):
        lines = app.poem_lines(app.load_poems()['Q040'])
        starts = [5 + i * 2 for i in range(len(lines))]
        pages = app.reels_reveal_pages(lines, starts, 26)
        self.assertEqual([p[0] for p in pages], lines)
        cursor = 0
        for count in app.reels_chunk_sizes(len(lines)):
            group = pages[cursor:cursor + count]
            ends = [start + duration for _, start, duration in group]
            self.assertEqual(len(set(ends)), 1)
            self.assertEqual(ends[0], starts[cursor + count] if cursor + count < len(lines) else 26)
            cursor += count

    def test_both_templates_have_safe_bounds_and_stable_layers(self):
        lines = app.poem_lines(app.load_poems()['Q040'])
        pages = app.reels_reveal_pages(lines, [5 + i * 2 for i in range(len(lines))], 26)
        pages.insert(0, ('Lời mở đầu', 0.35, 4.5))
        for template in ('tho-reels-doc-nhanh', 'tho-reels-anh-mo'):
            with self.subTest(template=template):
                doc, _ = app.build_from_template(app.TEMPLATES / template, 30, [(30, 1)],
                                                 pages, 'Tên bài', 'Tản Đà', [])
                verses = [c for c in doc['clips'] if c['trackId'].startswith('T2.line.')]
                self.assertEqual(len(verses), len(lines))
                track_order = [t['id'] for t in doc['tracks']]
                for c in verses:
                    self.assertGreater(track_order.index(c['trackId']), track_order.index('FG'))
                    self.assertLess(track_order.index(c['trackId']), track_order.index('FADE'))
                self.assertEqual([c['text']['content'] for c in verses], lines)
                for c in verses:
                    left = min(0.5, 1 - c['text']['maxWidth']) + c['offsetX']
                    self.assertAlmostEqual(left, 0.08)
                    self.assertLessEqual(left + c['text']['maxWidth'], 0.92 + 1e-9)
                    self.assertEqual(c['keys'], [])
                    self.assertEqual((c['fadeIn'], c['fadeOut'], c['opacity']), (0, 0, 1))
                for lane in {c['trackId'] for c in verses}:
                    clips = sorted([c for c in verses if c['trackId'] == lane], key=lambda c: c['start'])
                    for a, b in zip(clips, clips[1:]):
                        self.assertLessEqual(a['start'] + a['duration'], b['start'])
                self.assertEqual(verses[0]['offsetY'], verses[5]['offsetY'])


if __name__ == '__main__':
    unittest.main()
