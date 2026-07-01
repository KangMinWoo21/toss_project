# 자동매매 엔진 선행 리서치

작성 기준일: 2026-07-01

## 목적

이 문서는 기존 국내주식 엔진과 KIS 미국주식 paper-only 트랙 위에 자동매매 엔진을 설계하기 전 참고할 자료를 정리한다. 목표는 실주문부터 붙이는 것이 아니라, 데이터 수집, 신호 생성, 포트폴리오 판단, 위험 통제, 주문계획, 감사 로그를 분리한 paper-first 엔진 구조를 잡는 것이다.

v1 설계의 결론은 다음과 같다.

- 외부 대형 엔진을 당장 의존성으로 추가하지 않는다.
- Lean, NautilusTrader, Freqtrade, Hummingbot은 구조와 안전장치 참고자료로 사용한다.
- KIS 미국주식 트랙은 `paper-only`, `dry-run`, `execution_allowed=False`를 유지한다.
- 자동 실행은 “신호 -> 계획 -> 보호/리스크 검증 -> 보고서”까지를 먼저 완성한다.
- 실주문은 별도 승인 게이트, kill switch, 모의 운용 관측 기간, 실패 복구 절차가 문서화되기 전까지 만들지 않는다.

## 핵심 참고 오픈소스

### QuantConnect Lean

