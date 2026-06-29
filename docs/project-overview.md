# 토스증권 자동매매 연구 프로젝트 전체 설명서

작성 기준일: 2026-06-21

이 문서는 `C:\Users\KangMinWoo\Documents\토스증권` 저장소의 목적, 구조, 주요 모듈, 데이터 흐름, 안전장치, 백테스트/운영 워크플로우를 한눈에 파악하기 위한 프로젝트 설명서다.

## 1. 프로젝트의 정체성

이 프로젝트는 단순 백테스터가 아니라 **국내/미국 주식 데이터를 수집하고, 여러 전략을 검증하고, 월간 리밸런싱 주문계획과 생산 준비성 리포트를 생성하는 연구 및 paper-operation 시스템**이다.

핵심 목표는 다음과 같다.

- 국내 주식 중심의 자동매매 후보 전략 연구
- KRX, pykrx, Toss Open API, DART, 뉴스/SNS, 투자자 수급 데이터 통합
- 단일 구간 성과가 아니라 walk-forward, holdout, 장세별, 스트레스 검증 수행
- 실거래 실행이 아닌 **검토 가능한 주문계획** 생성
- 데이터 품질, 편향, stale 리포트, 위험 한도, readiness gate를 통해 안전하게 차단
- 노트북이 꺼져도 클라우드 VM에서 데이터 수집과 월간 paper plan을 유지할 수 있는 구조 마련

중요한 원칙은 **실제 주문 실행을 구현하지 않는다**는 것이다. 현재 시스템은 live executor가 없고, `monthly-plan`도 주문을 넣지 않고 CSV/Markdown 계획만 만든다.

## 2. 전체 아키텍처 개요

```text
데이터 수집
  Toss Open API / pykrx / DART / 뉴스 / SNS / 수급
        ↓
CSV 저장
  data/, data/krx_expanded/, data/reports/
        ↓
데이터 품질 검사
  data-check, data_quality.py, exclude symbols
        ↓
전략 연구
  compare, walk-forward, leader-swing, momentum, monthly-backtest
        ↓
검증
  monthly-validate, regime/stress/duration validation
        ↓
주문계획 생성
  monthly-plan, risk_status, risk_reasons
        ↓
운영 게이트
  production-check, readiness.py, report freshness, risk reports
        ↓
사람 검토
  CSV/Markdown reports only, no live orders
```

## 3. 저장소 구조

```text
backtester/      핵심 Python 패키지
tests/           unittest 기반 회귀 테스트
data/            샘플 데이터, 수집 데이터, 리포트 출력 위치
docs/            API 가이드, 운영 문서, 전략 검토 문서
scripts/         Windows/Cloud 자동화 스크립트
scripts/cloud/   Linux VM systemd 및 수집/월간 계획 스크립트
.env.example     환경변수 예시
.env             로컬 비밀값, 커밋 금지
README.md        기본 실행 안내
AGENTS.md        저장소 contributor guide
```

## 4. 핵심 패키지 구조

### CLI 진입점

- `backtester/__main__.py`
  - 모든 CLI 명령의 진입점이다.
  - `python -m backtester ...` 명령을 처리한다.
  - 데이터 수집, 전략 비교, 월간 백테스트, 월간 검증, production-check, scalper 수집/리플레이 등을 연결한다.

### 공통 모델과 데이터 로딩

- `models.py`
  - `Candle` 같은 기본 시장 데이터 모델을 정의한다.
- `data.py`
  - OHLCV CSV를 `Candle` 리스트로 로드한다.
- `data_quality.py`
  - 캔들 CSV, 데이터셋 freshness, universe metadata를 검증한다.
  - `DataQualityResult`에는 `status`, `issues`, `warnings`, `latest_date`, `stale_days`, `rows_checked`, `blocked_symbols`가 포함된다.
  - `data-check --exclude-output`으로 품질 미달 종목 CSV를 만들 수 있다.

### 외부 데이터 수집

- `toss.py`
  - Toss Open API 인증, 일봉/틱/호가/체결/시장시간 조회를 담당한다.
  - 테스트에서는 실제 Toss API를 호출하지 않는 것이 원칙이다.
