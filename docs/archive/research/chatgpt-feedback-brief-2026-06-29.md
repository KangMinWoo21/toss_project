# ChatGPT 피드백 요청용 프로젝트 현황 브리프

작성일: 2026-06-29

## 1. 한 줄 요약

이 프로젝트는 토스증권/KRX/공시/뉴스/수급 데이터를 활용해 국내 주식 전략을 연구하고, 백테스트/검증/리스크 차단/월간 paper 주문계획/클라우드 수집까지 연결하는 Python CLI 기반의 안전 우선형 trading research 시스템이다.

현재 핵심 원칙은 **실거래 자동주문을 만들지 않고, 모든 운영 후보를 paper-operation과 사람 검토 단계에 묶어 둔다**는 것이다.

## 2. 프로젝트 목적

- 국내 주식 자동매매 후보 전략을 실거래 전에 검증한다.
- 단일 백테스트 수익률이 아니라 walk-forward, holdout, 장세별 검증, stress 검증, OOS 관찰을 통과했는지 본다.
- KRX OHLCV, Toss Open API, OpenDART, 뉴스/RSS/SNS, 투자자 수급 데이터를 연구용으로 통합한다.
- 월간 리밸런싱 후보에 대해 실제 주문이 아니라 CSV/Markdown 기반 주문계획과 리스크 리포트를 만든다.
- 데이터 품질, stale report, look-ahead bias, 위험 한도, production readiness gate를 통해 위험한 상태를 BLOCK한다.
- 노트북이 꺼져도 cloud VM에서 paper data collection과 월간 계획 생성을 유지할 수 있는 구조를 준비한다.

## 3. 현재 안전 원칙

- 실제 주문 실행 기능은 구현하지 않는다.
- `PRODUCTION_TRADING_ENABLED`는 기본적으로 꺼져 있어야 한다.
- readiness/production/risk 결과가 `BLOCK`이면 하드 스톱으로 본다.
- 테스트에서 Toss API나 외부 네트워크를 호출하지 않는다.
- `.env`의 실계정 정보, API 키, 증권사 credential은 출력/요약/커밋하지 않는다.
- 2026-06-18까지의 데이터는 고정 baseline으로 보고, 이후 post-cutoff 데이터는 튜닝이 아니라 paper-only OOS 관찰용으로만 쓴다.

## 4. 구현된 주요 기능

### 백테스트와 전략 검증

- 단일 종목 백테스트 엔진
- 기본 전략 비교: buy and hold, 이동평균, 변동성 돌파, RSI, 거래량 돌파 등
- 수수료, 세금, 슬리피지 반영
- 신호 발생 후 다음 시점 체결 구조로 look-ahead bias 완화
- walk-forward 검증과 rolling window 요약
- 장세별 전략 비교와 leader/swing/momentum 계열 검증

### 월간 리밸런싱 연구

- 월간 리밸런싱 백테스트
- point-in-time universe 사용
- 데이터 품질 미달 종목 제외
- 수급/이벤트 필터, 시장 추세/변동성 필터, drawdown guard, performance guard
- 월간 주문계획 CSV/Markdown 생성
- 주문별 `risk_status`, `risk_reasons`, execution block reason 기록
- deployment gate, validation suite, risk report, performance audit 생성

### 데이터 수집과 통합

- Toss Open API 기반 일봉/틱/호가/체결 조회 구조
- pykrx 기반 KRX OHLCV, universe snapshot, 시장 snapshot, 투자자 수급 수집
- OpenDART 공시/재무 데이터 이벤트화
- GDELT/Google News RSS/SNS CSV 이벤트 점수화
- 이벤트 데이터의 `event_date`와 `available_date`를 구분해 미래 데이터 누수 방지
- 데이터 품질 검사와 excluded symbols 리포트 생성

### 스캘퍼와 paper data collection

- Toss REST market data 기반 paper scalper
- 실제 주문 없이 tick/orderbook snapshot과 paper signal만 기록
- 저장된 tick CSV replay로 여러 rule variant 비교
- KR/US 시장 시간에 따라 paper scalper 수집을 자동으로 돌리는 구조

