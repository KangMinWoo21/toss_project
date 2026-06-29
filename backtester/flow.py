import csv
from dataclasses import dataclass
from datetime import date as Date
from pathlib import Path


@dataclass(frozen=True)
class FlowScoreStore:
    scores: dict[tuple[str, str], float]

    def score(self, symbol: str, date: str) -> float:
        return self.scores.get((symbol, date), 0.0)

    def latest_score_before(self, symbol: str, date: str) -> float:
        target_date = Date.fromisoformat(date)
        prior = [
            (Date.fromisoformat(row_date), score)
            for (row_symbol, row_date), score in self.scores.items()
            if row_symbol == symbol and Date.fromisoformat(row_date) < target_date
        ]
        if not prior:
            return 0.0
        return max(prior, key=lambda row: row[0])[1]


def load_flow_scores(path: Path | str, scale_value: float = 100_000_000.0) -> FlowScoreStore:
    csv_path = Path(path)
    scores: dict[tuple[str, str], float] = {}
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {
            "date",
            "symbol",
            "foreign_net_value",
            "institution_net_value",
            "individual_net_value",
            "insider_buy_value",
            "insider_sell_value",
        }
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header")
        missing = required.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(sorted(missing))}")

        for row in reader:
            scores[(row["symbol"], row["date"])] = score_flow_row(
                foreign_net_value=float(row["foreign_net_value"]),
                institution_net_value=float(row["institution_net_value"]),
                individual_net_value=float(row["individual_net_value"]),
                insider_buy_value=float(row["insider_buy_value"]),
                insider_sell_value=float(row["insider_sell_value"]),
                scale_value=scale_value,
            )
    return FlowScoreStore(scores)


def score_flow_row(
    foreign_net_value: float,
    institution_net_value: float,
    individual_net_value: float,
    insider_buy_value: float,
    insider_sell_value: float,
    scale_value: float = 100_000_000.0,
) -> float:
    if scale_value <= 0:
        raise ValueError("scale_value must be positive")
    raw = (
        0.45 * _scaled(foreign_net_value, scale_value)
        + 0.35 * _scaled(institution_net_value, scale_value)
        - 0.10 * _scaled(max(individual_net_value, 0.0), scale_value)
        + 0.30 * _scaled(insider_buy_value, scale_value)
        - 0.50 * _scaled(insider_sell_value, scale_value)
    )
    return max(-1.0, min(1.0, raw))


def _scaled(value: float, scale_value: float) -> float:
    return max(-1.0, min(1.0, value / scale_value))
