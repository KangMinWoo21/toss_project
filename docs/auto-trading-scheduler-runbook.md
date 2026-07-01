# 미국주식 Paper-Only Scheduler Runbook

## 원칙

이 runbook은 paper-only 자동매매 연구 엔진의 로컬 스케줄 실행 순서다. 실주문, 실전 계좌 주문, 브로커 주문 제출은 포함하지 않는다. `auto-paper-run`은 local CSV only이며, 네트워크 fetch는 별도 스크립트에서만 수행한다.

## 권장 실행 순서

1. 데이터 갱신이 필요할 때만 별도 fetch 스크립트를 실행한다.

```powershell
python scripts/fetch_us_yahoo_daily.py --symbols SPY,QQQ,AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA
python scripts/fetch_us_free_external_data.py --symbols SPY,QQQ,AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA
```

2. 로컬 데이터 readiness를 확인한다.

```powershell
python -m backtester auto-paper-external-data-readiness
```

3. 핵심 paper-only 엔진을 실행한다.

```powershell
python -m backtester auto-paper-run
```

4. 후보 비중을 paper-only optimizer로 재산출하거나 비교한다.

```powershell
python -m backtester auto-paper-optimize-portfolio
```

5. risk gate를 통과하는지 확인한다.

```powershell
python -m backtester auto-paper-factor-risk
python -m backtester auto-paper-risk-gate --kis-targets data/reports/auto_trading/auto_paper_optimized_targets.csv --portfolio-value-usd 100000
```

6. KIS paper-only 주문계획과 paper execution/TCA를 생성한다.

```powershell
python -m backtester kis-us-paper-plan-demo
python -m backtester auto-paper-simulate-execution
python -m backtester auto-paper-market-impact
python -m backtester auto-paper-tca
```

7. 마지막으로 scheduler monitoring 리포트를 확인한다.

```powershell
python -m backtester auto-paper-monitoring-report
```

## 스케줄러 통과 기준

`auto-paper-monitoring-report`의 `scheduler_monitoring_status`가 `PASS`여야 한다. 다음 중 하나라도 실패하면 다음 주문계획 단계로 넘기지 않는다.

- audit log: `engine_status=SUCCESS`, `objective_status=COMPLETE`
- audit safety flags: `paper_only=True`, `dry_run=True`, `execution_allowed=False`, `production_effect=none`
- external data readiness: 모든 adapter `PASS`
- portfolio risk gate: 모든 check `PASS`
- factor risk: 모든 check `PASS`
- TCA: 모든 row `PASS`
- operation health: 모든 check `PASS`

## 장애 대응

- `missing_file`: 해당 선행 명령이 실행되지 않았거나 output path가 바뀐 상태다.
- `non_pass_status`: 원본 gate 리포트를 열어 `BLOCK` 또는 `REVIEW` 원인을 확인한다.
- `unsafe_flags`: 산출물에 paper-only 안전 플래그가 깨진 row가 있다는 뜻이므로 실행을 중단한다.
- `objective_not_complete`: 전략 목표가 아직 기준 모델을 이긴 상태가 아니다. 엔진 구현이 성공했더라도 목표 완료로 보지 않는다.

## 산출물

- `data/reports/auto_trading/auto_paper_scheduler_monitoring.csv`
- `data/reports/auto_trading/auto_paper_scheduler_monitoring.md`

이 산출물은 모니터링/감사용이다. 실주문 승인서가 아니며 production effect는 항상 `none`이다.
