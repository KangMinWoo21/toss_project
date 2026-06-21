import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from .models import Candle
from .momentum_rotation import (
    MomentumRotationConfig,
    MomentumRotationResult,
    _equal_weight_buy_hold_return,
    momentum_rotation_config_for_preset,
    run_momentum_rotation_backtest,
)


@dataclass(frozen=True)
class MomentumValidationWindow:
    name: str
    train_start: str
    train_end: str
    test_start: str
    test_end: str


VALIDATION_COLUMNS = [
    "window",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "selected_preset",
    "selection_score",
    "train_total_return_pct",
    "train_buy_hold_return_pct",
    "train_excess_return_pct",
    "train_max_drawdown_pct",
    "train_trades",
    "train_subwindows",
    "train_positive_subwindows",
    "train_positive_ratio",
    "train_avg_subwindow_excess_pct",
    "train_worst_subwindow_excess_pct",
    "test_total_return_pct",
    "test_buy_hold_return_pct",
    "test_excess_return_pct",
    "test_max_drawdown_pct",
    "test_trades",
    "accepted",
    "reject_reason",
    "train_symbols",
    "test_symbols",
]

DEPLOYMENT_GATE_COLUMNS = [
    "deployable",
    "reject_reason",
    "walk_windows",
    "accepted_windows",
    "accepted_ratio",
    "avg_test_excess_return_pct",
    "worst_test_excess_return_pct",
    "min_accepted_ratio",
    "min_avg_test_excess_pct",
    "min_worst_test_excess_pct",
]


