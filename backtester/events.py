import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


EVENT_COLUMNS = [
    "date",
    "event_date",
    "available_date",
    "symbol",
    "source",
    "title",
    "sentiment_score",
    "importance_score",
]


@dataclass(frozen=True)
class EventScoreStore:
    scores: dict[tuple[str, str], float]
    warnings: tuple[str, ...] = ()

    def score(self, symbol: str, date: str) -> float:
        return self.scores.get((symbol, date), 0.0)

    def score_window(self, symbol: str, date: str, lookback_days: int, *, include_target_date: bool = True) -> float:
        if lookback_days <= 0:
            if not include_target_date:
                return 0.0
            return self.score(symbol, date)
        target_date = _parse_date(date)
        start_date = target_date - timedelta(days=lookback_days)
        values = [
            score
            for (row_symbol, row_date), score in self.scores.items()
            if row_symbol == symbol
            and start_date <= _parse_date(row_date)
            and (
                _parse_date(row_date) <= target_date
                if include_target_date
                else _parse_date(row_date) < target_date
            )
        ]
        if not values:
            return 0.0
        return sum(values) / len(values)


def load_event_scores(path: Path | str, source_weights: dict[str, float] | None = None) -> EventScoreStore:
    csv_path = Path(path)
    weighted_scores: dict[tuple[str, str], list[tuple[float, float]]] = {}
    warnings: list[str] = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"symbol", "sentiment_score", "importance_score"}
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header")
        missing = required.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(sorted(missing))}")

        for index, row in enumerate(reader, start=2):
            available_date = _available_date(row, warnings=warnings, row_number=index)
            if not available_date:
                continue
            if not _is_iso_date(available_date):
                warnings.append(f"row {index} invalid available_date: {available_date}")
                continue
            try:
                sentiment = float(row["sentiment_score"])
                importance_score = float(row["importance_score"])
            except (TypeError, ValueError):
                warnings.append(f"row {index} invalid event score")
                continue
            key = (row["symbol"], available_date)
            importance = max(importance_score, 0.0) * _source_weight(row.get("source", ""), source_weights)
            weighted_scores.setdefault(key, []).append((sentiment, importance))

    scores = {
        key: _weighted_average(values)
        for key, values in weighted_scores.items()
    }
    return EventScoreStore(scores, tuple(warnings))


def merge_event_files(input_paths: list[Path | str], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    saved = 0
    seen: set[tuple[str, ...]] = set()

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EVENT_COLUMNS)
        writer.writeheader()
        for input_path in input_paths:
            for row in _read_event_rows(input_path):
                dedupe_key = tuple(str(row.get(column, "")) for column in EVENT_COLUMNS)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                writer.writerow(row)
                saved += 1

    return saved


def _read_event_rows(input_path: Path | str) -> list[dict[str, str]]:
    csv_path = Path(input_path)
    rows: list[dict[str, str]] = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header")
        missing = {"symbol", "sentiment_score", "importance_score"}.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(sorted(missing))}")

        for row in reader:
            normalized = {column: str(row.get(column, "")).strip() for column in EVENT_COLUMNS}
            if not normalized["event_date"]:
                normalized["event_date"] = normalized["date"]
            if not normalized["available_date"]:
                normalized["available_date"] = normalized["event_date"] or normalized["date"]
            if not normalized["date"]:
                normalized["date"] = normalized["event_date"] or normalized["available_date"]
            if normalized["symbol"] and (normalized["available_date"] or normalized["event_date"] or normalized["date"]):
                rows.append(normalized)
    return rows


def _weighted_average(values: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in values)
    if total_weight == 0:
        return 0.0
    return sum(score * weight for score, weight in values) / total_weight


def _source_weight(source: str, source_weights: dict[str, float] | None) -> float:
    if not source_weights:
        return 1.0
    normalized = source.strip()
    if normalized in source_weights:
        return max(float(source_weights[normalized]), 0.0)
    prefix = normalized.split(":", 1)[0]
    if prefix in source_weights:
        return max(float(source_weights[prefix]), 0.0)
    return 1.0


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _available_date(row: dict[str, str], *, warnings: list[str], row_number: int) -> str:
    available = str(row.get("available_date", "")).strip()
    if available:
        return available
    event_date = str(row.get("event_date", "")).strip()
    if event_date:
        warnings.append(f"row {row_number} missing available_date; using event_date")
        return event_date
    legacy_date = str(row.get("date", "")).strip()
    if legacy_date:
        warnings.append(f"row {row_number} missing available_date; using legacy date")
        return legacy_date
    warnings.append(f"row {row_number} missing available_date/event_date/date")
    return ""


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
