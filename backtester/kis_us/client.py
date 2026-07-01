import json
import urllib.parse
import urllib.request
from typing import Any, Callable

from .models import KisUsConfig, KisUsPosition, KisUsQuote


KIS_US_TOKEN_PATH = "/oauth2/tokenP"
KIS_US_INTEGRATED_MARGIN_PATH = "/uapi/domestic-stock/v1/trading/intgr-margin"
KIS_US_BALANCE_PATH = "/uapi/overseas-stock/v1/trading/inquire-balance"
KIS_US_PRESENT_BALANCE_PATH = "/uapi/overseas-stock/v1/trading/inquire-present-balance"
KIS_US_PSAMOUNT_PATH = "/uapi/overseas-stock/v1/trading/inquire-psamount"
KIS_US_PRICE_PATH = "/uapi/overseas-price/v1/quotations/price"
KIS_US_INTEGRATED_MARGIN_TR_ID = "TTTC0869R"
KIS_US_BALANCE_TR_ID_DEMO = "VTTS3012R"
KIS_US_PRESENT_BALANCE_TR_ID_DEMO = "VTRP6504R"
KIS_US_PSAMOUNT_TR_ID_DEMO = "VTTS3007R"
KIS_US_PRICE_TR_ID = "HHDFS00000300"

BALANCE_TO_QUOTE_EXCHANGE = {
    "NASD": "NAS",
    "NYSE": "NYS",
    "AMEX": "AMS",
}
QUOTE_TO_BALANCE_EXCHANGE = {quote: balance for balance, quote in BALANCE_TO_QUOTE_EXCHANGE.items()}


