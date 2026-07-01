# 미국주식 Paper-Only 자동매매 엔진 Evidence Packet

작성 기준일: 2026-07-01

이 문서는 `data/reports/auto_trading/` 아래 로컬 생성 리포트의 핵심 값을 PR에서 검토할 수 있도록 요약한 증거 패킷이다. 원본 리포트는 재현 산출물이며, 이 문서는 대용량 CSV 전체를 추적하지 않고도 완성 판정의 핵심 근거를 남기기 위한 요약본이다.

## 실행 상태

| 항목 | 값 |
| --- | --- |
| engine_status | `SUCCESS` |
| objective_status | `COMPLETE` |
| best_model | `momentum_cash_guard_vol_spy21_tvol10_floor75_cap105_m84_t70_top1_exp18_reb70` |
| benchmark_model_id | `proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244` |
| benchmark_row_selector | `name=return_concentration` |
| benchmark_report_sha256 | `802351b5ffec93c0b96f5cf72010bf0ce4fa60cbafbb15409d356587f326aefe` |
| paper_only | `True` |
| dry_run | `True` |
| execution_allowed | `False` |
| production_effect | `none` |

## 성과 비교

Benchmark 값은 `backtester/auto_trading/benchmark.py`가 기존 감사 리포트에서 추출하는 비교 기준이다. benchmark에는 Sharpe가 없으므로 hard gate의 "Sharpe 또는 risk-adjusted return" 조건은 risk-adjusted return으로 판정한다.

| 지표 | Benchmark | 신규 모델 base | 신규 모델 conservative | 판정 |
| --- | ---: | ---: | ---: | --- |
| net_total_return_pct | 120.0483 | 131.039395 | 125.024275 | PASS |
| net_cagr_pct | 0.8313 | 7.559879 | 7.313231 | PASS |
| max_drawdown_abs_pct | 21.7069 | 17.538243 | 17.917675 | PASS |
| risk_adjusted_return | 4.4114 | 43.105109 | 40.815737 | PASS |
| sharpe_ratio | N/A | 0.865389 | 0.838880 | INFO |

## 비용/세금 정책

| 항목 | 값 |
| --- | --- |
| base fee_rate | `0.00015` |
| base slippage_rate | `0.0005` |
| base fx_buffer_rate | `0.0010` |
| conservative fee_rate | `0.00030` |
| conservative slippage_rate | `0.0015` |
| conservative fx_buffer_rate | `0.0030` |
| annual_deduction_krw | `2_500_000` |
| capital_gains_tax_rate | `0.22` |
| constant_usd_krw_rate | `1400.0` |
| tax_proxy | `constant_fx` |
| lot_method | `FIFO` |
| tax_year_by | `settlement_date` |
| settlement_lag_days | `1` |

## 데이터/회계 정책

| 항목 | 값 |
| --- | --- |
| return_price_basis | `adj_close` |
| trade_price_basis | `close` |
| tax_price_basis | `trade_fill_price` |
| dividend_tax_policy | `excluded_v1` |
| tax_consistency_warning | `True` |
| survivorship_warning | `current liquid US research universe; survivorship bias possible` |
| external_data_policy | `free_local_csv_only` |
| external_data_network_policy | `fetch_scripts_only_auto_paper_run_local_csv_only` |

## Validation Audit

| Gate | Status | Detail |
| --- | --- | --- |
| required_scenarios | PASS | `0 failed of 10 required` |
| required_net_total | PASS | `min_required_net_total_return_pct=0.4273` |
| walk_forward_margin | PASS | `min_walk_forward_net_total_return_pct=0.4273` |
| drawdown_buffer | PASS | `worst_max_drawdown_abs_pct=18.0389; warn_at_or_above=20.0000; block_above=25.0000` |
| return_concentration | PASS | `full_net_total_return_pct=125.0243; median_walk_forward_net_total_return_pct=6.3711; ratio=19.6237; warn_above=20.0000` |
| trade_activity | PASS | `10 required scenarios traded` |

## 재현 명령

```powershell
python -m backtester auto-paper-run --prices-dir data/external/yahoo/us_daily --universe data/auto_trading/us_core_universe.csv --benchmark-report data/reports/monthly_performance_audit_candidate_proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244.csv --benchmark-row-selector name=return_concentration --usd-krw-rate 1400.0 --external-data-dir data/auto_trading/free_external_data --output-dir data/reports/auto_trading
```

검증 명령:

```powershell
python -m unittest discover -s tests
python -m compileall -q backtester scripts
git diff --check
```

## 해석

신규 모델은 conservative 비용 시나리오에서도 benchmark보다 높은 net total return, 더 높은 net CAGR, 더 낮은 max_drawdown_abs_pct, 더 높은 risk-adjusted return을 기록했다. 모든 산출물은 paper-only/dry-run 정책을 유지하며 실주문 효과는 없다.
