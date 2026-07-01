# Auto Paper Market Impact Model

작성일: 2026-07-01

## 목적

dry-run 주문계획을 기준으로 paper-only 시장충격 비용을 추정한다.
이 모델은 실제 체결 모델이 아니라 주문 규모, ADV, 변동성, spread proxy, scenario multiplier를 사용하는 보수적 proxy다.

## CLI

```powershell
python -m backtester auto-paper-market-impact `
  --orders data/reports/kis_us_paper_order_plan_from_auto_risk_adjusted_demo.csv `
  --prices-dir data/external/yahoo/us_daily `
  --scenario stress `
  --output data/reports/auto_trading/auto_paper_market_impact.csv
```

## Inputs

- `order_value_usd`
- `average_daily_dollar_volume`
- `participation_rate`
- `annualized_volatility`
- `spread_rate`
- `scenario`: `base`, `conservative`, `stress`

## Outputs

- `estimated_impact_rate`
- `estimated_impact_usd`
- `risk_bucket`: `LOW`, `MEDIUM`, `HIGH`
- `paper_only=True`
- `dry_run=True`
- `execution_allowed=False`
- `production_effect=none`

## Fail-Closed

ADV가 0 이하이면 시장충격 추정을 중단한다. 빈 가격 데이터나 0 volume 데이터는 통과시키지 않는다.
