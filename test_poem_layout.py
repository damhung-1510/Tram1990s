import unittest
from PIL import ImageFont

import tao_video as video


class PoemLayoutTests(unittest.TestCase):
    def test_reels_reveal_has_no_gaps_overlaps_or_fades(self):
        lines = ["Một câu thơ dài", "Câu thứ hai", "Câu thứ ba", "Câu thứ tư"] * 2
        starts = [1 + i * 2 for i in range(8)]
        pages = video.reels_reveal_pages(lines, starts, 17)
        for current, following in zip(pages, pages[1:]):
            self.assertAlmostEqual(current[1] + current[2], following[1])
        self.assertEqual(pages[0][0], "Một")
        self.assertEqual(next(p[0] for p in pages if p[1] == 3), lines[0] + "\nCâu")
        self.assertEqual(next(p[0] for p in pages if p[1] == 9), "Một")
        for template in ("tho-reels-doc-nhanh", "tho-reels-anh-mo"):
            doc = video.build_from_template(video.TEMPLATES / template, 21,
                                           [(21, 1)], pages, "Tên bài", "Tác giả", [])[0]
            clips = [c for c in doc["clips"] if c["trackId"] == "T2"]
            tops = []
            for c in clips:
                self.assertEqual(c["keys"], [])
                self.assertEqual(c["fadeIn"], 0)
                self.assertEqual(c["fadeOut"], 0)
                tops.append(self.bounds(c)[0])
            self.assertLess(max(tops) - min(tops), 1e-8)
            for current, following in zip(clips, clips[1:]):
                self.assertAlmostEqual(current["start"] + current["duration"], following["start"])

    def build(self, pages, template="tho-hoai-co"):
        return video.build_from_template(
            video.TEMPLATES / template, 50, [(50, 1)],
            [(text, 1, 20) for text in pages], "Yêu", "Xuân Diệu", [],
        )[0]

    def bounds(self, clip):
        style = clip["text"]
        variant = " Bold" if style.get("fontWeight", 400) >= 600 else ""
        variant += " Italic" if style.get("italic") else ""
        font = ImageFont.truetype(
            f"/System/Library/Fonts/Supplemental/Georgia{variant}.ttf", 1000)
        lines = style["content"].splitlines()
        height = ((len(lines) - 1) * style.get("lineHeight", 1.2)
                  + sum(font.getmetrics()) / 1000) * style["fontSize"]
        center = 0.5 + clip["offsetY"]
        return center - height / 2, center + height / 2, font

    def assert_layout(self, doc):
        text = {c["trackId"]: c for c in doc["clips"] if c["kind"] == "text"}
        poem_top, poem_bottom, font = self.bounds(text["T2"])
        self.assertGreaterEqual(poem_top, 0.22 - 1e-8)
        title_top, title_bottom, _ = self.bounds(text["T3"])
        author_top, author_bottom, _ = self.bounds(text["T3.2"])
        self.assertGreater(title_top, poem_bottom)
        self.assertGreater(author_top, title_bottom)
        self.assertLess(author_bottom, 0.94)
        style = text["T2"]["text"]
        for line in style["content"].splitlines():
            pixels = font.getlength(line) / 1000 * style["fontSize"] * doc["video"]["height"]
            self.assertLess(pixels, style["maxWidth"] * doc["video"]["width"])

    def test_yeu_preserves_lines_and_timing(self):
        poem = "\n".join(video.poem_lines(video.load_poems()["Q052"]))
        doc = self.build([poem])
        self.assert_layout(doc)
        text = {c["trackId"]: c for c in doc["clips"] if c["kind"] == "text"}
        self.assertEqual(text["T2"]["text"]["content"], poem)
        self.assertEqual(text["T2"]["start"], text["T1"]["start"])
        self.assertEqual(text["T2"]["duration"], text["T1"]["duration"])

    def test_short_and_long_poems(self):
        for count in (2, 4, 13, 25, 40):
            with self.subTest(count=count):
                self.assert_layout(self.build(["\n".join(["Yêu, là chết ở trong lòng một ít,"] * count)]))

    def test_long_line_fits(self):
        self.assert_layout(self.build(["Một câu thơ rất dài " * 5]))

    def test_pages_share_size_and_position(self):
        for template in ("tho-hoai-co", "tho-hoai-co-chay-chu-2-trang",
                         "tho-hoai-co-chay-chu-nhieu-trang"):
            with self.subTest(template=template):
                doc = self.build(["Một câu thơ", "\n".join(["Một câu thơ dài hơn"] * 13)], template)
                pages = [c for c in doc["clips"] if c["trackId"] == "T2"]
                self.assertEqual(pages[0]["text"]["fontSize"], pages[1]["text"]["fontSize"])
                self.assertEqual(pages[0]["offsetY"], pages[1]["offsetY"])
                self.assert_layout(doc)

    def test_reels_fast_read_template(self):
        sample = video.load_poems()["Q052"]
        self.assertEqual(video.template_per_page("tho-reels-doc-nhanh", sample), 4)
        poem = video.poem_lines(sample)
        pages = ["\n".join(poem[i:i + 4]) for i in range(0, len(poem), 4)]
        doc = self.build(pages, "tho-reels-doc-nhanh")
        text = [c for c in doc["clips"] if c["kind"] == "text"]
        poem_clips = [c for c in text if c["trackId"] == "T2"]
        self.assertTrue(all(c["text"]["align"] == "left" for c in poem_clips))
        self.assertTrue(all(not c["text"]["italic"] for c in poem_clips))
        self.assertTrue(all(len(c["text"]["content"].splitlines()) <= 4 for c in poem_clips))
        self.assertTrue(all(c["text"]["fontSize"] <= 0.0306667 for c in poem_clips))
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", 1000)
        for c in poem_clips:
            max_pixels = c["text"]["maxWidth"] * doc["video"]["width"]
            for line in c["text"]["content"].splitlines():
                self.assertLessEqual(font.getlength(line) / 1000 * c["text"]["fontSize"]
                                     * doc["video"]["height"], max_pixels)
        title = next(c for c in text if c["trackId"] == "T3")
        author = next(c for c in text if c["trackId"] == "T3.2")
        self.assertTrue(all(c["text"]["fontSize"] == poem_clips[0]["text"]["fontSize"]
                            for c in (title, author)))
        self.assertGreaterEqual(title["start"], max(c["start"] + c["duration"] for c in poem_clips))
        self.assertGreaterEqual(author["start"], title["start"])

    def test_reels_hook_is_short_and_readable(self):
        hook = video.load_poems()["Q052"]["hook"]
        lines = video.reels_hook_text(hook).splitlines()
        self.assertLessEqual(len(lines), 4)
        self.assertTrue(all(len(line) <= 38 for line in lines))
        self.assertEqual(" ".join(lines), hook)

    def test_reels_brand_rule_alignment_calibration(self):
        doc = self.build(["Một câu thơ"], "tho-reels-doc-nhanh")
        brand = next(c for c in doc["clips"] if c.get("trackId") == "T1")
        rule = next(c for c in doc["clips"] if c.get("name") == "page rule")
        self.assertEqual(brand["offsetX"], -0.39)
        self.assertEqual(rule["offsetX"], -0.341)

    def test_reels_hook_is_left_aligned_but_verse_uses_full_width(self):
        sample = video.load_poems()["Q052"]
        doc = video.build_from_template(
            video.TEMPLATES / "tho-reels-doc-nhanh", 30, [(30, 1)],
            [(video.reels_hook_text(sample["hook"]), 0.35, 5.0),
             ("\n".join(video.poem_lines(sample)[:4]), 6.0, 10.0)],
            "Yêu", "Xuân Diệu", [],
        )[0]
        pages = sorted((c for c in doc["clips"] if c.get("trackId") == "T2"),
                       key=lambda c: c["start"])
        self.assertEqual(pages[0]["text"]["align"], "left")
        self.assertEqual(pages[0]["offsetX"], -0.39)
        self.assertEqual(pages[1]["text"]["align"], "left")
        self.assertEqual(pages[1]["text"]["maxWidth"], 0.94)

    def test_reels_blurred_image_template(self):
        sample = video.load_poems()["Q052"]
        self.assertEqual(video.template_per_page("tho-reels-anh-mo", sample), 4)
        doc = video.build_from_template(
            video.TEMPLATES / "tho-reels-anh-mo", 30, [(30, 1)],
            [("\n".join(video.poem_lines(sample)[:4]), 1.0, 20.0)],
            "Yêu", "Xuân Diệu", [],
        )[0]
        visuals = [c for c in doc["clips"] if c.get("trackId") in ("BG", "FG")]
        self.assertTrue(all(c["kind"] == "image" for c in visuals))
        foreground = next(c for c in visuals if c["trackId"] == "FG")
        blur = next(e for e in foreground["videoEffects"] if e["id"] == "concat.gaussian-blur")
        self.assertEqual(blur["params"]["radius"], 6.0)
        images = [c for group in video.list_clips().values() for c in group if c["kind"] == "image"]
        self.assertGreaterEqual(len(images), 3)


if __name__ == "__main__":
    unittest.main()
