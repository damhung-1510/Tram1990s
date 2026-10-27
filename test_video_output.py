import unittest

import tao_video as video


class VideoOutputTests(unittest.TestCase):
    def test_morning_category_uses_requested_folder_for_any_template(self):
        for template in video.LABELS:
            poem = {'kind': 'Trích dẫn Ngày mới', 'template': template}
            self.assertEqual(video.video_output_dir(poem), video.ROOT / 'Vid_chao_ngay_moi')

    def test_other_categories_keep_existing_folder(self):
        for kind in ('Trích dẫn', 'Thơ', 'Ca dao', '', None):
            self.assertEqual(video.video_output_dir({'kind': kind}), video.OUT)
        self.assertEqual(video.video_output_dir({}), video.OUT)

    def test_all_thirty_morning_poems_are_routed(self):
        poems = [p for p in video.load_poems().values() if p.get('kind') == 'Trích dẫn Ngày mới']
        self.assertEqual(len(poems), 30)
        for poem in poems:
            self.assertEqual(video.video_output_dir(poem), video.MORNING_OUT)


if __name__ == '__main__':
    unittest.main()
