# 미국주식 Paper-Only TCA Simulator

## 목적

`auto-paper-tca`는 paper execution simulator의 fill 결과를 받아 transaction cost analysis 리포트를 만든다. 실제 체결, 브로커 체결장, 실시간 호가를 읽지 않으며, 모든 결과는 dry-run 감사용이다.

## 입력

- paper execution CSV: 기본 `data/reports/auto_trading/auto_paper_execution_simulation.csv`
- market impact CSV: 기본 `data/reports/auto_trading/auto_paper_market_impact.csv`

execution row는 다음 안전 플래그를 가져야 한다.

- `simulated=True`
- `paper_only=True`
- `dry_run=True`
- `execution_allowed=False`
- `production_effect=none`

market impact row도 `paper_only=True`, `dry_run=True`, `execution_allowed=False`, `production_effect=none`이어야 한다.

## 계산 기준

TCA v1은 reference price를 arrival price proxy로 둔다.

- BUY shortfall: `(simulated_fill_price - reference_price) * filled_quantity`
- SELL shortfall: `(reference_price - simulated_fill_price) * filled_quantity`
- shortfall bps: `implementation_shortfall_usd / arrival_notional_usd * 10000`
- expected total cost: `estimated_spread_cost_usd + estimated_slippage_cost_usd + expected_market_impact_usd`
- cost variance: `implementation_shortfall_usd - expected_total_cost_usd`

기본 gate:

- `max_shortfall_bps=50.0`
- `max_cost_variance_usd=5.0`

NO_FILL row는 `REVIEW`로 표시한다. shortfall 또는 variance 한도를 넘으면 `BLOCK`이다.

## 실행

```powershell
python -m backtester auto-paper-tca
```

기본 산출물:

- `data/reports/auto_trading/auto_paper_tca.csv`
- `data/reports/auto_trading/auto_paper_tca.md`

## 한계

v1은 paper fill 기반 TCA proxy다. 실제 venue별 체결 품질, NBBO, real VWAP, broker routing, queue priority, cancel/replace 로그는 포함하지 않는다. 따라서 리포트는 post-trade audit 형식을 흉내내는 연구 산출물이며, 실주문 품질 판단으로 쓰면 안 된다.