### 운영/클라우드 준비

- Linux VM용 systemd service/timer 스크립트
- cloud scalper, monthly plan, health check 실행 스크립트
- Windows에서 cloud report/scalper data를 내려받는 PowerShell 스크립트
- `production-check`, `health-check`로 운영 전 상태 점검

### 최근 추가된 연구-only 기능

- `docs/archive/research/macro_event_sentiment_overlay_research_plan.md`
  - macro/event/news/SNS risk overlay 연구 계획
  - production 전략 변경 없음
  - post-cutoff OOS 데이터로 튜닝 금지
- `backtester/macro_overlay.py`
  - macro/event/sentiment observation schema
  - risk score enum: `normal`, `caution`, `risk_off`, `panic`
  - 단순 deterministic risk score combiner
  - 기본값은 `overlay_config=disabled`, `production_effect=none`

## 5. 현재 상태

최근 체크포인트 기준:

- 전체 unittest: PASS, 641 tests
- `python -m compileall -q backtester`: PASS
- 기본 `production-check`: BLOCK
  - `BLOCK=8`, `PASS=33`, `WARN=8`
- candidate overlay 기준 `production-check`: BLOCK
  - `BLOCK=8`, `PASS=32`, `WARN=8`
- `health-check`: WARN
  - scalper data stale
  - 새 OHLCV 입력 이후 monthly universe price coverage 재생성 필요
- production은 아직 live-ready가 아니다.

현재 BLOCK 항목:

- `overall`
- `deployment_gate`
- `validation_scenarios`
- `validation_failure_actions`
- `validation_remediation`
- `validation_failure_patterns`
- `risk_report`
- `performance_report`

## 6. 현재 가장 좋은 후보 전략

현재 paper-review 후보:

`proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244`

이 후보가 좋아 보이는 이유:

- 기존 baseline의 required validation failures 5개를 full validation 안에서는 0개로 줄였다.
- `walk_forward_001`, `walk_forward_003`, `walk_forward_005` 문제를 해결했다.
- `regime_sideways` 구간에서 neutral-breadth 고노출 손실 cluster를 줄였다.
- stress/duration review에서는 0/5 failure, baseline regression 0으로 기록되었다.

하지만 아직 채택하지 않는 이유:

- point-in-time history gate를 `min_history244`로 완화한다.
- post-cutoff OOS에서 아직 실패했다.
- production/readiness가 계속 BLOCK이다.
- 현재 결정은 `PAPER_REVIEW`이며 promote/adopt가 아니다.

## 7. Post-cutoff OOS 관찰 상태

baseline cutoff: 2026-06-18

post-cutoff OOS는 paper-only 관찰 목적이며, 튜닝에 쓰면 안 된다.

최근 고정 파라미터 OOS 결과:

- status: `paper_oos_failed`
- trades: 12
- gross return: `-10.6872%`
- benchmark return: `-8.8464%`
- excess return: `-1.8408%`
- max drawdown: `-10.6165%`
- failed required scenarios: 7
- true short-history/data-quality blocks: 185

실패 원인 해석:

- 0-trade 문제는 해결되었고, 이제는 실제로 12건의 거래가 발생했다.
- 손실은 선택된 종목들의 짧은 OOS 구간 손실에서 주로 발생했다.
- short-history/data-quality block 185개는 traded/target symbols와 겹치지 않아 현재 excess gap의 주 원인으로 보기 어렵다.
- 현금 비중은 약 14.33%였고, 마이너스 benchmark 대비 방어에 도움을 준 쪽이다.

현재 관찰 계획:

- 최소 15개 추가 paper OOS trading days 관찰
- 다음 리뷰는 22 trading days 이후 권장
- OOS 성과를 보고 threshold를 조정하지 않는다.
- persistent negative excess, insufficient activity, drawdown 악화가 있으면 demotion review

## 8. 남아 있는 핵심 문제

### 1. Production readiness BLOCK

현재 시스템은 의도적으로 BLOCK 상태다. 자동주문을 켜기 위한 시스템이 아니라, 위험 상태를 차단하고 paper evidence를 쌓는 시스템으로 운용 중이다.