- `pykrx_fetcher.py`
  - pykrx 기반 KRX OHLCV, universe snapshot, 시장 snapshot, 수급 데이터 수집을 담당한다.
- `dart.py`
  - OpenDART 공시와 재무 계정 데이터를 이벤트/재무 CSV로 변환한다.
- `news.py`
  - GDELT, Google News RSS, SNS CSV를 이벤트 점수 CSV로 변환한다.
- `flow.py`
  - 외국인/기관/개인/내부자 수급 데이터를 점수화한다.
- `events.py`
  - 뉴스/SNS/DART 이벤트 점수를 로드하고 병합한다.
  - `event_date`와 `available_date`를 구분한다.
  - 전략에는 `available_date <= as_of_date`인 데이터만 반영하여 look-ahead bias를 줄인다.
  - legacy CSV에 `date`만 있으면 경고와 함께 사용 가능일로 간주한다.

### 전략과 백테스트

- `engine.py`
  - 단일 종목 전략 백테스트 엔진이다.
  - 신호 발생 후 다음 시점 체결 등 look-ahead 방지를 반영한다.
- `strategies.py`
  - buy-and-hold, 이동평균, 변동성 돌파, RSI, 거래량 돌파, 뉴스/수급 필터 전략을 포함한다.
- `analysis.py`
  - rolling window, walk-forward 분석 유틸리티를 제공한다.
- `study.py`
  - 여러 종목과 장세에서 전략을 비교한다.
- `regime.py`
  - 상승/하락/횡보 장세 분류 로직을 제공한다.

### 월간 모멘텀/리밸런싱 계열

- `momentum_rotation.py`
  - cross-sectional momentum rotation 전략과 preset 설정을 다룬다.
- `momentum_validation.py`
  - train-only selection, yearly walk-forward, holdout 검증을 수행한다.
- `monthly_rebalance.py`
  - 현재 가장 중요한 운영 후보 로직이다.
  - 월간 리밸런싱 의사결정, point-in-time universe, 수급/이벤트 필터, 시장 추세/변동성 필터, drawdown guard, performance guard, 주문계획, 리스크 리포트, validation suite를 포함한다.
  - 실제 주문 실행이 아니라 `PlannedOrder`와 리포트 생성에 집중한다.
- `readiness.py`
  - production readiness를 평가한다.
  - deployment gate, validation scenarios, risk report, coverage report, performance report, freshness, data quality를 종합해 `PASS/WARN/BLOCK`을 만든다.

### 스윙/주도주 계열

- `leader_swing.py`
  - 거래대금이 높은 주도주를 대상으로 하는 스윙 로테이션 백테스트.
  - max position weight, cash buffer, ADV 제한, 손실 제한 등을 반영한다.
- `leader_regime_switch.py`
  - 장세에 따라 leader strategy 설정을 바꾸는 실험 구조.
- `leader_window_study.py`
  - 주도주 전략의 윈도우별 검토.
- `swing_sweep.py`
  - 스윙 전략 파라미터 sweep과 후보 검증.

### 스캘퍼/초단기 데이터 수집

- `scalper.py`
  - Toss REST market data를 이용한 paper scalper 로직.
  - 실제 주문이 아니라 틱/호가 기반 paper signal과 CSV 저장 중심이다.
- `auto_scalper.py`
  - 한국장/미국장 개장 시간에 따라 자동으로 paper scalper 수집 루프를 돌린다.
  - market closed 상태에서는 sleep한다.
- `scalp_replay.py`
  - 저장된 tick CSV를 여러 룰로 replay해 성과를 비교한다.

### 리스크/포트폴리오/주문계획 공통 모듈

- `portfolio.py`
  - 현재 비중 계산, 목표 비중 cap, 리밸런싱 후보 주문 계산을 제공한다.
- `risk.py`
  - 최대 단일 비중, 최대 보유 종목 수, 가격 누락, 차단 종목, stale 종목, 유동성 제약을 검증한다.
