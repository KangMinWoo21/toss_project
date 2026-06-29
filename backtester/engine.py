from dataclasses import dataclass
from math import sqrt
from statistics import mean, pstdev

from .models import Candle
from .strategies import Strategy


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10_000_000.0
    fee_rate: float = 0.00015
    tax_rate: float = 0.0018
    slippage_rate: float = 0.0005
    position_fraction: float = 1.0


@dataclass(frozen=True)
class Position:
    quantity: int
    entry_price: float
    entry_date: str


@dataclass(frozen=True)
class Trade:
    date: str
    side: str
    price: float
    quantity: int
    cash_after: float
    equity_after: float
    reason: str
    entry_price: float = 0.0
    pnl: float = 0.0


@dataclass(frozen=True)
class BacktestResult:
    strategy_name: str
    initial_cash: float
    final_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    trade_count: int
    win_rate_pct: float
    profit_factor: float
    sharpe_ratio: float
    calmar_ratio: float
    trades: list[Trade]
    equity_curve: list[float]


class Backtester:
    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def run(self, candles: list[Candle], strategy: Strategy) -> BacktestResult:
        if not candles:
            raise ValueError("candles cannot be empty")

        cash = self.config.initial_cash
        position: Position | None = None
        trades: list[Trade] = []
        equity_curve: list[float] = []

        for index, candle in enumerate(candles):
            signal = "HOLD"
            if index > 0:
                signal = strategy.on_candle(index - 1, candles, position)

            if signal == "BUY" and position is None:
                fill_price = candle.open * (1 + self.config.slippage_rate)
                budget = cash * self.config.position_fraction
                quantity = int(budget / (fill_price * (1 + self.config.fee_rate)))
                if quantity > 0:
                    gross = quantity * fill_price
                    fee = gross * self.config.fee_rate
                    cash -= gross + fee
                    position = Position(quantity=quantity, entry_price=fill_price, entry_date=candle.date)

            elif signal == "SELL" and position is not None:
                fill_price = candle.open * (1 - self.config.slippage_rate)
                gross = position.quantity * fill_price
                fee = gross * self.config.fee_rate
                tax = gross * self.config.tax_rate
                pnl = (fill_price - position.entry_price) * position.quantity - fee - tax
                cash += gross - fee - tax
                equity = cash
                trades.append(
                    Trade(
                        date=candle.date,
                        side="SELL",
                        price=fill_price,
                        quantity=position.quantity,
                        cash_after=cash,
                        equity_after=equity,
                        reason=strategy.name,
                        entry_price=position.entry_price,
                        pnl=pnl,
                    )
                )
                position = None

            equity_curve.append(_equity(cash, position, candle.close))

        if position is not None:
            final_candle = candles[-1]
            fill_price = final_candle.close * (1 - self.config.slippage_rate)
            gross = position.quantity * fill_price
            fee = gross * self.config.fee_rate
            tax = gross * self.config.tax_rate
            pnl = (fill_price - position.entry_price) * position.quantity - fee - tax
            cash += gross - fee - tax
            equity_curve[-1] = cash
            trades.append(
                Trade(
                    date=final_candle.date,
                    side="SELL",
                    price=fill_price,
                    quantity=position.quantity,
                    cash_after=cash,
                    equity_after=cash,
                    reason=strategy.name,
                    entry_price=position.entry_price,
                    pnl=pnl,
                )
            )
            position = None

        final_price = candles[-1].close
        return self.build_result(
            initial_cash=self.config.initial_cash,
            final_cash=cash,
            final_position=0,
            final_price=final_price,
            equity_curve=equity_curve,
            trades=trades,
            strategy_name=strategy.name,
        )

    @staticmethod
    def build_result(
        initial_cash: float,
        final_cash: float,
        final_position: int,
        final_price: float,
        equity_curve: list[float],
        trades: list[Trade],
        strategy_name: str = "manual",
    ) -> BacktestResult:
        final_equity = final_cash + final_position * final_price
        total_return_pct = (final_equity / initial_cash - 1) * 100
        max_drawdown_pct = _max_drawdown_pct(equity_curve)
        wins, losses = _trade_pnls(trades)
        closed_count = len(wins) + len(losses)
        win_rate_pct = (len(wins) / closed_count * 100) if closed_count else 0.0
        profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("inf")
        sharpe_ratio = _annualized_sharpe_ratio(equity_curve)
        calmar_ratio = _calmar_ratio(total_return_pct, max_drawdown_pct)
        return BacktestResult(
            strategy_name=strategy_name,
            initial_cash=initial_cash,
            final_equity=final_equity,
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            trade_count=len(trades),
            win_rate_pct=win_rate_pct,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio,
            trades=trades,
            equity_curve=equity_curve,
        )


def _equity(cash: float, position: Position | None, market_price: float) -> float:
    if position is None:
        return cash
    return cash + position.quantity * market_price


def _max_drawdown_pct(equity_curve: list[float]) -> float:
    peak = equity_curve[0]
    worst = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        drawdown = (equity / peak - 1) * 100
        worst = min(worst, drawdown)
    return worst


def _trade_pnls(trades: list[Trade]) -> tuple[list[float], list[float]]:
    wins: list[float] = []
    losses: list[float] = []
    for trade in trades:
        pnl = trade.pnl
        if pnl > 0:
            wins.append(pnl)
        elif pnl < 0:
            losses.append(pnl)
    return wins, losses


def _period_returns(equity_curve: list[float]) -> list[float]:
    returns: list[float] = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous > 0:
            returns.append(current / previous - 1)
    return returns


def _annualized_sharpe_ratio(equity_curve: list[float], periods_per_year: int = 252) -> float:
    returns = _period_returns(equity_curve)
    if len(returns) < 2:
        return 0.0
    volatility = pstdev(returns)
    if volatility == 0:
        return 0.0
    return mean(returns) / volatility * sqrt(periods_per_year)


def _calmar_ratio(total_return_pct: float, max_drawdown_pct: float) -> float:
    drawdown = abs(max_drawdown_pct)
    if drawdown == 0:
        return float("inf") if total_return_pct > 0 else 0.0
    return total_return_pct / drawdown
