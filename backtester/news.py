import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree


GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"

POSITIVE_TERMS = {
    "beat",
    "beats",
    "boom",
    "breakthrough",
    "gain",
    "gains",
    "growth",
    "improve",
    "improves",
    "profit",
    "record",
    "rise",
    "rises",
    "strong",
    "surge",
    "surges",
    "up",
    "upgrade",
    "호조",
    "급등",
    "상승",
    "성장",
    "실적",
}

NEGATIVE_TERMS = {
    "ban",
    "cut",
    "decline",
    "delay",
    "drop",
    "falls",
    "fall",
    "loss",
    "miss",
    "probe",
    "risk",
    "slump",
    "weak",
    "warning",
    "규제",
    "급락",
    "부진",
    "손실",
    "위험",
    "하락",
}


def fetch_gdelt_articles(
    query: str,
    start: str | None = None,
    end: str | None = None,
    max_records: int = 100,
) -> dict[str, Any]:
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(max_records),
        "sort": "datedesc",
    }
    if start:
        params["startdatetime"] = _to_gdelt_datetime(start, end_of_day=False)
    if end:
        params["enddatetime"] = _to_gdelt_datetime(end, end_of_day=True)
    url = f"{GDELT_DOC_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_google_news_rss(query: str, language: str = "ko", country: str = "KR") -> str:
    params = {
        "q": query,
        "hl": f"{language}-{country}",
        "gl": country,
        "ceid": f"{country}:{language}",
    }
    url = f"{GOOGLE_NEWS_RSS_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def articles_to_event_rows(payload: dict[str, Any], symbol: str) -> list[list[object]]:
    rows: list[list[object]] = []
    for article in payload.get("articles", []):
        title = str(article.get("title", "")).strip()
        if not title:
            continue
        date = _date_from_seen(str(article.get("seendate", "")))
        domain = str(article.get("domain", "unknown")).strip() or "unknown"
        rows.append(
            [
                date,
                symbol,
                f"gdelt:{domain}",
                title,
                score_title_sentiment(title),
                1.0,
            ]
        )
    return rows


def rss_to_event_rows(rss_text: str, symbol: str) -> list[list[object]]:
    root = ElementTree.fromstring(rss_text)
    rows: list[list[object]] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        pub_date = (item.findtext("pubDate") or "").strip()
        source = item.findtext("source") or "unknown"
        rows.append(
            [
                _date_from_rss(pub_date),
                symbol,
                f"google-news:{source}",
                title,
                score_title_sentiment(title),
                1.0,
            ]
        )
    return rows


def save_event_rows(rows: list[list[object]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "symbol", "source", "title", "sentiment_score", "importance_score"])
        writer.writerows(rows)
    return len(rows)


def score_title_sentiment(title: str) -> float:
    lowered = title.casefold()
    positive = sum(1 for term in POSITIVE_TERMS if term.casefold() in lowered)
    negative = sum(1 for term in NEGATIVE_TERMS if term.casefold() in lowered)
    raw = positive - negative
    if raw > 0:
        return min(1.0, raw * 0.35)
    if raw < 0:
        return max(-1.0, raw * 0.35)
    return 0.0


def _to_gdelt_datetime(value: str, end_of_day: bool) -> str:
    digits = value.replace("-", "")
    suffix = "235959" if end_of_day else "000000"
    return f"{digits}{suffix}"


def _date_from_seen(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return value[:10]


def _date_from_rss(value: str) -> str:
    if not value:
        return ""
    return parsedate_to_datetime(value).date().isoformat()
