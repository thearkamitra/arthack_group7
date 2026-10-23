import tempfile
import unittest
from pathlib import Path

from borrowed_eyes.normalize import normalize_pair
from PIL import Image


class NormalizeTests(unittest.TestCase):
    def test_pair_alignment_and_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, box in [("one", (20, 10, 59, 89)), ("two", (80, 30, 119, 109))]:
                im = Image.new("RGBA", (160, 120))
                from PIL import ImageDraw

                ImageDraw.Draw(im).rectangle(box, fill=(180, 90, 30, 255))
                im.save(root / f"{name}.png")
            sources = [root / "one.png", root / "two.png"]
            original = [p.read_bytes() for p in sources]
            results = normalize_pair(*sources, root / "result")
            bounds = []
            for result in results:
                with Image.open(result) as image:
                    self.assertEqual(image.size, (128, 128))
                    b = image.getchannel("A").point(lambda x: 255 if x > 127 else 0).getbbox()
                    bounds.append(b)
                    self.assertGreater(b[0], 0)
                    self.assertGreater(b[1], 0)
                    self.assertAlmostEqual((b[3] - b[1]) / (b[2] - b[0]), 2, delta=0.04)
            self.assertEqual(bounds[0], bounds[1])
            self.assertEqual(original, [p.read_bytes() for p in sources])
            with self.assertRaises(FileExistsError):
                normalize_pair(*sources, root / "result")

    def test_bad_canvas_rejected_before_reading(self):
        with self.assertRaises(ValueError):
            normalize_pair(Path("missing"), Path("missing"), Path("unused"), size=0)
