# 미국주식 Paper-Only Portfolio Optimizer

## 목적

`auto-paper-optimize-portfolio`는 로컬 후보 CSV와 무료 factor proxy를 사용해 paper-only 목표비중을 생성한다. 실시간 데이터, 브로커, KIS, Toss, yfinance 네트워크 호출은 하지 않는다.

## 입력

- 후보 CSV: 기본 `data/auto_trading/us_portfolio_optimizer_candidates.csv`
- 외부 데이터 디렉터리: 기본 `data/auto_trading/free_external_data`
- 필수 factor 파일: `factors.csv`

후보 CSV 필수 컬럼:

- `symbol`
- `exchange`
- `alpha_score`
- `paper_only`
- `dry_run`
- `execution_allowed`
- `production_effect`

모든 후보 row는 `paper_only=True`, `dry_run=True`, `execution_allowed=False`, `production_effect=none`이어야 한다.

## 최적화 방식

v1은 외부 최적화 라이브러리를 추가하지 않고, deterministic greedy allocator를 사용한다.

1. `alpha_score`가 높은 후보부터 평가한다.
2. beta와 quality가 심볼 단위 필터를 통과해야 한다.
3. `weight_step` 단위로 비중을 늘리되 다음 한도를 넘지 않는다.
4. 한도에 걸리면 해당 지점에서 멈추고 다음 후보로 넘어간다.

기본 제약:

- `max_total_weight=0.98`
- `max_single_weight=0.35`
- `max_sector_weight=0.50`
- `max_weighted_beta=1.50`
- `max_symbol_beta=1.80`
- `min_quality_score=0.50`
- `min_alpha_score=0.0`
- `weight_step=0.01`

## 출력

기본 산출물:

- `data/reports/auto_trading/auto_paper_optimized_targets.csv`
- `data/reports/auto_trading/auto_paper_optimized_targets.md`

CSV는 선택된 후보와 SKIP 후보를 모두 남긴다. `target_weight=0`인 row는 감사 목적이며, 이후 risk gate와 KIS paper-only target loader는 양수 비중만 사용한다.

모든 출력 row는 다음 값을 포함한다.

- `paper_only=True`
- `dry_run=True`
- `execution_allowed=False`
- `production_effect=none`

## 검증 연결

optimizer 출력은 다음 명령으로 바로 점검할 수 있다.

```powershell
python -m backtester auto-paper-factor-risk --kis-targets data/reports/auto_trading/auto_paper_optimized_targets.csv
python -m backtester auto-paper-risk-gate --kis-targets data/reports/auto_trading/auto_paper_optimized_targets.csv --portfolio-value-usd 100000
```

## 한계

v1은 월가식 최적화의 paper-only proxy다. 실제 공분산 행렬, 제약부 quadratic optimizer, tax-aware lot optimizer, broker-specific execution optimizer는 포함하지 않는다. 이 출력은 실주문 지시가 아니라 다음 research/audit 단계로 넘기는 dry-run target이다.