def generate_yearly_walk_forward_windows(
    first_year: int,
    last_year: int,
    train_years: int,
    test_years: int,
    holdout_start: str | None = None,
) -> list[MomentumValidationWindow]:
    if train_years <= 0:
        raise ValueError("train_years must be positive")
    if test_years <= 0:
        raise ValueError("test_years must be positive")

    windows: list[MomentumValidationWindow] = []
    for train_start_year in range(first_year, last_year + 1):
        train_end_year = train_start_year + train_years - 1
        test_start_year = train_end_year + 1
        test_end_year = test_start_year + test_years - 1
        if test_end_year > last_year:
            break
        train_start = f"{train_start_year:04d}-01-01"
        train_end = f"{train_end_year:04d}-12-31"
        test_start = f"{test_start_year:04d}-01-01"
        test_end = f"{test_end_year:04d}-12-31"
        if holdout_start and test_end >= holdout_start:
            break
        windows.append(
            MomentumValidationWindow(
                name=f"train_{train_start_year}_{train_end_year}_test_{test_start_year}_{test_end_year}",
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
    return windows


def generate_calendar_year_subwindows(start: str, end: str) -> list[MomentumValidationWindow]:
    start_year = date.fromisoformat(start).year
    end_year = date.fromisoformat(end).year
    windows: list[MomentumValidationWindow] = []
    for year in range(start_year, end_year + 1):
        sub_start = max(start, f"{year:04d}-01-01")
        sub_end = min(end, f"{year:04d}-12-31")
        if sub_start <= sub_end:
            windows.append(
                MomentumValidationWindow(
                    name=f"train_stability_{year}",
                    train_start=sub_start,
                    train_end=sub_end,
                    test_start=sub_start,
                    test_end=sub_end,
                )
            )
    return windows


def generate_train_stability_windows(
    start: str,
    end: str,
    *,
    stability_years: int = 2,
) -> list[MomentumValidationWindow]:
    if stability_years <= 0:
        raise ValueError("stability_years must be positive")
    if stability_years == 1:
        return generate_calendar_year_subwindows(start, end)
    start_year = date.fromisoformat(start).year
    end_year = date.fromisoformat(end).year
    windows: list[MomentumValidationWindow] = []
    for sub_start_year in range(start_year, end_year + 1):
        sub_end_year = sub_start_year + stability_years - 1
        if sub_end_year > end_year:
            break
        sub_start = max(start, f"{sub_start_year:04d}-01-01")
        sub_end = min(end, f"{sub_end_year:04d}-12-31")
        windows.append(
            MomentumValidationWindow(
                name=f"train_stability_{sub_start_year}_{sub_end_year}",
                train_start=sub_start,
                train_end=sub_end,
                test_start=sub_start,
                test_end=sub_end,
            )
        )
    return windows


def select_best_train_candidate(
    rows: list[dict[str, Any]],
    *,
    min_train_trades: int = 1,
    min_train_positive_ratio: float = 0.0,
) -> dict[str, Any] | None:
    eligible = [
        row
        for row in rows
        if float(row["excess_return_pct"]) > 0 and int(row["trades"]) >= min_train_trades
        and float(row.get("train_positive_ratio", 1.0)) >= min_train_positive_ratio
    ]
    if not eligible:
        return None
    return max(eligible, key=_selection_score)


def run_walk_forward_validation(
    symbol_candles: dict[str, list[Candle]],
    windows: list[MomentumValidationWindow],
    *,
    presets: list[str] | None = None,
    min_train_trades: int = 1,
    min_test_trades: int = 1,
    min_rows_per_window: int = 120,
    start_grace_days: int = 14,
    min_train_positive_ratio: float = 0.5,
    train_stability_years: int = 2,
    fallback_breadth_days: int = 120,
    fallback_breadth_threshold: float = 0.4,
    weak_breadth_min_train_avg_excess_pct: float = 10.0,
    runner: Callable[
        [dict[str, list[Candle]], MomentumRotationConfig],
        MomentumRotationResult,
    ] = run_momentum_rotation_backtest,
) -> list[dict[str, Any]]:
    selected_presets = presets or ["balanced", "aggressive", "retail"]
    cash_baseline_config = momentum_rotation_config_for_preset(selected_presets[0])
    rows: list[dict[str, Any]] = []
    for window in windows:
        train_candles = _slice_symbol_candles(
            symbol_candles,
            window.train_start,
            window.train_end,
            min_rows=min_rows_per_window,
            start_grace_days=start_grace_days,
        )
        test_candles = _slice_symbol_candles(
            symbol_candles,
            window.test_start,
            window.test_end,
            min_rows=min_rows_per_window,
            start_grace_days=start_grace_days,
        )
        prior_market_breadth = market_breadth_before_date(
            symbol_candles,
            before_date=window.test_start,
            trend_days=fallback_breadth_days,
        )
        train_results = [
            _summary_row(preset, runner(train_candles, momentum_rotation_config_for_preset(preset)))
            for preset in selected_presets
        ]
        _add_train_stability_metrics(
            train_results,
            symbol_candles,
            window=window,
            min_rows_per_window=min_rows_per_window,
            start_grace_days=start_grace_days,
            train_stability_years=train_stability_years,
            runner=runner,
        )
        selected = select_best_train_candidate(
            train_results,
            min_train_trades=min_train_trades,
            min_train_positive_ratio=min_train_positive_ratio,
        )
        if selected is None:
            if _breadth_allows_beta(prior_market_breadth, fallback_breadth_threshold):
                rows.append(
                    _market_beta_row(
                        window,
                        len(train_candles),
                        len(test_candles),
                        test_candles,
                        cash_baseline_config,
                    )
                )
                continue
            rows.append(
                _cash_row(
                    window,
                    len(train_candles),
                    len(test_candles),
                    "no_train_candidate",
                    test_candles,
                    cash_baseline_config,
                )
            )
            continue

        if not _breadth_allows_alpha(
            prior_market_breadth,
            fallback_breadth_threshold,
            selected,
            weak_breadth_min_train_avg_excess_pct,
        ):
            rows.append(
                _cash_row(
                    window,
                    len(train_candles),
                    len(test_candles),
                    "weak_market_breadth",
                    test_candles,
                    cash_baseline_config,
                )
            )
            continue

        test_result = runner(test_candles, momentum_rotation_config_for_preset(str(selected["preset"])))
        test_summary = _summary_row(str(selected["preset"]), test_result)
        reject_reason = ""
        if int(test_summary["trades"]) < min_test_trades and float(test_summary["excess_return_pct"]) <= 0:
            reject_reason = "no_test_trades"
        elif float(test_summary["excess_return_pct"]) <= 0:
            reject_reason = "negative_test_excess"

        rows.append(
            {
                "window": window.name,
                "train_start": window.train_start,
                "train_end": window.train_end,
                "test_start": window.test_start,
                "test_end": window.test_end,
                "selected_preset": selected["preset"],
                "selection_score": round(_selection_score(selected), 4),
                "train_total_return_pct": selected["total_return_pct"],
                "train_buy_hold_return_pct": selected["buy_hold_return_pct"],
                "train_excess_return_pct": selected["excess_return_pct"],
                "train_max_drawdown_pct": selected["max_drawdown_pct"],
                "train_trades": selected["trades"],
                "train_subwindows": selected["train_subwindows"],
                "train_positive_subwindows": selected["train_positive_subwindows"],
                "train_positive_ratio": selected["train_positive_ratio"],
                "train_avg_subwindow_excess_pct": selected["train_avg_subwindow_excess_pct"],
                "train_worst_subwindow_excess_pct": selected["train_worst_subwindow_excess_pct"],
                "test_total_return_pct": test_summary["total_return_pct"],
                "test_buy_hold_return_pct": test_summary["buy_hold_return_pct"],
                "test_excess_return_pct": test_summary["excess_return_pct"],
                "test_max_drawdown_pct": test_summary["max_drawdown_pct"],
                "test_trades": test_summary["trades"],
                "accepted": reject_reason == "",
                "reject_reason": reject_reason,
                "train_symbols": len(train_candles),
                "test_symbols": len(test_candles),
            }
        )
    return rows


def run_holdout_validation(
    symbol_candles: dict[str, list[Candle]],
    *,
    train_start: str,
    train_end: str,
    holdout_start: str,
    holdout_end: str,
    presets: list[str] | None = None,
    min_train_trades: int = 1,
    min_test_trades: int = 1,
    min_rows_per_window: int = 120,
    start_grace_days: int = 14,
    min_train_positive_ratio: float = 0.5,
    train_stability_years: int = 2,
    fallback_breadth_days: int = 120,
    fallback_breadth_threshold: float = 0.4,
    weak_breadth_min_train_avg_excess_pct: float = 10.0,
) -> dict[str, Any]:
    window = MomentumValidationWindow(
        name="final_holdout",
        train_start=train_start,
        train_end=train_end,
        test_start=holdout_start,
        test_end=holdout_end,
    )
    rows = run_walk_forward_validation(
        symbol_candles,
        [window],
        presets=presets,
        min_train_trades=min_train_trades,
        min_test_trades=min_test_trades,
        min_rows_per_window=min_rows_per_window,
        start_grace_days=start_grace_days,
        min_train_positive_ratio=min_train_positive_ratio,
        train_stability_years=train_stability_years,
        fallback_breadth_days=fallback_breadth_days,
        fallback_breadth_threshold=fallback_breadth_threshold,
        weak_breadth_min_train_avg_excess_pct=weak_breadth_min_train_avg_excess_pct,
    )
    return rows[0]


def save_validation_rows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_COLUMNS)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in VALIDATION_COLUMNS} for row in rows)
    return len(rows)


