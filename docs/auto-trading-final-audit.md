# 미국주식 Paper-Only 자동매매 엔진 Final Audit

## 결론

미국주식 paper-only 자동매매 엔진은 `backtester/auto_trading/`에 분리 구현되어 있으며, 실주문 실행 경로 없이 로컬 CSV 기반 성과 비교, KIS paper-only 주문계획, execution/TCA/monitoring 리포트를 생성한다.

전략 목표 상태는 `data/reports/auto_trading/auto_paper_audit_log.json` 기준 `engine_status=SUCCESS`, `objective_status=COMPLETE`다. 기준 모델 대비 비교는 gross가 아니라 세금, 수수료, 슬리피지, FX buffer proxy를 반영한 net 성과 기준이다.

## 핵심 증거

| 항목 | 증거 |
| --- | --- |
| 신규 엔진 분리 | `backtester/auto_trading/` |
| KIS paper-only 분리 | `backtester/kis_us/` |
| PR 검토용 핵심 증거 패킷 | `docs/auto-trading-final-evidence.md` |
| 기준 모델 감사 해시 | `benchmark_report_sha256=802351b5ffec93c0b96f5cf72010bf0ce4fa60cbafbb15409d356587f326aefe` |
| 전략 목표 상태 | `data/reports/auto_trading/auto_paper_audit_log.json` |
| 순성과 비교 | `data/reports/auto_trading/auto_paper_performance.csv` |
| 비용 정책 | `data/reports/auto_trading/auto_paper_cost_policy.md` |
| 모델 등록 | `data/reports/auto_trading/auto_paper_model_registry.json` |
| KIS 주문계획 | `data/reports/kis_us_paper_order_plan_from_auto_risk_adjusted_demo.csv` |
| execution simulator | `data/reports/auto_trading/auto_paper_execution_simulation.csv` |
| market impact | `data/reports/auto_trading/auto_paper_market_impact.csv` |
| factor risk | `data/reports/auto_trading/auto_paper_factor_risk.csv` |
| optimizer | `data/reports/auto_trading/auto_paper_optimized_targets.csv` |
| TCA | `data/reports/auto_trading/auto_paper_tca.csv` |
| scheduler monitoring | `data/reports/auto_trading/auto_paper_scheduler_monitoring.csv` |

## Hard Gate 상태

| Gate | 상태 | 근거 |
| --- | --- | --- |
| 기존 국내주식 엔진 미변경 | PASS | 변경은 신규 `auto_trading`, `kis_us`, CLI 연결, 문서/테스트/데이터 산출물 중심 |
| 신규 엔진 모듈화 | PASS | `benchmark`, `costs`, `runner`, `portfolio_optimizer`, `factor_risk`, `execution_simulator`, `market_impact`, `tca`, `monitoring` 등 분리 |
| 실주문 금지 | PASS | KIS 주문 메서드 없음, 모든 실행 산출물 `execution_allowed=False` |
| output row safety flags | PASS | 주요 CSV row에 `paper_only=True`, `dry_run=True`, `execution_allowed=False`, `production_effect=none` 포함 |
| Yahoo daily data + KIS plan 연결 | PASS | auto paper target -> KIS target -> KIS paper order plan demo 생성 |
| benchmark 기준 로드/감사 | PASS | benchmark SHA-256와 row selector audit log 저장 |
| net 성과 기준 benchmark 초과 | PASS | `objective_status=COMPLETE`, conservative net total return 초과 |
| MDD 정규화 | PASS | `max_drawdown_abs_pct` 사용 |
| 비용/세금 정책 | PASS | fee/slippage/fx buffer, FIFO, settlement-date tax year, constant FX tax proxy 문서화 |
| walk-forward/train-test 검증 | PASS | validation scenarios와 audit log의 walk-forward margin PASS |
| 비용 민감도 | PASS | base/conservative scenario 저장 |
| local CSV only run | PASS | `auto-paper-run` 네트워크 차단 테스트 및 fetch 분리 |
| survivorship warning | PASS | universe schema와 audit/report warning 저장 |
| scheduler monitoring | PASS | `auto-paper-monitoring-report` PASS |

## 월가식 보완 항목의 v1 범위

| 항목 | v1 구현 |
| --- | --- |
| 실시간 호가/체결 execution model | daily bar 기반 paper execution simulator |
| 주문장/시장충격 모델 | ADV/volatility/spread proxy 기반 market impact |
| factor risk model | sector, beta, size, value, quality, momentum exposure |
| 체결 비용 추정 | fee/slippage/spread/impact/TCA proxy |
| 대체데이터 | SEC/FINRA/Alpha Vantage/GDELT/Nasdaq Trader CSV readiness adapter |
| survivorship-bias 완화 | point-in-time universe loader와 warning |
| OMS/EMS, kill switch | 실주문 없음, scheduler monitoring, production_effect=none |
| post-trade TCA | paper fill 기반 TCA simulator |

## 한계

이 결과는 paper-only 연구 엔진 완성이다. 실제 월가 수준의 live OMS/EMS, venue routing, NBBO, tick/order-book replay, broker별 체결장, Barra/Axioma급 factor covariance, survivorship-bias-free 상용 데이터셋은 포함하지 않는다. 해당 항목은 현재 무료/로컬 데이터 기반 proxy로 구현했다.
