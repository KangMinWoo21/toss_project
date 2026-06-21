# Academic notes for backtesting and scalping

This project applies a few conservative ideas from quantitative finance and market microstructure research.

## Backtest evaluation

- Bailey and Lopez de Prado argue that repeatedly searching many strategy variants inflates apparent performance. The code therefore reports risk-adjusted metrics, not just total return.
- Walk-forward selection now prefers Calmar-style risk-adjusted performance before raw return, so a high-return strategy with severe drawdown is less likely to be selected.
- Sharpe ratio is included as a quick return-per-volatility diagnostic. It is not treated as proof of edge, especially after many trials.

## Scalping and limit order book signals

- Cont, Kukanov, and Stoikov show that short-horizon price changes are more directly related to order-flow imbalance near the best bid/ask than to raw trade volume alone.
- The paper scalper records best bid, best ask, spread, top-5 bid/ask volume, and bid/ask imbalance for each saved tick.
- A max-spread filter blocks entries when the bid-ask spread is too wide, because spread is an immediate execution cost for short-horizon trades.

## References

- Bailey, D. H. and Lopez de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality." Journal of Portfolio Management.
- Bailey, D. H., Borwein, J. M., Lopez de Prado, M., and Zhu, Q. J. (2016). "The Probability of Backtest Overfitting." Journal of Computational Finance.
- Cont, R., Kukanov, A., and Stoikov, S. (2014). "The Price Impact of Order Book Events." Journal of Financial Econometrics.
- Dixon, M. (2018). "Sequence classification of the limit order book using recurrent neural networks." Journal of Computational Science.
