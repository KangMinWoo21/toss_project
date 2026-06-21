import csv
import json
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree


DART_CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DART_FINANCIAL_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
DART_EVENT_COLUMNS = ["date", "symbol", "source", "title", "sentiment_score", "importance_score"]
DART_FINANCIAL_COLUMNS = [
    "symbol",
    "corp_code",
    "business_year",
    "report_code",
    "fs_div",
    "statement_name",
    "account_name",
    "current_amount",
    "previous_amount",
    "currency",
    "ord",
]

NEGATIVE_DISCLOSURE_TERMS = {
    "감사의견",
    "감자",
    "관리종목",
    "거래정지",
    "불성실공시",
    "상장폐지",
    "소송",
    "신주인수권부사채",
    "유상증자",
    "전환사채",
    "투자경고",
    "투자위험",
    "투자주의",
    "파산",
    "횡령",
    "배임",
}

POSITIVE_DISCLOSURE_TERMS = {
    "공급계약",
    "무상증자",
    "수주",
    "실적",
    "영업실적",
    "자기주식취득",
    "현금배당",
}

HIGH_IMPORTANCE_TERMS = NEGATIVE_DISCLOSURE_TERMS | POSITIVE_DISCLOSURE_TERMS


@dataclass(frozen=True)
class DartCorpCode:
    corp_code: str
    corp_name: str
    stock_code: str
    modify_date: str


@dataclass(frozen=True)
class DartDisclosureRow:
    date: str
    symbol: str
    corp_name: str
    report_name: str
    receipt_no: str


def fetch_dart_disclosures(
    api_key: str,
    symbol: str,
    start: str,
    end: str,
    page_count: int = 100,
) -> list[DartDisclosureRow]:
    corp_codes = fetch_dart_corp_codes(api_key)
    corp_code = corp_code_for_symbol(corp_codes, symbol)
    return fetch_dart_disclosures_for_corp_code(
        api_key=api_key,
        symbol=symbol,
        corp_code=corp_code,
        start=start,
        end=end,
        page_count=page_count,
    )


def fetch_dart_disclosures_for_symbols(
    api_key: str,
    symbols: list[str],
    start: str,
    end: str,
    page_count: int = 100,
) -> list[DartDisclosureRow]:
    corp_codes = fetch_dart_corp_codes(api_key)
    rows: list[DartDisclosureRow] = []
    for symbol in symbols:
        corp_code = corp_code_for_symbol(corp_codes, symbol)
        rows.extend(
            fetch_dart_disclosures_for_corp_code(
                api_key=api_key,
                symbol=symbol,
                corp_code=corp_code,
                start=start,
                end=end,
                page_count=page_count,
            )
        )
    return rows


def fetch_dart_disclosures_for_corp_code(
    api_key: str,
    symbol: str,
    corp_code: str,
    start: str,
    end: str,
    page_count: int = 100,
    list_fetcher: Callable[..., dict[str, Any]] | None = None,
) -> list[DartDisclosureRow]:
    fetcher = list_fetcher or fetch_dart_list_payload
    first_payload = fetcher(
        api_key=api_key,
        corp_code=corp_code,
        start=start,
        end=end,
        page_count=page_count,
        page_no=1,
    )
    rows = normalize_dart_list_payload(symbol, first_payload)
    total_page = int(first_payload.get("total_page") or 1)
    for page_no in range(2, total_page + 1):
        payload = fetcher(
            api_key=api_key,
            corp_code=corp_code,
            start=start,
            end=end,
            page_count=page_count,
            page_no=page_no,
        )
        rows.extend(normalize_dart_list_payload(symbol, payload))
    return rows


def fetch_dart_corp_codes(api_key: str) -> list[DartCorpCode]:
    params = urllib.parse.urlencode({"crtfc_key": api_key})
    request = urllib.request.Request(f"{DART_CORP_CODE_URL}?{params}", method="GET")
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    return parse_dart_corp_codes(raw)


def fetch_dart_financial_rows_for_symbols(
    api_key: str,
    symbols: list[str],
    *,
    business_year: str,
    report_code: str = "11011",
    fs_div: str = "CFS",
) -> list[dict[str, Any]]:
    corp_codes = fetch_dart_corp_codes(api_key)
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        corp_code = corp_code_for_symbol(corp_codes, symbol)
        rows.extend(
            fetch_dart_financial_rows_for_corp_code(
                api_key=api_key,
                symbol=symbol,
                corp_code=corp_code,
                business_year=business_year,
                report_code=report_code,
                fs_div=fs_div,
            )
        )
    return rows


