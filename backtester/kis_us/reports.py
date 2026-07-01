import csv
from pathlib import Path

from .models import KisUsPlannedOrder


KIS_US_ORDER_COLUMNS = [
    "plan_id",
    "as_of",
    "symbol",
    "exchange",
    "side",
    "quantity",
    "current_quantity",
    "target_weight",
    "current_weight",
    "reference_price",
    "estimated_value",
    "risk_status",
    "risk_reasons",
    "paper_only",
    "dry_run",
    "execution_allowed",
    "production_effect",
    "created_at",
]


def save_kis_us_order_plan(rows: list[KisUsPlannedOrder], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=KIS_US_ORDER_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in KIS_US_ORDER_COLUMNS})
    return len(rows)


def save_kis_us_order_summary(
    rows: list[KisUsPlannedOrder],
    output_path: Path | str,
    *,
    as_of: str,
    cash_usd: float,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blocked = [row for row in rows if row.risk_status != "PASS"]
    buys = [row for row in rows if row.side == "BUY"]
    sells = [row for row in rows if row.side == "SELL"]
    lines = [
        "# KIS US Paper-Only Order Plan",
        "",
        "Status: paper-only / dry-run / no order submitted",
        f"As of: {as_of}",
        f"Cash USD: {cash_usd:.2f}",
        f"Rows: {len(rows)}",
        f"BUY rows: {len(buys)}",
        f"SELL rows: {len(sells)}",
        f"Blocked rows: {len(blocked)}",
        "",
        "## Safety",
        "",
        "- paper_only is always True.",
        "- dry_run is always True.",
        "- execution_allowed is always False.",
        "- production_effect is always none.",
        "- This report does not submit broker orders.",
        "",
        "## Orders",
        "",
        "| symbol | exchange | side | quantity | risk_status | risk_reasons |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.symbol} | {row.exchange} | {row.side} | {row.quantity} | {row.risk_status} | {row.risk_reasons} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