def summarize_deployment_gate(
    walk_rows: list[dict[str, Any]],
    *,
    min_accepted_ratio: float = 0.5,
    min_avg_test_excess_pct: float = 0.0,
    min_worst_test_excess_pct: float = -20.0,
) -> dict[str, Any]:
    if not walk_rows:
        return {
            "deployable": False,
            "reject_reason": "no_walk_forward_windows",
            "walk_windows": 0,
            "accepted_windows": 0,
            "accepted_ratio": 0.0,
            "avg_test_excess_return_pct": 0.0,
            "worst_test_excess_return_pct": 0.0,
            "min_accepted_ratio": min_accepted_ratio,
            "min_avg_test_excess_pct": min_avg_test_excess_pct,
            "min_worst_test_excess_pct": min_worst_test_excess_pct,
        }
    accepted_windows = sum(1 for row in walk_rows if _bool_value(row.get("accepted", False)))
    excess_values = [float(row["test_excess_return_pct"]) for row in walk_rows]
    accepted_ratio = accepted_windows / len(walk_rows)
    avg_excess = sum(excess_values) / len(excess_values)
    worst_excess = min(excess_values)
    reject_reason = ""
    if accepted_ratio < min_accepted_ratio:
        reject_reason = "low_walk_forward_acceptance"
    elif avg_excess < min_avg_test_excess_pct:
        reject_reason = "low_average_oos_excess"
    elif worst_excess < min_worst_test_excess_pct:
        reject_reason = "fragile_worst_oos_excess"
    return {
        "deployable": reject_reason == "",
        "reject_reason": reject_reason,
        "walk_windows": len(walk_rows),
        "accepted_windows": accepted_windows,
        "accepted_ratio": round(accepted_ratio, 4),
        "avg_test_excess_return_pct": round(avg_excess, 4),
        "worst_test_excess_return_pct": round(worst_excess, 4),
        "min_accepted_ratio": min_accepted_ratio,
        "min_avg_test_excess_pct": min_avg_test_excess_pct,
        "min_worst_test_excess_pct": min_worst_test_excess_pct,
    }


