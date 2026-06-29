import csv
from dataclasses import dataclass
from pathlib import Path


ORDER_PLAN_COLUMNS = [
    "plan_id",
    "rebalance_date",
    "symbol",
    "side",
    "current_weight",
    "target_weight",
    "target_amount",
    "estimated_quantity",
    "reference_price",
    "reason",
    "risk_status",
    "risk_reasons",
    "created_at",
]


@dataclass(frozen=True)
class OrderPlanRow:
    plan_id: str
    rebalance_date: str
    symbol: str
    side: str
    current_weight: float
    target_weight: float
    target_amount: float
    estimated_quantity: int
    reference_price: float
    reason: str
    risk_status: str
    risk_reasons: str
    created_at: str


def save_order_plan_rows(rows: list[OrderPlanRow], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=ORDER_PLAN_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in ORDER_PLAN_COLUMNS})
    return len(rows)


def load_order_plan(path: Path | str) -> list[OrderPlanRow]:
    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header")
        missing = set(ORDER_PLAN_COLUMNS).difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(sorted(missing))}")
        return [_row_from_csv(row) for row in reader]


def _row_from_csv(row: dict[str, str]) -> OrderPlanRow:
    return OrderPlanRow(
        plan_id=str(row.get("plan_id", "")),
        rebalance_date=str(row.get("rebalance_date", "")),
        symbol=str(row.get("symbol", "")),
        side=str(row.get("side", "")),
        current_weight=float(row.get("current_weight", 0) or 0),
        target_weight=float(row.get("target_weight", 0) or 0),
        target_amount=float(row.get("target_amount", 0) or 0),
        estimated_quantity=int(float(row.get("estimated_quantity", 0) or 0)),
        reference_price=float(row.get("reference_price", 0) or 0),
        reason=str(row.get("reason", "")),
        risk_status=str(row.get("risk_status", "")),
        risk_reasons=str(row.get("risk_reasons", "")),
        created_at=str(row.get("created_at", "")),
    )