class KisUsClient:
    def __init__(
        self,
        config: KisUsConfig,
        *,
        opener: Callable[..., Any] | None = None,
        access_token: str | None = None,
    ) -> None:
        self.config = config
        self._opener = opener or urllib.request.urlopen
        self._access_token = access_token

    def issue_token(self) -> str:
        body = json.dumps(
            {
                "grant_type": "client_credentials",
                "appkey": self.config.app_key,
                "appsecret": self.config.app_secret,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.mock_base_url}{KIS_US_TOKEN_PATH}",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        payload = self._request_json(request)
        self._access_token = str(payload["access_token"])
        return self._access_token

    def fetch_balance(self, exchange: str) -> tuple[list[KisUsPosition], float]:
        token = self._ensure_token()
        params = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_product_code,
            "OVRS_EXCG_CD": exchange,
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": "",
        }
        request = self._request(
            f"{KIS_US_BALANCE_PATH}?{urllib.parse.urlencode(params)}",
            token=token,
            tr_id=KIS_US_BALANCE_TR_ID_DEMO,
        )
        payload = self._request_json(request)
        cash = _parse_float(_first_value(_as_mapping(payload.get("output1")), ["frcr_pchs_amt1", "frcr_dncl_amt_2", "cash_usd"]))
        rows = payload.get("output2", [])
        if isinstance(rows, dict):
            rows = [rows]
        positions = [_position_from_row(row) for row in rows if isinstance(row, dict)]
        return [position for position in positions if position.quantity > 0], cash

    def fetch_present_cash_usd(self) -> float:
        token = self._ensure_token()
        params = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_product_code,
            "WCRC_FRCR_DVSN_CD": "02",
            "NATN_CD": "000",
            "TR_MKET_CD": "00",
            "INQR_DVSN_CD": "00",
        }
        request = self._request(
            f"{KIS_US_PRESENT_BALANCE_PATH}?{urllib.parse.urlencode(params)}",
            token=token,
            tr_id=KIS_US_PRESENT_BALANCE_TR_ID_DEMO,
        )
        payload = self._request_json(request)
        return _parse_present_cash_usd(payload)

    def fetch_integrated_margin_cash_usd(self) -> float:
        token = self._ensure_token()
        params = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_product_code,
            "CMA_EVLU_AMT_ICLD_YN": "N",
            "WCRC_FRCR_DVSN_CD": "01",
            "FWEX_CTRT_FRCR_DVSN_CD": "01",
        }
        request = self._request(
            f"{KIS_US_INTEGRATED_MARGIN_PATH}?{urllib.parse.urlencode(params)}",
            token=token,
            tr_id=KIS_US_INTEGRATED_MARGIN_TR_ID,
        )
        payload = self._request_json(request)
        return _parse_integrated_margin_cash_usd(payload)

    def fetch_quote(self, symbol: str, exchange: str) -> KisUsQuote:
        token = self._ensure_token()
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol,
        }
        request = self._request(
            f"{KIS_US_PRICE_PATH}?{urllib.parse.urlencode(params)}",
            token=token,
            tr_id=KIS_US_PRICE_TR_ID,
        )
        payload = self._request_json(request)
        output = payload.get("output", {})
        if isinstance(output, list):
            output = output[0] if output else {}
        price = _parse_float(
            _first_value(
                _as_mapping(output),
                ["last", "stck_prpr", "ovrs_stck_prpr", "base", "close"],
            )
        )
        return KisUsQuote(symbol=str(symbol).strip().upper(), exchange=str(exchange).strip().upper(), price=price)

    def fetch_psamount_usd(self, symbol: str, exchange: str, reference_price: float) -> float:
        token = self._ensure_token()
        normalized_exchange = str(exchange).strip().upper()
        psamount_exchange = QUOTE_TO_BALANCE_EXCHANGE.get(normalized_exchange, normalized_exchange)
        params = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_product_code,
            "OVRS_EXCG_CD": psamount_exchange,
            "OVRS_ORD_UNPR": _format_kis_decimal(reference_price),
            "ITEM_CD": str(symbol).strip().upper(),
        }
        request = self._request(
            f"{KIS_US_PSAMOUNT_PATH}?{urllib.parse.urlencode(params)}",
            token=token,
            tr_id=KIS_US_PSAMOUNT_TR_ID_DEMO,
        )
        payload = self._request_json(request)
        output = payload.get("output", {})
        if isinstance(output, list):
            output = output[0] if output else {}
        if not isinstance(output, dict):
            return 0.0
        return _parse_float(_first_value(output, ["ord_psbl_frcr_amt", "ovrs_ord_psbl_amt", "frcr_ord_psbl_amt1"]))

    def _ensure_token(self) -> str:
        return self._access_token or self.issue_token()

    def _request(self, path_and_query: str, *, token: str, tr_id: str) -> urllib.request.Request:
        request = urllib.request.Request(
            f"{self.config.mock_base_url}{path_and_query}",
            headers={
                "authorization": f"Bearer {token}",
                "appkey": self.config.app_key,
                "appsecret": self.config.app_secret,
                "tr_id": tr_id,
                "custtype": "P",
            },
            method="GET",
        )
        request.headers["tr_id"] = tr_id
        return request

    def _request_json(self, request: urllib.request.Request) -> dict[str, Any]:
        with self._opener(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


def _position_from_row(row: dict[str, Any]) -> KisUsPosition:
    symbol = str(_first_value(row, ["ovrs_pdno", "pdno", "symbol"])).strip().upper()
    raw_exchange = str(_first_value(row, ["ovrs_excg_cd", "excg_cd", "exchange"])).strip().upper()
    exchange = BALANCE_TO_QUOTE_EXCHANGE.get(raw_exchange, raw_exchange)
    quantity = int(_parse_float(_first_value(row, ["ovrs_cblc_qty", "hldg_qty", "qty", "quantity"])))
    market_value = _parse_float(_first_value(row, ["ovrs_stck_evlu_amt", "evlu_amt", "market_value", "amount"]))
    average_price = _parse_float(_first_value(row, ["pchs_avg_pric", "avg_price", "average_price"]))
    return KisUsPosition(
        symbol=symbol,
        exchange=exchange,
        quantity=quantity,
        market_value=market_value,
        average_price=average_price,
    )


def _parse_present_cash_usd(payload: dict[str, Any]) -> float:
    candidates: list[float] = []
    for output_key in ("output2", "output3"):
        rows = payload.get(output_key, [])
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            crcy_cd = str(_first_value(row, ["crcy_cd", "buy_crcy_cd"])).strip().upper()
            if crcy_cd and crcy_cd not in {"USD", "0"}:
                continue
            candidates.extend(
                _parse_float(_first_value(row, [field]))
                for field in [
                    "frcr_dncl_amt_2",
                    "frcr_use_psbl_amt",
                    "frcr_drwg_psbl_amt_1",
                    "nxdy_frcr_drwg_psbl_amt",
                    "tot_dncl_amt",
                    "dncl_amt",
                ]
            )
    return max([value for value in candidates if value > 0], default=0.0)


def _parse_integrated_margin_cash_usd(payload: dict[str, Any]) -> float:
    output = payload.get("output", {})
    if isinstance(output, list):
        output = output[0] if output else {}
    if not isinstance(output, dict):
        return 0.0
    candidates = [
        _parse_float(_first_value(output, [field]))
        for field in [
            "usd_ord_psbl_amt",
            "usd_itgr_ord_psbl_amt",
            "usd_gnrl_ord_psbl_amt",
            "usd_ruse_ord_psbl_amt",
            "usd_objt_amt",
        ]
    ]
    return max([value for value in candidates if value > 0], default=0.0)


def _first_value(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return 0


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _format_kis_decimal(value: float) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
