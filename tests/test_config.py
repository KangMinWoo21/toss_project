import tempfile
import unittest
from pathlib import Path

from backtester.config import load_env_file


class ConfigTests(unittest.TestCase):
    def test_load_env_file_reads_key_value_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                "TOSSINVEST_CLIENT_ID=c_test\n"
                "TOSSINVEST_CLIENT_SECRET=s_test\n"
                "# ignored comment\n",
                encoding="utf-8",
            )

            values = load_env_file(path)

        self.assertEqual(values["TOSSINVEST_CLIENT_ID"], "c_test")
        self.assertEqual(values["TOSSINVEST_CLIENT_SECRET"], "s_test")


if __name__ == "__main__":
    unittest.main()