- `execution_plan.py`
  - 독립 주문계획 CSV 스키마를 정의한다.
  - `OrderPlanRow`에는 `plan_id`, `rebalance_date`, `symbol`, `side`, `weights`, `amounts`, `estimated_quantity`, `risk_status`, `risk_reasons`, `created_at`이 포함된다.

### 리포팅

- `reporting.py`
  - 전략 비교, walk-forward, 후보 검증 표를 사람이 읽기 좋게 출력한다.

## 5. 주요 CLI 명령

### 단일/기본 백테스트

```powershell
python -m backtester run --data data/sample_kr_stock.csv --strategy volatility_breakout
python -m backtester compare --data data/sample_kr_stock.csv
python -m backtester walk-forward --data data/sample_kr_stock.csv --train-size 60 --test-size 20
```

### 데이터 품질 검사

```powershell
python -m backtester data-check --path data/krx_expanded --max-stale-days 7
python -m backtester data-check --path data/krx_expanded --max-stale-days 7 --exclude-output data/reports/data_quality_excluded_symbols.csv
```

현재 실데이터 기준으로 `data/krx_expanded`에는 품질 BLOCK 종목이 존재하며, 제외 파일에는 355개 종목이 기록된 상태다.

### Toss/KRX/DART/뉴스 수집

```powershell
python -m backtester fetch-toss --symbol 005930 --output data/toss/005930.csv
python -m backtester fetch-pykrx-ohlcv --symbol 005930 --start 20240101 --end 20260621 --output data/krx_expanded/005930.csv
python -m backtester fetch-dart-events --symbol 005930 --start 2026-01-01 --end 2026-06-21 --output data/dart_events.csv
python -m backtester fetch-google-news-events --symbol 005930 --query "삼성전자" --output data/news_events.csv
```

### 이벤트/SNS 병합

```powershell
python -m backtester import-social-events --input data/social.csv --output data/social_events.csv --symbol 005930
python -m backtester merge-events --input data/news_events.csv --input data/social_events.csv --output data/events_combined.csv
```

### 월간 전략

```powershell
python -m backtester monthly-backtest --data-dir data/krx_expanded --start 2024-01-01 --end 2026-06-18 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --exclude-symbols data/reports/data_quality_excluded_symbols.csv
```

```powershell
python -m backtester monthly-validate --data-dir data/krx_expanded --start 2024-01-01 --end 2026-06-18 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --exclude-symbols data/reports/data_quality_excluded_symbols.csv
```

```powershell
python -m backtester monthly-plan --data-dir data/krx_expanded --as-of 2026-06-20 --exclude-symbols data/reports/data_quality_excluded_symbols.csv
```

### 생산 준비성 확인

```powershell
python -m backtester production-check --strict --max-report-age-days 45 --data-quality-path data/krx_expanded
```

현재 readiness는 `data_quality` 문제 때문에 `BLOCK`이 되는 것이 정상이다.

### 스캘퍼 수집/리플레이

```powershell
python -m backtester paper-scalp --symbol AAPL --iterations 10 --interval-seconds 1
python -m backtester auto-scalp --kr-symbols 005930,000660 --us-symbols AAPL,NVDA,TSLA,QQQ
python -m backtester scalp-replay --data-dir data/scalper
```

## 6. 데이터와 주요 파일

### 입력 데이터

- `data/sample_kr_stock.csv`
  - 샘플 OHLCV 데이터
- `data/sample_events.csv`
  - 뉴스/SNS 이벤트 샘플
- `data/sample_flows.csv`
  - 투자자 수급 샘플
- `data/krx_expanded/`
  - 실제 KRX OHLCV 데이터 저장 위치
- `data/krx_metadata/krx_universe_monthly.csv`
  - 월별 point-in-time universe snapshot

### 리포트 출력

- `data/reports/monthly_validation_scenarios*.csv`
  - 월간 전략 검증 시나리오 결과
- `data/reports/monthly_deployment_gate*.csv`
  - 배포 가능 여부 요약
- `data/reports/monthly_risk_report.csv`
  - 월간 주문계획 전 리스크 체크
- `data/reports/monthly_order_plan.csv`
  - 주문계획 CSV
