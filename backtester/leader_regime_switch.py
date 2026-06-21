from collections import Counter
from dataclasses import dataclass, field
from statistics import mean

from .leader_swing import LeaderSwingConfig, LeaderSwingResult, run_leader_swing_backtest
from .models import Candle


@dataclass(frozen=True)
class LeaderRegimeSwitchConfig:
    regime_window: int = 126
    bull_return_threshold_pct: float = 8.0
    bull_breadth_threshold: float = 0.5
    defensive: LeaderSwingConfig = field(
        default_factory=lambda: LeaderSwingConfig(
            max_positions=5,
            liquidity_top_n=10,
            min_short_return_pct=8,
            max_holding_days=20,
            market_breadth_threshold=0.6,
            loss_cooldown_days=10,
        )
    )
    bullish: LeaderSwingConfig = field(
        default_factory=lambda: LeaderSwingConfig(
            max_positions=10,
            liquidity_top_n=15,
            min_short_return_pct=3,
            min_long_return_pct=-5,
            max_holding_days=90,
            exit_ma_window=40,
            stop_loss_pct=-15,
            market_breadth_threshold=0.4,
            symbol_weight_multipliers={"000660": 2.5, "005930": 1.5, "006400": 1.5},
            loss_cooldown_days=10,
        )
    )


@dataclass(frozen=True)
class RegimeSwitchingLeaderResult:
    result: LeaderSwingResult
    mode_counts: dict[str, int]


def classify_leader_market_regime(
    date: str,
    symbol_candles: dict[str, list[Candle]],
    index_by_symbol_date: dict[str, dict[str, int]],
    config: LeaderRegimeSwitchConfig,
) -> str:
    returns: list[float] = []
    breadth_checks: list[bool] = []
    for symbol, candles in symbol_candles.items():
        index = index_by_symbol_date[symbol].get(date)
        if index is None or index < config.regime_window:
            continue
        current = candles[index]
        previous = candles[index - config.regime_window]
        returns.append((current.close / previous.close - 1) * 100)
        moving_average = mean(c.close for c in candles[index - config.regime_window + 1 : index + 1])
        breadth_checks.append(current.close > moving_average)

    if not returns or not breadth_checks:
        return "defensive"

    market_return_pct = mean(returns)
    breadth_ratio = sum(breadth_checks) / len(breadth_checks)
    if market_return_pct >= config.bull_return_threshold_pct and breadth_ratio >= config.bull_breadth_threshold:
        return "bull"
    return "defensive"


def run_regime_switching_leader_backtest(
    symbol_candles: dict[str, list[Candle]],
    config: LeaderRegimeSwitchConfig | None = None,
) -> RegimeSwitchingLeaderResult:
    cfg = config or LeaderRegimeSwitchConfig()
    mode_counts: Counter[str] = Counter()

    def resolve_config(
        date: str,
        candles_by_symbol: dict[str, list[Candle]],
        index_by_symbol_date: dict[str, dict[str, int]],
        base_config: LeaderSwingConfig,
    ) -> LeaderSwingConfig:
        del base_config
        mode = classify_leader_market_regime(date, candles_by_symbol, index_by_symbol_date, cfg)
        mode_counts[mode] += 1
        return cfg.bullish if mode == "bull" else cfg.defensive

    result = run_leader_swing_backtest(
        symbol_candles=symbol_candles,
        config=cfg.defensive,
        config_resolver=resolve_config,
    )
    return RegimeSwitchingLeaderResult(result=result, mode_counts=dict(mode_counts))