### 2. Regime sideways 취약성

기존 baseline의 주요 실패는 sideways regime에서의 negative excess와 drawdown이다. `min_history244` 후보가 full validation에서는 해결했지만 post-cutoff OOS에서 아직 실패했기 때문에 기본값으로 승격할 수 없다.

### 3. 데이터 품질과 universe coverage

- 데이터 품질 미달 종목 제외 목록이 중요하다.
- post-cutoff OHLCV/PIT universe alignment 문제를 해결했지만, 관찰 기간이 아직 짧다.
- health-check는 scalper data stale과 coverage 재생성 필요로 WARN이다.

### 4. 과최적화 위험

여러 candidate/sweep/guard 조합을 실험했기 때문에 post-cutoff OOS를 튜닝에 쓰면 과최적화가 심해질 수 있다.

### 5. 실제 체결 현실성

현재 비용 모델은 수수료/세금/슬리피지 중심이다. 실제 호가 충격, 거래정지, 상하한가, 대량 주문 market impact, 상장폐지 이력은 더 보강해야 한다.

## 9. 앞으로의 방향

### 단기

1. post-cutoff OOS를 최소 15개 추가 trading days 동안 그대로 관찰한다.
2. OOS 기간에는 threshold, guard, parameter를 조정하지 않는다.
3. stale scalper data와 monthly universe price coverage를 재생성해 health WARN을 줄인다.
4. production-check BLOCK 항목을 계속 하드 스톱으로 유지한다.
5. `regime_sideways` 실패 원인을 selection, recovery participation, missed winner, drawdown pressure 관점에서 더 분해한다.

### 중기

1. `min_history244` 후보를 채택할지 말지 OOS 관찰 후 판단한다.
2. 데이터 품질 미달 종목의 원인을 pykrx 원본, 수정주가, 병합 오류, 거래정지/상장폐지 이력으로 분류한다.
3. 거래비용 모델을 ADV 참여율, 예상 체결 불리함, turnover cost까지 확장한다.
4. macro/event/news/SNS overlay는 buy alpha가 아니라 risk overlay로만 research-only ablation을 진행한다.
5. cloud timer 실패, API 실패, CSV schema drift, report stale 상태를 감지하는 운영 모니터링을 강화한다.

### 장기

1. 실거래 자동주문은 계속 금지하고, 사람이 검토하는 주문계획 중심으로 유지한다.
2. paper-operation에서 충분한 OOS 기간과 안정성을 확보한 뒤에만 다음 단계의 운영 설계를 논의한다.
3. production readiness를 통과하더라도 즉시 live order로 연결하지 않고, 별도 승인/설계/리스크 리뷰를 요구한다.

## 10. ChatGPT에게 받고 싶은 피드백

아래 관점에서 비판적으로 검토해 주세요.

1. 현재 safety-first 구조가 실거래 전 research/paper-operation 시스템으로 충분히 보수적인가?
2. `PAPER_REVIEW` 후보를 post-cutoff OOS에서 관찰하는 방식이 과최적화 방지에 적절한가?
3. `min_history244`처럼 history gate를 완화한 후보를 평가할 때 추가로 봐야 할 리스크는 무엇인가?
4. `regime_sideways` 실패를 더 잘 진단하려면 어떤 리포트나 attribution이 필요한가?
5. macro/event/news/SNS overlay를 buy alpha가 아니라 risk overlay로 제한하는 방향이 합리적인가?
6. production readiness가 BLOCK인 상태에서 다음으로 가장 가치 있는 개발/검증 순서는 무엇인가?
7. 실제 주문 실행을 만들지 않는 전제에서, paper 주문계획과 운영 리포트를 더 신뢰 가능하게 만들려면 무엇을 보강해야 하는가?

## 11. 현재 판단

이 프로젝트는 단순 백테스터 단계는 넘어섰지만, 아직 실거래 자동화 시스템은 아니다. 현재 가장 합리적인 방향은 **실거래를 막은 상태로 paper OOS 관찰, 데이터 품질 강화, sideways regime 원인 분석, 운영 리포트 신뢰도 개선을 계속하는 것**이다.