- `data/reports/monthly_order_plan_summary.md`
  - 사람이 읽는 주문계획 요약
- `data/reports/production_readiness.csv`
  - production readiness CSV
- `data/reports/production_readiness_report.md`
  - 사람이 읽는 production readiness 보고서
- `data/reports/data_quality_excluded_symbols.csv`
  - 데이터 품질 미달 종목 제외 목록

## 7. 안전장치 구조

이 프로젝트는 자동주문 시스템처럼 보이지만 실제 설계는 **차단 우선**이다.

### 기본 안전 플래그

- `PRODUCTION_TRADING_ENABLED`는 기본적으로 꺼져 있다.
- 환경변수에 `true`, `1`, `yes`, `on` 같은 명시값을 넣어야 enabled로 해석된다.
- enabled여도 현재 저장소에는 실제 live order executor가 없다.

### 월간 주문계획 안전성

`monthly-plan`은 주문을 실행하지 않는다. 대신 다음을 생성한다.

- decision CSV
- order plan CSV
- order plan Markdown summary
- risk report CSV

각 주문 row에는 다음 안전 필드가 포함된다.

- `execution_allowed`
- `execution_mode`
- `execution_block_reason`
- `risk_status`
- `risk_reasons`

기본적으로 `PRODUCTION_TRADING_ENABLED`가 꺼져 있으면 risk check가 `PASS`여도 `BLOCKED`로 남는다.

### 리스크 체크

월간 계획은 다음을 본다.

- kill switch 파일 존재 여부
- 당일 손실 제한
- deployment gate 통과 여부
- performance guard 상태
- signal age
- 전체 목표 비중
- 음수 목표 비중
- SKIP 주문 여부
- 주문 개수
- 단일 주문 금액
- 총 매수/매도 금액
- 보유 수량 초과 매도 여부
- 주문 shape
- report freshness

### production-check

`production-check`는 다음을 종합한다.

- 필수 artifact 존재 여부
- deployment gate
- validation scenario
- risk report
- universe price coverage
- performance report
- report freshness
- data quality

결과는 `PASS`, `WARN`, `BLOCK`이다. `--strict`에서는 `WARN`도 비정상 종료 코드로 처리한다.

## 8. Look-ahead Bias 방지

이 저장소는 미래 데이터를 실수로 쓰지 않도록 여러 장치를 넣었다.

- 단일 백테스터는 신호를 다음 시점 체결로 처리한다.
- 월간 전략은 `as_of_date` 기준으로 볼 수 있는 데이터만 사용한다.
- point-in-time universe는 signal date 이전 최신 snapshot을 사용한다.
- 이벤트 데이터는 `available_date` 기준으로 반영한다.
- `event_date`는 사건 발생일이고, `available_date`는 전략이 실제로 알 수 있는 날짜다.
- legacy 이벤트 CSV에 `date`만 있으면 경고를 남기고 사용 가능일로 fallback한다.
- 사용 가능한 날짜가 없는 이벤트 row는 제외한다.

## 9. 백테스트 현실성

현재 백테스트는 다음 비용 요소를 지원한다.

- `fee_rate`
- `tax_rate`
- `slippage_rate`
- `min_trade_value`
- 월간 전략의 리밸런싱 주문 단위

다만 아직 실제 체결 호가, 대량 주문 impact, 호가 공백, 상장폐지/거래정지 전체 이력, 공매도/대주/차입 비용까지 완전히 모델링하지는 않는다. 따라서 결과는 실거래 수익 예측이 아니라 전략 후보의 상대적 검증 자료로 봐야 한다.

## 10. 현재 관측된 중요한 상태

최근 검사 기준:

- `pytest`는 설치되어 있지 않아 실행 불가
- `python -m unittest discover -s tests`는 261개 테스트 통과
- `python -m compileall -q backtester` 통과
- `data/krx_expanded` 품질 검사 결과 `BLOCK`
- 품질 미달 제외 종목 수: 355개
- 제외 목록 적용 월간 백테스트:
  - 총수익: `+81.22%`
  - buy-and-hold: `+16.96%`
  - 초과수익: `+64.26%`
  - MDD: `-24.04%`
  - universe: 2184개

