import unittest

from backtester.cli.common import (
    arg_or_default,
    normalize_symbol,
    parse_source_weights,
    parse_windows,
)


class CliCommonTests(unittest.TestCase):
    def test_arg_or_default_uses_default_only_for_none(self) -> None:
        self.assertEqual(arg_or_default(None, 10), 10)
        self.assertEqual(arg_or_default(0, 10), 0)

    def test_normalize_symbol_pads_numeric_symbols_and_uppercases_text(self) -> None:
        self.assertEqual(normalize_symbol("5930"), "005930")
        self.assertEqual(normalize_symbol("'abc'"), "ABC")
        self.assertEqual(normalize_symbol(None), "")

    def test_parse_source_weights_accepts_comma_separated_source_weights(self) -> None:
        self.assertEqual(parse_source_weights("news=0.7,flow=0.3"), {"news": 0.7, "flow": 0.3})
        self.assertIsNone(parse_source_weights(""))
        self.assertIsNone(parse_source_weights(None))

    def test_parse_source_weights_rejects_invalid_items(self) -> None:
        with self.assertRaises(SystemExit):
            parse_source_weights("news")
        with self.assertRaises(SystemExit):
            parse_source_weights("=0.5")

    def test_parse_windows_requires_four_colon_separated_parts(self) -> None:
        self.assertEqual(
            parse_windows(["train:2024-01-01:2024-06-30:paper"]),
            [("train", "2024-01-01", "2024-06-30", "paper")],
        )
        with self.assertRaises(SystemExit):
            parse_windows(["bad:window"])


if __name__ == "__main__":
    unittest.main()
