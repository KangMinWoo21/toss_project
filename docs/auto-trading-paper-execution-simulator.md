# Auto Paper Execution Simulator

작성일: 2026-07-01

## 목적

KIS dry-run 주문계획을 실제 주문 없이 simulated fill 리포트로 변환한다.
이 기능은 paper-only 분석용이며, 주문 전송, 취소, 정정, 브로커 라우팅을 수행하지 않는다.

## CLI

```powershell
python -m backtester auto-paper-simulate-execution `
  --orders data/reports/kis_us_paper_order_plan_from_auto_risk_adjusted_demo.csv `
  --prices-dir data/external/yahoo/us_daily `
  --fill-policy close `
  --output data/reports/auto_trading/auto_paper_execution_simulation.csv
```

## Fill Policies

- `close`: as_of 당일 또는 그 이전의 최신 close 사용
- `open`: as_of 당일 또는 그 이전의 최신 open 사용
- `next_bar`: as_of 이후 첫 bar 사용
- `vwap_proxy`: `(high + low + close) / 3`

`next_bar`를 포함한 모든 정책은 `execution_time_kst`가 주어졌을 때 `usable_from_kst` 이전 bar 사용을 lookahead로 차단한다.

## Liquidity And Cost Proxy

- `max_adv_participation`으로 최대 체결 가능 수량을 제한한다.
- 수량이 한도를 넘으면 `PARTIAL`로 저장한다.
- volume이 0이면 `NO_FILL`과 `insufficient_liquidity`를 저장한다.
- spread/slippage proxy는 simulated fill price와 비용 컬럼으로 분리한다.

## Safety

모든 row는 다음 값을 고정한다.

- `simulated=True`
- `paper_only=True`
- `dry_run=True`
- `execution_allowed=False`
- `production_effect=none`

시장충격 추정은 `docs/auto-trading-market-impact.md`를 참고한다.