def fetch_dart_financial_rows_for_corp_code(
    api_key: str,
    symbol: str,
    corp_code: str,
    *,
    business_year: str,
    report_code: str = "11011",
    fs_div: str = "CFS",
    financial_fetcher: Callable[..., dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    fetcher = financial_fetcher or fetch_dart_financial_payload
    payload = fetcher(
        api_key=api_key,
        corp_code=corp_code,
        business_year=business_year,
        report_code=report_code,
        fs_div=fs_div,
    )
    return normalize_dart_financial_payload(symbol, payload)


def fetch_dart_financial_payload(
    api_key: str,
    corp_code: str,
    business_year: str,
    report_code: str = "11011",
    fs_div: str = "CFS",
) -> dict[str, Any]:
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": str(business_year),
        "reprt_code": report_code,
        "fs_div": fs_div,
    }
    url = f"{DART_FINANCIAL_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_dart_financial_payload(symbol: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(payload.get("status", ""))
    if status and status not in {"000", "013"}:
        message = payload.get("message", "unknown OpenDART error")
        raise RuntimeError(f"OpenDART error {status}: {message}")

    rows: list[dict[str, Any]] = []
    for item in payload.get("list", []):
        rows.append(
            {
                "symbol": str(item.get("stock_code") or symbol).strip() or symbol,
                "corp_code": str(item.get("corp_code", "")).strip(),
                "business_year": str(item.get("bsns_year", "")).strip(),
                "report_code": str(item.get("reprt_code", "")).strip(),
                "fs_div": str(item.get("fs_div", "")).strip(),
                "statement_name": str(item.get("sj_nm", "")).strip(),
                "account_name": str(item.get("account_nm", "")).strip(),
                "current_amount": _amount(item.get("thstrm_amount", 0)),
                "previous_amount": _amount(item.get("frmtrm_amount", 0)),
                "currency": str(item.get("currency", "")).strip(),
                "ord": str(item.get("ord", "")).strip(),
            }
        )
    return rows


def parse_dart_corp_codes(zip_bytes: bytes) -> list[DartCorpCode]:
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        xml_name = zf.namelist()[0]
        root = ElementTree.fromstring(zf.read(xml_name))

    rows: list[DartCorpCode] = []
    for item in root.findall("list"):
        stock_code = (item.findtext("stock_code") or "").strip()
        if not stock_code:
            continue
        rows.append(
            DartCorpCode(
                corp_code=(item.findtext("corp_code") or "").strip(),
                corp_name=(item.findtext("corp_name") or "").strip(),
                stock_code=stock_code,
                modify_date=(item.findtext("modify_date") or "").strip(),
            )
        )
    return rows


def corp_code_for_symbol(corp_codes: list[DartCorpCode], symbol: str) -> str:
    normalized_symbol = _normalize_symbol_code(symbol)
    for row in corp_codes:
        if _normalize_symbol_code(row.stock_code) == normalized_symbol:
            return row.corp_code
    raise ValueError(f"DART corp_code not found for symbol: {symbol}")


def fetch_dart_list_payload(
    api_key: str,
    corp_code: str,
    start: str,
    end: str,
    page_count: int = 100,
    page_no: int = 1,
) -> dict[str, Any]:
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": _compact_date(start),
        "end_de": _compact_date(end),
        "page_no": str(page_no),
        "page_count": str(page_count),
        "sort": "date",
        "sort_mth": "desc",
    }
    url = f"{DART_LIST_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_dart_list_payload(symbol: str, payload: dict[str, Any]) -> list[DartDisclosureRow]:
    status = str(payload.get("status", ""))
    if status and status not in {"000", "013"}:
        message = payload.get("message", "unknown OpenDART error")
        raise RuntimeError(f"OpenDART error {status}: {message}")

    rows: list[DartDisclosureRow] = []
    for item in payload.get("list", []):
        report_name = str(item.get("report_nm", "")).strip()
        receipt_date = str(item.get("rcept_dt", "")).strip()
        if not report_name or not receipt_date:
            continue
        rows.append(
            DartDisclosureRow(
                date=_dash_date(receipt_date),
                symbol=str(item.get("stock_code") or symbol).strip() or symbol,
                corp_name=str(item.get("corp_name", "unknown")).strip() or "unknown",
                report_name=report_name,
                receipt_no=str(item.get("rcept_no", "")).strip(),
            )
        )
    return rows


def disclosure_rows_to_event_rows(disclosures: list[DartDisclosureRow]) -> list[list[object]]:
    rows: list[list[object]] = []
    for disclosure in disclosures:
        sentiment, importance = classify_dart_disclosure(disclosure.report_name)
        title = disclosure.report_name
        if disclosure.receipt_no:
            title = f"{title} [{disclosure.receipt_no}]"
        rows.append(
            [
                disclosure.date,
                disclosure.symbol,
                f"dart:{disclosure.corp_name}",
                title,
                sentiment,
                importance,
            ]
        )
    return rows


def save_dart_event_rows(rows: list[list[object]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(DART_EVENT_COLUMNS)
        writer.writerows(rows)
    return len(rows)


def save_dart_financial_rows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DART_FINANCIAL_COLUMNS)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in DART_FINANCIAL_COLUMNS} for row in rows)
    return len(rows)


def classify_dart_disclosure(report_name: str) -> tuple[float, float]:
    normalized = report_name.casefold()
    negative_hits = sum(1 for term in NEGATIVE_DISCLOSURE_TERMS if term.casefold() in normalized)
    positive_hits = sum(1 for term in POSITIVE_DISCLOSURE_TERMS if term.casefold() in normalized)
    raw_score = positive_hits - negative_hits
    if raw_score > 0:
        sentiment = min(1.0, raw_score * 0.45)
    elif raw_score < 0:
        sentiment = max(-1.0, raw_score * 0.45)
    else:
        sentiment = 0.0
    importance = 1.5 if any(term.casefold() in normalized for term in HIGH_IMPORTANCE_TERMS) else 1.0
    return sentiment, importance


def _compact_date(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())[:8]


def _dash_date(value: str) -> str:
    digits = _compact_date(value)
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return value


def _amount(value: Any) -> float:
    text = str(value or "0").replace(",", "").strip()
    if text in {"", "-"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _normalize_symbol_code(value: Any) -> str:
    text = str(value).strip().strip("'").strip('"')
    if not text:
        return ""
    if text.isdigit():
        return text.zfill(6)
    return text.upper()
