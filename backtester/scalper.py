import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class OrderbookLevel:
    price: float
    volume: float


@dataclass(frozen=True)
class TickSnapshot:
    timestamp: str
    last_price: float
    recent_trade_volume: float
    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]


@dataclass(frozen=True)
class ScalperConfig:
    volume_spike_multiplier: float = 3.0
    bid_ask_imbalance_threshold: float = 1.5
    max_spread_pct: float = 0.2
    take_profit_pct: float = 0.8
    stop_loss_pct: float = -1.0
    max_hold_ticks: int = 120


@dataclass(frozen=True)
class ScalpSignal:
    action: str
    reason: str


def decide_scalp_signal(
    history: list[TickSnapshot],
    current: TickSnapshot,
    position: dict[str, object] | None,
    config: ScalperConfig,
) -> ScalpSignal:
    if position is not None:
        entry_price = float(position["entry_price"])
        pnl_pct = (current.last_price / entry_price - 1) * 100
        if pnl_pct >= config.take_profit_pct:
            return ScalpSignal("SELL", f"take_profit {pnl_pct:.2f}%")
        if pnl_pct <= config.stop_loss_pct:
            return ScalpSignal("SELL", f"stop_loss {pnl_pct:.2f}%")
        return ScalpSignal("HOLD", "position_open")

    if len(history) < 1:
        return ScalpSignal("HOLD", "need_history")

    avg_volume = sum(s.recent_trade_volume for s in history) / len(history)
    previous_price = history[-1].last_price
    volume_spike = avg_volume > 0 and current.recent_trade_volume >= avg_volume * config.volume_spike_multiplier
    price_rising = current.last_price > previous_price
    imbalance = _bid_ask_imbalance(current)
    spread_pct = _spread_pct(current)

    if spread_pct > config.max_spread_pct:
        return ScalpSignal("HOLD", f"spread_too_wide {spread_pct:.3f}%")

    if volume_spike and price_rising and imbalance >= config.bid_ask_imbalance_threshold:
        return ScalpSignal("BUY", f"volume_spike imbalance={imbalance:.2f}")
    return ScalpSignal("HOLD", "conditions_not_met")


def _bid_ask_imbalance(snapshot: TickSnapshot) -> float:
    bid_volume = sum(level.volume for level in snapshot.bids[:5])
    ask_volume = sum(level.volume for level in snapshot.asks[:5])
    if ask_volume <= 0:
        return float("inf")
    return bid_volume / ask_volume


def _spread_pct(snapshot: TickSnapshot) -> float:
    if not snapshot.bids or not snapshot.asks or snapshot.last_price <= 0:
        return 0.0
    return (snapshot.asks[0].price - snapshot.bids[0].price) / snapshot.last_price * 100


def run_paper_scalper(
    snapshot_fetcher: Callable[[], TickSnapshot],
    iterations: int,
    interval_seconds: float,
    output_path: Path | str,
    config: ScalperConfig | None = None,
    append: bool = False,
    required_date: str | None = None,
) -> list[dict[str, object]]:
    scalper_config = config or ScalperConfig()
    history: list[TickSnapshot] = []
    position: dict[str, object] | None = None
    rows: list[dict[str, object]] = []

    for tick in range(iterations):
        snapshot = snapshot_fetcher()
        if required_date and not snapshot.timestamp.startswith(required_date):
            if tick < iterations - 1 and interval_seconds > 0:
                time.sleep(interval_seconds)
            continue
        signal = decide_scalp_signal(history, snapshot, position, scalper_config)
        realized_pnl_pct = 0.0

        if signal.action == "BUY" and position is None:
            position = {"entry_price": snapshot.last_price, "entry_time": snapshot.timestamp, "entry_tick": tick}
        elif signal.action == "SELL" and position is not None:
            entry_price = float(position["entry_price"])
            realized_pnl_pct = (snapshot.last_price / entry_price - 1) * 100
            position = None

        metrics = snapshot_metrics(snapshot)
        rows.append(
            {
                "tick": tick,
                "timestamp": snapshot.timestamp,
                "last_price": snapshot.last_price,
                "recent_trade_volume": snapshot.recent_trade_volume,
                **metrics,
                "signal": signal.action,
                "reason": signal.reason,
                "position": "LONG" if position is not None else "FLAT",
                "realized_pnl_pct": round(realized_pnl_pct, 4),
            }
        )
        history.append(snapshot)
        history = history[-30:]
        if tick < iterations - 1 and interval_seconds > 0:
            time.sleep(interval_seconds)

    _write_paper_scalp_log(rows, output_path, append=append)
    return rows


def snapshot_metrics(snapshot: TickSnapshot) -> dict[str, float]:
    bid_volume_5 = sum(level.volume for level in snapshot.bids[:5])
    ask_volume_5 = sum(level.volume for level in snapshot.asks[:5])
    best_bid = snapshot.bids[0].price if snapshot.bids else 0.0
    best_ask = snapshot.asks[0].price if snapshot.asks else 0.0
    imbalance = float("inf") if ask_volume_5 <= 0 else bid_volume_5 / ask_volume_5
    spread = best_ask - best_bid if best_bid and best_ask else 0.0
    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread,
        "bid_volume_5": bid_volume_5,
        "ask_volume_5": ask_volume_5,
        "bid_ask_imbalance": imbalance,
    }


def _write_paper_scalp_log(rows: list[dict[str, object]], output_path: Path | str, append: bool = False) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tick",
        "timestamp",
        "last_price",
        "recent_trade_volume",
        "best_bid",
        "best_ask",
        "spread",
        "bid_volume_5",
        "ask_volume_5",
        "bid_ask_imbalance",
        "signal",
        "reason",
        "position",
        "realized_pnl_pct",
    ]
    needs_header = not append or not path.exists() or path.stat().st_size == 0
    with path.open("a" if append else "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        if needs_header:
            writer.writeheader()
        writer.writerows(rows)