- 링크: [QuantConnect/Lean](https://github.com/QuantConnect/Lean)
- 성격: C#/Python 기반 오픈소스 알고리즘 트레이딩 엔진.
- 참고할 점:
  - event-driven 구조.
  - backtest, optimization, live trading 명령을 같은 엔진 계열에서 다룬다.
  - 모듈형 설계와 플러그인 가능한 구성 요소를 강조한다.
  - 프로젝트 안에 `Engine`, `Brokerages`, `Data`, `Algorithm`, `Algorithm.Framework`, `Report`, `Tests`처럼 책임 경계가 분리되어 있다.
- 우리에게 주는 힌트:
  - `backtester/kis_us/`를 더 키우기보다, 상위에 `auto_trading/` 같은 오케스트레이션 레이어를 두고 브로커/전략/리스크/리포트를 분리하는 편이 좋다.
  - 백테스트와 paper 운용의 입력/출력 모델을 최대한 맞춰 research-to-paper 차이를 줄인다.

### NautilusTrader

- 링크: [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader), [문서](https://nautilustrader.io/docs/latest/)
- 성격: Rust core + Python control plane 구조의 multi-asset, multi-venue 트레이딩 엔진.
- 참고할 점:
  - deterministic event-driven architecture를 전면에 둔다.
  - research, simulation, live execution을 같은 실행 의미론으로 연결하려 한다.
  - adapter를 통해 REST/WebSocket venue를 정규화된 도메인 모델로 변환한다.
  - cache, message bus, adapter, execution semantics 같은 엔진 내부 경계를 명확히 둔다.
- 우리에게 주는 힌트:
  - KIS REST 조회 결과를 바로 전략에 넘기지 말고, 내부 `MarketSnapshot`, `PositionSnapshot`, `OrderIntent`, `PlannedOrder` 같은 표준 모델로 변환한다.
  - 재현 가능한 paper run을 위해 “입력 스냅샷 + 신호 + 계획 + 리스크 결과”를 모두 저장한다.

### Freqtrade

- 링크: [Freqtrade 문서](https://www.freqtrade.io/en/stable/)
- 성격: Python 기반 오픈소스 crypto trading bot.
- 참고할 점:
  - dry-run을 먼저 권장한다.
  - 전략 개발, 데이터 다운로드, 백테스트, 최적화, pairlist/blacklist, simulated/live mode, WebUI/Telegram 모니터링을 제공한다.
  - stoploss, trailing stop, ROI, hyperopt 등 전략 파라미터와 보호장치가 제품 수준으로 분리되어 있다.
- 우리에게 주는 힌트:
  - 처음부터 “자동주문”보다 “paper run 상태 관찰”과 “운영 UI/리포트”가 중요하다.
  - 종목 universe와 blacklist/protected positions를 엔진 핵심 정책으로 둬야 한다.
  - 설정 파일과 CLI override의 우선순위를 명확히 해야 한다.

### Hummingbot

- 링크: [Hummingbot](https://hummingbot.org/)
- 성격: CEX/DEX 자동매매와 market making에 강한 오픈소스 Python 프레임워크.
- 참고할 점:
  - client, gateway, API, UI/monitoring 계층을 나눈다.
  - connector 중심 구조로 다양한 거래소/체인을 붙인다.
  - 전략 프레임워크와 connector를 분리한다.
- 우리에게 주는 힌트:
  - KIS를 “브로커 connector”로 보고, 전략은 KIS를 직접 알지 못하게 해야 한다.
  - 국내주식, KIS 미국주식, 향후 다른 브로커를 같은 내부 인터페이스 뒤에 둘 수 있다.

### Backtrader / vectorbt

- 링크: [Backtrader](https://github.com/mementum/backtrader), [vectorbt](https://github.com/polakowo/vectorbt)
- 성격:
  - Backtrader: Python event-style 백테스팅 프레임워크.
  - vectorbt: NumPy/Pandas 기반 대규모 vectorized research/backtest 도구.
- 참고할 점:
  - 자동매매 실행 엔진으로 바로 쓰기보다는 연구/검증 계층 참고에 적합하다.
  - 대량 파라미터 검증과 walk-forward 분석은 vectorized 연구 도구가 유리하다.
- 우리에게 주는 힌트:
  - 실시간 엔진은 event-driven으로 두고, 후보 전략 발굴/검증은 기존 backtester와 벡터화 리포트 쪽에 남긴다.

## 규제/통제 참고자료

### FINRA Regulatory Notice 15-09

- 링크: [FINRA Regulatory Notice 15-09](https://www.finra.org/rules-guidance/notices/15-09)
- 핵심:
  - 알고리즘 전략이 시장/회사 안정성에 악영향을 줄 수 있으므로 supervision/control practice가 필요하다고 본다.
  - 중점 영역은 risk assessment, software/code development, testing/validation, trading systems, compliance다.
  - SEC Market Access Rule 15c3-5도 언급하며, market access 관련 financial/regulatory risk control을 요구한다.
- 우리에게 주는 힌트:
  - 자동매매 엔진에는 “전략 코드”보다 “승인/검증/관측/중지”가 먼저 들어가야 한다.
  - 리스크 위반 시 주문을 줄이는 것이 아니라 fail-closed로 차단해야 한다.
  - 운영 로그는 사람이 사후 검토할 수 있어야 한다.

### kill switch / circuit breaker 관점

- 참고: FINRA 15-09, SEC Market Access Rule 언급, 알고리즘 트레이딩 통제 논문.
- 우리에게 필요한 최소 통제:
  - 전역 kill switch: 파일 또는 env로 `AUTO_TRADE_ENABLED=false`면 어떤 주문도 실행하지 않는다.
  - 전략별 kill switch: 특정 strategy_id 중지.
  - 종목별 kill switch: protected positions / no-trade list.
  - 손실/드로다운 중지: 일간 손실, 누적 손실, 연속 실패, 급등락, 시세 누락.
  - API 이상 중지: 403/500 반복, stale quote, 잔고 불일치.
  - 주문 한도: 주문 횟수, 종목별 수량, 총 노출, 현금 사용률, 가격 괴리.

## 논문/연구 메모

### Nine Challenges in Modern Algorithmic Trading and Controls

- 링크: [arXiv:2101.08813](https://arxiv.org/abs/2101.08813)
- 핵심:
  - 자동매매의 과제는 전략만이 아니라 illiquid securities, optimal execution, risk management, automated controls, testing/simulation까지 포함된다.
- 반영 원칙:
  - v1은 alpha보다 controls를 먼저 만든다.
  - 시뮬레이션/페이퍼 운용에서 리스크 로그를 축적한 뒤 자동화를 확장한다.

### mt5se: An Open Source Framework for Building Autonomous Trading Robots

- 링크: [arXiv:2101.08169](https://arxiv.org/abs/2101.08169)
- 핵심:
  - 백테스트 성능이 실제 시장에서 잘 이어지지 않는 문제를 지적한다.
  - price prediction과 capital allocation을 분리하는 multi-agent 구조를 제안한다.
- 반영 원칙:
  - 우리 엔진도 `Signal`과 `Allocation/Planner`를 분리한다.
  - 전략은 “매수/매도”가 아니라 점수, 목표비중, 금지 사유를 낸다.

### PLUTUS Open Source

- 링크: [arXiv:2505.14050](https://arxiv.org/abs/2505.14050)
- 핵심:
  - 알고리즘 트레이딩의 재현성, 표준화, 문서화 부족을 문제로 보고 open/reproducible framework를 제안한다.
- 반영 원칙:
  - 모든 paper run은 설정, 입력 데이터 버전, 생성된 신호, 리스크 결과, 주문계획을 함께 저장한다.
  - 실험/운영 산출물은 사람이 재실행 가능한 CLI 명령과 함께 남긴다.

### Optimal Execution / Slippage

- 링크: [Optimal Trade Execution with Uncertain Volume Target](https://arxiv.org/abs/1810.11454)
- 배경: Almgren-Chriss 계열 최적집행 연구는 가격 변동 위험과 시장충격/슬리피지 사이의 균형을 다룬다.
- 반영 원칙:
  - v1은 시장가 자동주문을 만들지 않는다.
  - 주문계획에는 reference_price, estimated_value, max_price_deviation, stale_quote_seconds를 포함해야 한다.
  - 나중에 주문 실행을 붙이더라도 “한 번에 전량”보다 child order, 가격 제한, 체결 관측이 필요하다.

### Backtest Overfitting

- 참고 링크:
  - [Determining Optimal Trading Rules without Backtesting](https://arxiv.org/abs/1408.1159)
  - [Avoiding Backtesting Overfitting by Covariance-Penalties](https://arxiv.org/abs/1905.05023)
  - [Backtesting Trading Strategies with GAN To Avoid Overfitting](https://arxiv.org/abs/2209.04895)
- 반영 원칙:
  - 자동매매 후보 전략은 단일 backtest 결과로 승격하지 않는다.
  - 최소 조건: walk-forward, holdout, 비용/슬리피지 포함, 시장국면별 성과, 실패 패턴 리포트.

## 자동매매 엔진 기본 아키텍처 후보

v1에서 권장하는 모듈 경계는 아래와 같다.

```text
MarketDataAdapter
  -> MarketSnapshot

AccountAdapter
  -> PositionSnapshot / CashSnapshot

Strategy
  -> Signal / TargetWeight / NoTradeReason

PortfolioPolicy
  -> DesiredPortfolio

RiskEngine
  -> ApprovedIntent / BlockedIntent

OrderPlanner
  -> PlannedOrder

ExecutionGateway
  -> PaperExecutionResult only in v1

AuditStore
  -> run manifest, input snapshots, reports, errors
```

### 모듈별 책임

- `MarketDataAdapter`
  - KIS 시세, 기존 CSV, 향후 다른 브로커 데이터를 내부 모델로 변환한다.
  - stale quote, 가격 0, 거래소 코드 오류를 fail-closed로 처리한다.
- `AccountAdapter`
  - 잔고/현금/보호 포지션을 내부 모델로 변환한다.
  - 계좌번호와 secret은 어떤 리포트에도 쓰지 않는다.
- `Strategy`
  - 가격/지표/신호를 계산한다.
  - 주문 수량이나 API 호출을 직접 만들지 않는다.
- `PortfolioPolicy`
  - 신호를 목표비중으로 바꾼다.
  - 집중도, 최대 종목 수, 최소 현금 비율을 적용한다.
- `RiskEngine`
  - 전역/전략/종목 kill switch를 본다.
  - 일간 손실, max drawdown, 주문 횟수, protected positions, API 상태를 검사한다.
- `OrderPlanner`
  - 목표비중과 현재 포지션을 dry-run 주문계획으로 바꾼다.
  - 모든 v1 계획은 `execution_allowed=False`다.
- `ExecutionGateway`
  - v1에서는 실주문 메서드를 만들지 않는다.
  - paper fill simulator만 허용한다.
- `AuditStore`
  - 모든 run의 config hash, input paths, API summary, generated plan, risk blocks, exceptions를 저장한다.

## v1 구현에 반영할 원칙

1. 실주문보다 paper-run 오케스트레이션을 먼저 만든다.
2. 전략은 broker/KIS를 모르게 한다.
3. 주문계획은 항상 risk result를 포함한다.
4. protected positions와 no-trade list는 전략보다 높은 우선순위를 가진다.
5. broker API 오류는 재시도보다 먼저 fail-closed로 기록한다.
6. 수동 cash override는 보고서에 표시하되, 실제 계좌 현금과 구분한다.
7. API 호출 빈도 제한을 엔진 설정으로 둔다.
8. 모든 run은 재현 가능한 manifest를 남긴다.
9. live order code는 별도 패키지/별도 승인 없이는 만들지 않는다.

## 우리 프로젝트의 다음 설계 후보

새 패키지는 기존 국내 엔진과 KIS paper-only 모듈을 건드리지 않고 추가하는 방향이 좋다.

```text
backtester/auto_trading/
  __init__.py
  models.py
  config.py
  adapters.py
  strategy_protocol.py
  portfolio_policy.py
  risk_engine.py
  order_planner.py
  audit_store.py
  orchestrator.py
```

CLI 후보:

```powershell
python -m backtester auto-paper-run `
  --strategy momentum_rotation_v1 `
  --universe data/examples/kis_us_targets_sample.csv `
  --broker kis-us `
  --cash-usd 100000 `
  --mode paper `
  --output-dir data/reports/auto_trading
```

초기 산출물:

- `manifest.json`: 설정, 시각, 입력 파일, git 상태 요약.
- `market_snapshot.csv`: 시세 스냅샷.
- `account_snapshot.csv`: 잔고/현금 스냅샷.
- `signals.csv`: 전략 신호.
- `risk_report.csv`: 차단/승인 사유.
- `order_plan.csv`: dry-run 주문계획.
- `summary.md`: 사람이 읽는 요약.

## 결론

자동매매 엔진은 “전략 자동화”가 아니라 “통제 가능한 의사결정 파이프라인”으로 시작해야 한다. 지금 상태에서 가장 좋은 다음 단계는 KIS 미국주식 paper-only 계획 생성기를 하위 adapter로 두고, 그 위에 `auto_trading` 오케스트레이터와 `RiskEngine`을 얹는 것이다.

v1은 실주문 없이 아래까지만 만든다.

- 시세/잔고 스냅샷 생성
- 전략 신호 생성
- 목표비중 생성
- 리스크 차단
- dry-run 주문계획
- 감사 가능한 run manifest/report

실주문은 별도 리서치, 운영 런북, kill switch, 모의 운용 관측 결과가 준비된 뒤에만 논의한다.