해석:

- 기존의 높은 성과 일부는 품질 미달 데이터에 민감했을 가능성이 있다.
- 이제부터는 `data_quality_excluded_symbols.csv`를 적용한 검증 결과를 더 신뢰해야 한다.
- 현재 production readiness가 `BLOCK`인 것은 안전장치가 의도대로 작동한 것이다.

## 11. 클라우드/노트북 오프라인 운영

관련 파일:

- `scripts/cloud/run_auto_scalper.sh`
- `scripts/cloud/run_scalper.sh`
- `scripts/cloud/run_monthly_plan.sh`
- `scripts/cloud/toss-scalper.service`
- `scripts/cloud/toss-monthly-plan.service`
- `scripts/cloud/toss-monthly-plan.timer`
- `scripts/download_scalper_data.ps1`
- `scripts/download_cloud_reports.ps1`
- `scripts/register_scalper_download_task.ps1`
- `scripts/register_cloud_reports_download_task.ps1`

구상은 다음과 같다.

- Google Cloud VM에서 paper scalper 데이터 수집
- 시장 시간에 따라 KR/US 자동 분기
- 월간 paper plan을 systemd timer로 생성
- 노트북이 켜지면 Windows scheduled task로 cloud reports와 scalper CSV를 내려받음
- live order executor는 없음
- 운영 전 최종 게이트는 `production-check --strict`

## 12. 테스트 구조

테스트는 `unittest` 기반이며 `tests/` 아래에 모듈별로 위치한다.

주요 테스트 영역:

- `test_engine.py`: 체결 시점, 비용, 신호 처리
- `test_events.py`: 이벤트 병합, source weight, available_date
- `test_flow.py`: 수급 점수화
- `test_monthly_rebalance.py`: 월간 전략, 주문계획, 리스크, 검증
- `test_readiness.py`: production readiness
- `test_data_quality.py`: 데이터 품질 검사
- `test_execution_plan.py`: 주문계획 CSV 스키마
- `test_portfolio.py`, `test_risk.py`: 공통 포트폴리오/리스크 로직
- `test_scalper.py`, `test_auto_scalper.py`, `test_scalp_replay.py`: paper scalper
- `test_cli.py`: CLI 명령 회귀
- `test_cloud_scripts.py`: cloud script 안전성

표준 검증 명령:

```powershell
python -m unittest discover -s tests
python -m compileall -q backtester
```

`pytest`를 쓰려면 별도 설치가 필요하다.

## 13. 실사용 전 남은 핵심 과제

이 프로젝트는 이미 단순 실험기를 넘어 paper-operation에 가까운 구조를 갖췄지만, 실사용 수준으로 보려면 다음이 남아 있다.

1. 데이터 품질 BLOCK 종목의 원인 조사
   - pykrx 원본 문제인지, 액면/수정주가 문제인지, 병합 오류인지 구분해야 한다.
2. 제외 목록 기준 `monthly-validate` 재실행
   - 기존 리포트보다 제외 목록 적용 리포트를 기준으로 봐야 한다.
3. point-in-time universe 개선
   - 상장폐지, 신규상장, 거래정지, 종목명/코드 변경 이력이 더 필요하다.
4. 거래비용/유동성 모델 고도화
   - ADV 참여율, 예상 체결 불리함, 거래정지/상하한가 리스크 반영.
5. 성과 집중도 완화
   - full-period 초과수익이 일부 구간/일부 종목에 집중되지 않는지 더 엄격히 확인.
6. 운영 모니터링 강화
   - cloud timer 실패, API 실패, CSV schema drift, report stale 상태 알림.
7. 실거래 실행은 계속 금지
   - 현재 단계에서는 order plan을 사람이 검토하는 구조를 유지해야 한다.

## 14. 이 프로젝트를 한 문장으로 요약하면

이 저장소는 **국내 주식 중심의 자동매매 전략을 실제 주문 없이 연구, 검증, 데이터 품질 점검, 리스크 차단, 클라우드 paper-operation까지 연결하는 안전 우선형 Python CLI 시스템**이다.