def save_deployment_gate_summary(row: dict[str, Any], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DEPLOYMENT_GATE_COLUMNS)
        writer.writeheader()
        writer.writerow({column: row.get(column, "") for column in DEPLOYMENT_GATE_COLUMNS})
    return 1


def _selection_score(row: dict[str, Any]) -> float:
    stability_bonus = 25.0 * float(row.get("train_positive_ratio", 1.0))
    worst_penalty = min(float(row.get("train_worst_subwindow_excess_pct", 0.0)), 0.0)
    return float(row["excess_return_pct"]) + float(row["max_drawdown_pct"]) + stability_bonus + worst_penalty


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _summary_row(preset: str, result: MomentumRotationResult) -> dict[str, Any]:
    return {
        "preset": preset,
        "total_return_pct": round(result.total_return_pct, 4),
        "buy_hold_return_pct": round(result.buy_hold_return_pct, 4),
        "excess_return_pct": round(result.excess_return_pct, 4),
        "max_drawdown_pct": round(result.max_drawdown_pct, 4),
        "trades": result.trade_count,
    }


def _add_train_stability_metrics(
    train_results: list[dict[str, Any]],
    symbol_candles: dict[str, list[Candle]],
    *,
    window: MomentumValidationWindow,
    min_rows_per_window: int,
    start_grace_days: int,
    train_stability_years: int,
    runner: Callable[
        [dict[str, list[Candle]], MomentumRotationConfig],
        MomentumRotationResult,
    ],
) -> None:
    subwindows = generate_train_stability_windows(
        window.train_start,
        window.train_end,
        stability_years=train_stability_years,
    )
    for row in train_results:
        preset = str(row["preset"])
        excess_values: list[float] = []
        positive_count = 0
        for subwindow in subwindows:
            sub_candles = slice_asof_symbol_candles(
                symbol_candles,
                start=subwindow.train_start,
                end=subwindow.train_end,
                min_rows=min_rows_per_window,
                start_grace_days=start_grace_days,
            )
            if not sub_candles:
                continue
            result = runner(sub_candles, momentum_rotation_config_for_preset(preset))
            excess = result.excess_return_pct
            excess_values.append(excess)
            if excess > 0 and result.trade_count > 0:
                positive_count += 1
        subwindow_count = len(excess_values)
        row["train_subwindows"] = subwindow_count
        row["train_positive_subwindows"] = positive_count
        row["train_positive_ratio"] = round(positive_count / subwindow_count, 4) if subwindow_count else 0.0
        row["train_avg_subwindow_excess_pct"] = (
            round(sum(excess_values) / subwindow_count, 4) if subwindow_count else 0.0
        )
        row["train_worst_subwindow_excess_pct"] = round(min(excess_values), 4) if excess_values else 0.0


def _slice_symbol_candles(
    symbol_candles: dict[str, list[Candle]],
    start: str,
    end: str,
    *,
    min_rows: int,
    start_grace_days: int,
) -> dict[str, list[Candle]]:
    return slice_asof_symbol_candles(
        symbol_candles,
        start=start,
        end=end,
        min_rows=min_rows,
        start_grace_days=start_grace_days,
    )


def slice_asof_symbol_candles(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
    min_rows: int,
    start_grace_days: int = 14,
) -> dict[str, list[Candle]]:
    latest_start_date = (date.fromisoformat(start) + timedelta(days=start_grace_days)).isoformat()
    sliced = {
        symbol: [candle for candle in candles if start <= candle.date <= end]
        for symbol, candles in symbol_candles.items()
    }
    return {
        symbol: candles
        for symbol, candles in sliced.items()
        if len(candles) >= min_rows and candles[0].date <= latest_start_date
    }


