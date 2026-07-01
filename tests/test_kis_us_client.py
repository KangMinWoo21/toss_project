import json
import unittest

from backtester.kis_us.client import (
    KIS_US_BALANCE_PATH,
    KIS_US_BALANCE_TR_ID_DEMO,
    KIS_US_INTEGRATED_MARGIN_PATH,
    KIS_US_INTEGRATED_MARGIN_TR_ID,
    KIS_US_PRESENT_BALANCE_PATH,
    KIS_US_PRESENT_BALANCE_TR_ID_DEMO,
    KIS_US_PRICE_PATH,
    KIS_US_PRICE_TR_ID,
    KIS_US_TOKEN_PATH,
    KisUsClient,
)
from backtester.kis_us.models import KisUsConfig


class _FakeResponse:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class _FakeOpener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []

    def __call__(self, request, timeout=30):
        self.requests.append(request)
        return _FakeResponse(self.payloads.pop(0))


class KisUsClientTests(unittest.TestCase):
    def _config(self):
        return KisUsConfig(
            app_key="app",
            app_secret="secret",
            account_no="12345678",
            account_product_code="01",
            mock_base_url="https://openapivts.koreainvestment.com:29443",
        )

    def test_issue_token_uses_mock_token_endpoint(self):
        opener = _FakeOpener([{"access_token": "token-1"}])
        client = KisUsClient(self._config(), opener=opener)

        token = client.issue_token()

        self.assertEqual(token, "token-1")
        self.assertIn(KIS_US_TOKEN_PATH, opener.requests[0].full_url)

    def test_fetch_balance_uses_demo_tr_id_and_parses_positions_and_cash(self):
        opener = _FakeOpener(
            [
                {
                    "output1": {"frcr_pchs_amt1": "1000.00"},
                    "output2": [
                        {
                            "ovrs_pdno": "AAPL",
                            "ovrs_excg_cd": "NASD",
                            "ovrs_cblc_qty": "3",
                            "ovrs_stck_evlu_amt": "600.00",
                            "pchs_avg_pric": "150.00",
                        }
                    ],
                    "ctx_area_fk200": "",
                    "ctx_area_nk200": "",
                }
            ]
        )
        client = KisUsClient(self._config(), opener=opener, access_token="token-1")

        positions, cash = client.fetch_balance("NASD")

        self.assertEqual(cash, 1000.0)
        self.assertEqual(positions[0].symbol, "AAPL")
        self.assertEqual(positions[0].exchange, "NAS")
        self.assertEqual(positions[0].quantity, 3)
        request = opener.requests[0]
        self.assertIn(KIS_US_BALANCE_PATH, request.full_url)
        self.assertEqual(request.headers["tr_id"], KIS_US_BALANCE_TR_ID_DEMO)

    def test_fetch_quote_uses_price_tr_id_and_parses_price(self):
        opener = _FakeOpener([{"output": {"last": "191.25"}}])
        client = KisUsClient(self._config(), opener=opener, access_token="token-1")

        quote = client.fetch_quote("AAPL", "NAS")

        self.assertEqual(quote.symbol, "AAPL")
        self.assertEqual(quote.exchange, "NAS")
        self.assertEqual(quote.price, 191.25)
        request = opener.requests[0]
        self.assertIn(KIS_US_PRICE_PATH, request.full_url)
        self.assertEqual(request.headers["tr_id"], KIS_US_PRICE_TR_ID)

    def test_fetch_present_cash_uses_demo_tr_id_and_parses_usd_cash_candidates(self):
        opener = _FakeOpener(
            [
                {
                    "output1": [{"pdno": "AAPL", "cblc_qty13": "1"}],
                    "output2": [{"crcy_cd": "USD", "frcr_dncl_amt_2": "1250.50"}],
                    "output3": {"frcr_use_psbl_amt": "1200.00", "tot_dncl_amt": "1300.00"},
                }
            ]
        )
        client = KisUsClient(self._config(), opener=opener, access_token="token-1")

        cash = client.fetch_present_cash_usd()

        self.assertEqual(cash, 1300.0)
        request = opener.requests[0]
        self.assertIn(KIS_US_PRESENT_BALANCE_PATH, request.full_url)
        self.assertEqual(request.headers["tr_id"], KIS_US_PRESENT_BALANCE_TR_ID_DEMO)
        self.assertIn("WCRC_FRCR_DVSN_CD=02", request.full_url)
        self.assertIn("NATN_CD=000", request.full_url)

    def test_fetch_integrated_margin_cash_uses_read_only_tr_and_parses_usd_orderable_cash(self):
        opener = _FakeOpener(
            [
                {
                    "output": {
                        "usd_ord_psbl_amt": "100000.00",
                        "usd_itgr_ord_psbl_amt": "99500.00",
                        "usd_gnrl_ord_psbl_amt": "0",
                    }
                }
            ]
        )
        client = KisUsClient(self._config(), opener=opener, access_token="token-1")

        cash = client.fetch_integrated_margin_cash_usd()

        self.assertEqual(cash, 100000.0)
        request = opener.requests[0]
        self.assertIn(KIS_US_INTEGRATED_MARGIN_PATH, request.full_url)
        self.assertEqual(request.headers["tr_id"], KIS_US_INTEGRATED_MARGIN_TR_ID)
        self.assertIn("CMA_EVLU_AMT_ICLD_YN=N", request.full_url)

    def test_client_exposes_no_order_methods(self):
        names = {name for name in dir(KisUsClient) if "order" in name.lower() or "buy" in name.lower() or "sell" in name.lower()}
        self.assertEqual(names, set())


if __name__ == "__main__":
    unittest.main()
