import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from backtester.dart import (
    classify_dart_disclosure,
    corp_code_for_symbol,
    disclosure_rows_to_event_rows,
    fetch_dart_disclosures_for_corp_code,
    fetch_dart_financial_rows_for_corp_code,
    normalize_dart_list_payload,
    normalize_dart_financial_payload,
    parse_dart_corp_codes,
    save_dart_event_rows,
    save_dart_financial_rows,
)
from backtester.events import load_event_scores


def _corp_code_zip(corp_code: str, stock_code: str) -> bytes:
    xml = (
        "<result>"
        f"<list><corp_code>{corp_code}</corp_code><corp_name>Test Corp</corp_name>"
        f"<stock_code>{stock_code}</stock_code><modify_date>20240101</modify_date></list>"
        "</result>"
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("CORPCODE.xml", xml)
    return buffer.getvalue()


class DartDisclosureTests(unittest.TestCase):
    def test_classify_negative_financing_disclosure(self):
        sentiment, importance = classify_dart_disclosure("주요사항보고서(유상증자결정)")

        self.assertLess(sentiment, 0)
        self.assertGreaterEqual(importance, 1.5)

    def test_classify_positive_share_buyback_disclosure(self):
        sentiment, importance = classify_dart_disclosure("주요사항보고서(자기주식취득결정)")

        self.assertGreater(sentiment, 0)
        self.assertGreaterEqual(importance, 1.5)

    def test_normalize_dart_list_payload_to_event_rows(self):
        payload = {
            "status": "000",
            "list": [
                {
                    "rcept_dt": "20260610",
                    "corp_name": "삼성전자",
                    "stock_code": "005930",
                    "report_nm": "주요사항보고서(유상증자결정)",
                    "rcept_no": "20260610000123",
                }
            ],
        }

        disclosures = normalize_dart_list_payload("005930", payload)
        rows = disclosure_rows_to_event_rows(disclosures)

        self.assertEqual(rows[0][0], "2026-06-10")
        self.assertEqual(rows[0][1], "005930")
        self.assertEqual(rows[0][2], "dart:삼성전자")
        self.assertIn("유상증자", rows[0][3])
        self.assertLess(rows[0][4], 0)

    def test_save_dart_event_rows_can_feed_event_score_store(self):
        payload = {
            "status": "000",
            "list": [
                {
                    "rcept_dt": "20260610",
                    "corp_name": "삼성전자",
                    "stock_code": "005930",
                    "report_nm": "주요사항보고서(유상증자결정)",
                    "rcept_no": "20260610000123",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dart_events.csv"
            rows = disclosure_rows_to_event_rows(normalize_dart_list_payload("005930", payload))
            saved = save_dart_event_rows(rows, path)
            store = load_event_scores(path)

        self.assertEqual(saved, 1)
        self.assertLess(store.score("005930", "2026-06-10"), 0)

    def test_parse_corp_code_zip_maps_stock_symbol_to_corp_code(self):
        xml = (
            "<result>"
            "<list><corp_code>00126380</corp_code><corp_name>삼성전자</corp_name>"
            "<stock_code>005930</stock_code><modify_date>20240101</modify_date></list>"
            "</result>"
        )
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("CORPCODE.xml", xml)

        rows = parse_dart_corp_codes(buffer.getvalue())

        self.assertEqual(corp_code_for_symbol(rows, "005930"), "00126380")

    def test_corp_code_for_symbol_accepts_unpadded_numeric_symbol(self):
        rows = [parse_dart_corp_codes(_corp_code_zip("00126380", "005930"))[0]]

        self.assertEqual(corp_code_for_symbol(rows, "5930"), "00126380")

    def test_fetch_dart_disclosures_reads_all_pages(self):
        calls = []

        def fake_fetcher(**kwargs):
            page_no = kwargs["page_no"]
            calls.append(page_no)
            return {
                "status": "000",
                "total_page": "2",
                "list": [
                    {
                        "rcept_dt": f"2026061{page_no}",
                        "corp_name": "삼성전자",
                        "stock_code": "005930",
                        "report_nm": "주요사항보고서(자기주식취득결정)",
                        "rcept_no": f"2026061000012{page_no}",
                    }
                ],
            }

        rows = fetch_dart_disclosures_for_corp_code(
            api_key="key",
            symbol="005930",
            corp_code="00126380",
            start="2026-01-01",
            end="2026-12-31",
            page_count=1,
            list_fetcher=fake_fetcher,
        )

        self.assertEqual(calls, [1, 2])
        self.assertEqual(len(rows), 2)

    def test_normalize_dart_financial_payload_writes_account_rows(self):
        payload = {
            "status": "000",
            "list": [
                {
                    "corp_code": "00126380",
                    "bsns_year": "2025",
                    "reprt_code": "11011",
                    "fs_div": "CFS",
                    "sj_nm": "손익계산서",
                    "account_nm": "매출액",
                    "thstrm_amount": "1,000",
                    "frmtrm_amount": "900",
                    "currency": "KRW",
                    "ord": "1",
                }
            ],
        }

        rows = normalize_dart_financial_payload("005930", payload)

        self.assertEqual(rows[0]["symbol"], "005930")
        self.assertEqual(rows[0]["account_name"], "매출액")
        self.assertEqual(rows[0]["current_amount"], 1000.0)
        self.assertEqual(rows[0]["previous_amount"], 900.0)

    def test_fetch_dart_financial_rows_for_corp_code_uses_fetcher_and_saves_csv(self):
        def fake_fetcher(**kwargs):
            return {
                "status": "000",
                "list": [
                    {
                        "corp_code": kwargs["corp_code"],
                        "bsns_year": kwargs["business_year"],
                        "reprt_code": kwargs["report_code"],
                        "fs_div": kwargs["fs_div"],
                        "sj_nm": "재무상태표",
                        "account_nm": "자산총계",
                        "thstrm_amount": "2,000",
                        "frmtrm_amount": "1,800",
                        "currency": "KRW",
                        "ord": "1",
                    }
                ],
            }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "financials.csv"
            rows = fetch_dart_financial_rows_for_corp_code(
                api_key="key",
                symbol="005930",
                corp_code="00126380",
                business_year="2025",
                report_code="11011",
                fs_div="CFS",
                financial_fetcher=fake_fetcher,
            )
            saved = save_dart_financial_rows(rows, path)
            text = path.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("자산총계", text)
        self.assertIn("2000.0", text)


if __name__ == "__main__":
    unittest.main()