def market_breadth_before_date(
    symbol_candles: dict[str, list[Candle]],
    *,
    before_date: str,
    trend_days: int,
) -> float | None:
    if trend_days <= 0:
        return None
    checks: list[bool] = []
    for candles in symbol_candles.values():
        prior = [candle for candle in candles if candle.date < before_date]
        if len(prior) < trend_days:
            continue
        window = prior[-trend_days:]
        average = sum(candle.close for candle in window) / len(window)
        checks.append(window[-1].close >= average)
    if not checks:
        return None
    return sum(checks) / len(checks)


def _breadth_allows_beta(prior_market_breadth: float | None, threshold: float) -> bool:
    return prior_market_breadth is not None and prior_market_breadth >= threshold


def _breadth_allows_alpha(
    prior_market_breadth: float | None,
    threshold: float,
    selected: dict[str, Any],
    weak_breadth_min_train_avg_excess_pct: float,
) -> bool:
    if prior_market_breadth is not None and prior_market_breadth >= threshold:
        return True
    return float(selected.get("train_avg_subwindow_excess_pct", 0.0)) >= weak_breadth_min_train_avg_excess_pct


def _market_beta_row(
    window: MomentumValidationWindow,
    train_symbol_count: int,
    test_symbol_count: int,
    test_candles: dict[str, list[Candle]],
    cfg: MomentumRotationConfig,
) -> dict[str, Any]:
    test_buy_hold_return_pct = _equal_weight_buy_hold_return(test_candles, cfg) if test_candles else 0.0
    return {
        "window": window.name,
        "train_start": window.train_start,
        "train_end": window.train_end,
        "test_start": window.test_start,
        "test_end": window.test_end,
        "selected_preset": "market_beta",
        "selection_score": 0.0,
        "train_total_return_pct": 0.0,
        "train_buy_hold_return_pct": 0.0,
        "train_excess_return_pct": 0.0,
        "train_max_drawdown_pct": 0.0,
        "train_trades": 0,
        "train_subwindows": 0,
        "train_positive_subwindows": 0,
        "train_positive_ratio": 0.0,
        "train_avg_subwindow_excess_pct": 0.0,
        "train_worst_subwindow_excess_pct": 0.0,
        "test_total_return_pct": round(test_buy_hold_return_pct, 4),
        "test_buy_hold_return_pct": round(test_buy_hold_return_pct, 4),
        "test_excess_return_pct": 0.0,
        "test_max_drawdown_pct": 0.0,
        "test_trades": 1,
        "accepted": True,
        "reject_reason": "",
        "train_symbols": train_symbol_count,
        "test_symbols": test_symbol_count,
    }


def _cash_row(
    window: MomentumValidationWindow,
    train_symbol_count: int,
    test_symbol_count: int,
    reject_reason: str,
    test_candles: dict[str, list[Candle]] | None = None,
    cfg: MomentumRotationConfig | None = None,
) -> dict[str, Any]:
    test_buy_hold_return_pct = (
        _equal_weight_buy_hold_return(test_candles, cfg or MomentumRotationConfig())
        if test_candles
        else 0.0
    )
    test_excess_return_pct = -test_buy_hold_return_pct
    accepted = test_excess_return_pct > 0
    return {
        "window": window.name,
        "train_start": window.train_start,
        "train_end": window.train_end,
        "test_start": window.test_start,
        "test_end": window.test_end,
        "selected_preset": "cash",
        "selection_score": 0.0,
        "train_total_return_pct": 0.0,
        "train_buy_hold_return_pct": 0.0,
        "train_excess_return_pct": 0.0,
        "train_max_drawdown_pct": 0.0,
        "train_trades": 0,
        "train_subwindows": 0,
        "train_positive_subwindows": 0,
        "train_positive_ratio": 0.0,
        "train_avg_subwindow_excess_pct": 0.0,
        "train_worst_subwindow_excess_pct": 0.0,
        "test_total_return_pct": 0.0,
        "test_buy_hold_return_pct": round(test_buy_hold_return_pct, 4),
        "test_excess_return_pct": round(test_excess_return_pct, 4),
        "test_max_drawdown_pct": 0.0,
        "test_trades": 0,
        "accepted": accepted,
        "reject_reason": "" if accepted else reject_reason,
        "train_symbols": train_symbol_count,
        "test_symbols": test_symbol_count,
    }
