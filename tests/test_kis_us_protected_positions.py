import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.kis_us.protected_positions import is_protected, load_protected_positions


class KisUsProtectedPositionsTests(unittest.TestCase):
    def test_loads_protected_positions_csv(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "protected.csv"
            path.write_text("symbol,reason\nAAPL,long term core\n", encoding="utf-8")

            protected = load_protected_positions(path)

        self.assertTrue(is_protected("aapl", protected))
        self.assertEqual(protected["AAPL"].reason, "long term core")
        self.assertFalse(is_protected("MSFT", protected))


if __name__ == "__main__":
    unittest.main()
