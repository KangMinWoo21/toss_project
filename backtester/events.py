import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass(frozen=True)
class EventScoreStore:
    scores: dict[tuple[str, str], float]

    def score(self, symbol: str, date: str) -> float:
        return self.scores.get((symbol, date), 0.0)

    def score_window(self, symbol: str, date: str, lookback_days: int) -> float:
        if lookback_days <= 0:
            return self.score(symbol, date)
        target_date = _parse_date(date)
        start_date = target_date - timedelta(days=lookback_days)
        values = [
            score
            for (row_symbol, row_date), score in self.scores.items()
            if row_symbol == symbol and start_date <= _parse_date(row_date) <= target_date
        ]
        if not values:
            return 0.0
        return sum(values) / len(values)


def load_event_scores(path: Path | str) -> EventScoreStore:
    csv_path = Path(path)
    weighted_scores: dict[tuple[str, str], list[tuple[float, float]]] = {}
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"date", "symbol", "sentiment_score", "importance_score"}
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header")
        missing = required.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(sorted(missing))}")

        for row in reader:
            key = (row["symbol"], row["date"])
            sentiment = float(row["sentiment_score"])
            importance = max(float(row["importance_score"]), 0.0)
            weighted_scores.setdefault(key, []).append((sentiment, importance))

    scores = {
        key: _weighted_average(values)
        for key, values in weighted_scores.items()
    }
    return EventScoreStore(scores)


def _weighted_average(values: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in values)
    if total_weight == 0:
        return 0.0
    return sum(score * weight for score, weight in values) / total_weight


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)
