# KIS 미국주식 Paper-Only 트랙 선행 리서치

작성 기준일: 2026-07-01

이 문서는 한국투자증권 KIS Open API로 미국주식 paper-only 자동매매 트랙을 만들기 전에 확인한 공식 자료, 오픈소스, 연구 자료를 정리한다. v1 구현의 목적은 실주문이 아니라 모의투자 잔고/시세를 읽고 보호 포지션 정책을 반영한 dry-run 주문계획을 생성하는 것이다.

## 1. 목적과 v1 범위

v1에서 다룰 범위는 다음으로 제한한다.

- KIS 모의투자 계좌의 미국주식 잔고 조회
- KIS 해외주식 시세 조회
- protected positions CSV 기반 보호 정책
- dry-run order plan CSV/Markdown 생성
- 모든 계획 행의 `execution_allowed=False` 고정

v1에서 제외할 범위는 다음과 같다.

- 실주문 API 호출
- 실전 계좌 조회 또는 실전 계좌 주문
- 환전, 원화/달러 배분, 환율 기반 현금 최적화
- 전략 자동선정, 백테스트 파라미터 튜닝, 포지션 추천 모델 학습
- 주문 정정/취소, 미체결 관리, 실시간 체결 이벤트 처리

결론적으로 v1은 "주문 실행기"가 아니라 "계좌 상태를 반영한 paper-only 계획 생성기"다.

## 2. KIS 공식 자료

### KIS Open API Portal

- 링크: [KIS Open API Portal](https://apiportal.koreainvestment.com/)
- 용도: 실제 구현 시 API 문서, TR-ID, 요청 파라미터, 모의투자/실전투자 도메인 구분을 확인하는 1차 기준.
- 반영 포인트:
  - KIS 엔드포인트와 TR-ID는 포털을 기준으로 최종 확인한다.
  - 포털 문서는 변경될 수 있으므로 구현 시 상수값을 코드에 박기 전에 다시 확인한다.
  - v1은 모의투자 전용으로 설계하고 실전투자 도메인은 사용하지 않는다.

### koreainvestment/open-trading-api

- 링크: [koreainvestment/open-trading-api](https://github.com/koreainvestment/open-trading-api)
- 용도: 한국투자증권이 제공하는 공식 Python 예제 저장소.
- 확인한 구조:
  - `examples_llm/`: 기능 단위 API 예제. 에이전트가 endpoint-level 구현을 이해하기 좋다.
  - `examples_user/`: 사용자 워크플로우 중심의 통합 예제.
  - `examples_llm/kis_auth.py`: 인증, 토큰, 모의투자/실전투자 환경 전환 흐름 참고.
  - `examples_llm/overseas_stock/`: 해외주식 관련 기능 단위 예제.
- 해외주식 예제 중 v1에서 참고할 후보:
  - `inquire_balance`: 해외주식 잔고 조회
  - `inquire_present_balance`: 현재잔고/예수금 성격의 조회
  - `price`: 해외주식 현재가 조회
  - `inquire_asking_price`: 호가 조회, v1 필수는 아니지만 추후 슬리피지/유동성 점검에 참고
  - `order`: 주문 예제. v1에서는 호출하지 않고 요청 구조 이해용으로만 참고

### LLM용 공식 가이드

- 링크: [open-trading-api llms.txt](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/llms.txt)
- 핵심 내용:
  - `examples_llm/`은 단일 기능 API 이해에 적합하다.
  - `examples_user/`는 완전한 거래 워크플로우 이해에 적합하다.
  - `kis_devlp.yaml`은 모의투자와 실전투자 환경, 앱키, 계좌 설정 템플릿을 제공한다.
- 반영 포인트:
  - v1 구현은 공식 예제의 인증/요청 구조를 참고하되, 이 저장소의 기존 `.env` 패턴에 맞춘다.
  - 토큰 파일명, 계좌번호, 앱키, 앱시크릿이 로그나 예외 메시지에 노출되지 않도록 한다.

## 3. 오픈소스 참고자료

### python-kis

- 링크: [Soju06/python-kis](https://github.com/Soju06/python-kis)
- 성격: 한국투자증권 REST 기반 Python 라이브러리.
- 장점:
  - 국내/해외 API를 객체 중심 인터페이스로 추상화한다.
  - 시세, 차트, 잔고, 주문, 실시간 이벤트까지 폭넓게 다룬다.
  - 잔고와 예수금을 구조화된 객체로 다루는 예시가 있어 내부 dataclass 설계에 참고할 수 있다.
  - PyPI 배포와 changelog가 있어 유지보수 흔적을 확인하기 쉽다.
- v1 적용 판단:
  - 직접 의존성으로 추가하지 않는다.
  - 응답 객체 모델링, 예외 분리, 토큰 재발급 흐름을 참고한다.
  - 주문 관련 API는 구조 참고만 하고 v1 코드에는 만들지 않는다.

### mojito

- 링크: [sharebook-kr/mojito](https://github.com/sharebook-kr/mojito)
- 성격: KIS Python wrapper.
- 장점:
  - 함수형 인터페이스가 단순하다.
  - 현재가 조회, 잔고 조회, 미국주식 주문 예제가 짧아 API 사용 흐름을 파악하기 좋다.
- v1 적용 판단:
  - 직접 의존성으로 추가하지 않는다.
  - 단순한 wrapper API 형태를 참고하되, 이 프로젝트에서는 안전 정책을 더 강하게 둔다.
  - README의 주문 예제는 "어떤 API가 있는지" 확인하는 용도이며, v1 구현 대상이 아니다.

### QuantConnect Lean

- 링크: [QuantConnect/Lean](https://github.com/QuantConnect/Lean)
- 성격: 모듈형 알고리즘 트레이딩 엔진.
- 참고 포인트:
  - 데이터, 브로커리지, 엔진, 리포트, 설정이 분리된 구조.
  - live trading까지 지원하는 큰 시스템이므로 v1에 직접 도입하기에는 과하다.
- v1 적용 판단:
  - 모듈 경계 설계 참고용으로만 사용한다.
  - `client`, `models`, `planner`, `reports`, `protected_positions`처럼 역할을 작게 나눈다.

### vectorbt

- 링크: [polakowo/vectorbt](https://github.com/polakowo/vectorbt)
- 성격: 대규모 벡터화 백테스팅/전략 연구 프레임워크.
- 참고 포인트:
  - 많은 전략 조합을 빠르게 실험하는 연구 구조.
  - 워크포워드와 강건성 검증 관점에서 참고할 가치가 있다.
- v1 적용 판단:
  - v1은 계좌 기반 dry-run 계획 생성이므로 직접 사용하지 않는다.
  - 향후 미국주식 전략 연구/검증을 붙일 때 참고한다.

### backtrader

- 링크: [mementum/backtrader](https://github.com/mementum/backtrader)
- 성격: Python 백테스팅 라이브러리.
- 참고 포인트:
  - broker, data feed, strategy 개념이 분리되어 있다.
  - 자체 엔진이 있는 이 저장소에는 직접 도입하지 않는다.
- v1 적용 판단:
  - paper-only 트랙에는 불필요한 의존성이다.
  - 향후 이벤트 기반 미국주식 백테스트를 설계할 때 구조 참고자료로 둔다.

## 4. 연구/논문 메모

### 백테스트 과최적화

- 자료: Carr & Lopez de Prado, [Determining Optimal Trading Rules without Backtesting](https://arxiv.org/abs/1408.1159)
- 핵심 메모:
  - 많은 규칙 후보를 과거 데이터에 반복 대입하면 백테스트 과최적화가 발생하기 쉽다.
  - paper-only 관찰 단계에서도 "잘 맞은 결과"를 곧바로 실전 전환 근거로 삼으면 위험하다.
- 설계 반영:
  - v1은 전략 선택이나 파라미터 튜닝을 하지 않는다.
  - dry-run 계획은 매매 승인 자료가 아니라 관찰/검토 자료로만 둔다.

### 과최적화 보정

- 자료: Koshiyama & Firoozye, [Avoiding Backtesting Overfitting by Covariance-Penalties](https://arxiv.org/abs/1905.05023)
- 핵심 메모:
  - 전략 성과 평가는 데이터 양, 파라미터 수, 반복 실험 수의 영향을 받는다.
  - 과거 성과가 좋아도 모델 복잡도와 선택 편향을 보정해야 한다.
- 설계 반영:
  - v1에서는 외부 전략/모델을 주문계획에 직접 연결하지 않는다.
  - 향후 전략 입력을 붙이더라도 별도 validation gate를 통과해야 한다.

### 실행비용과 슬리피지

- 자료: Almgren-Chriss 계열 최적집행 연구
- 참고 자료: Vaes & Hauser, [Optimal Trade Execution with Uncertain Volume Target](https://arxiv.org/abs/1810.11454)
- 핵심 메모:
  - 실제 체결 성과는 기준가격, 주문 크기, 유동성, 변동성, 슬리피지에 크게 좌우된다.
  - paper plan의 reference price는 실제 체결가격이 아니다.
- 설계 반영:
  - v1 CSV에 `reference_price`와 `estimated_value`를 두되 실제 체결 보장으로 해석하지 않는다.
  - v1에서는 주문 실행이 없으므로 슬리피지는 계산 대상이 아니라 리스크 메모로 남긴다.
  - 추후 확장 시 ADV, bid-ask spread, 주문참여율 점검을 별도 모듈로 추가한다.

### 자동매매 통제

- 자료: Jackie Shen, [Nine Challenges in Modern Algorithmic Trading and Controls](https://arxiv.org/abs/2101.08813)
- 핵심 메모:
  - 자동매매 시스템은 전략 자체보다 통제, 테스트, 시뮬레이션, 운영 리스크가 중요하다.
  - 주문 전 점검, 차단 상태, kill switch에 해당하는 강한 기본값이 필요하다.
- 설계 반영:
  - v1은 주문 API 호출 코드를 만들지 않는 방식으로 가장 강한 kill switch를 둔다.
  - 모든 계획 행은 `execution_allowed=False`로 고정한다.
  - protected position은 기본적으로 SELL 차단한다.
  - CSV/Markdown에는 "paper-only", "dry-run", "no order submitted" 문구를 명시한다.

## 5. 우리 설계에 반영할 원칙

KIS 미국주식 paper-only 트랙은 다음 원칙으로 구현한다.

- API 클라이언트, 데이터 모델, 보호 포지션 정책, 플래너, 리포트 저장을 분리한다.
- 기존 국내주식 엔진과 월간 리밸런싱 로직은 건드리지 않는다.
- 공식 KIS 예제의 엔드포인트와 TR-ID를 기준으로 하되, 구현 직전에 포털에서 다시 확인한다.
- v1에는 주문 제출 함수, 주문 정정 함수, 주문 취소 함수를 만들지 않는다.
- 주문 예제 코드는 요청 구조 이해용으로만 참고하고 실행 경로에 넣지 않는다.
- 목표비중은 로컬 CSV에서 읽고, 전략 엔진과 직접 연결하지 않는다.
- 모든 계획 행은 `execution_allowed=False`로 저장한다.
- protected position은 SELL 차단을 기본 정책으로 둔다.
- 시세 누락, 수량 0, 가격 0 이하, 필수 설정 누락은 fail-closed 처리한다.
- 외부 라이브러리는 당장 의존성으로 추가하지 않는다.

## 6. 권장 모듈 구조

v1 구현은 다음 패키지 구조를 기준으로 한다.

```text
backtester/kis_us/
  __init__.py
  config.py
  client.py
  models.py
  protected_positions.py
  planner.py
  reports.py
```

각 모듈의 책임은 다음과 같다.

- `config.py`: `.env`와 CLI 입력을 조합해 모의투자 전용 설정을 만든다.
- `client.py`: 토큰 발급, 잔고 조회, 해외주식 시세 조회만 담당한다.
- `models.py`: 잔고, 시세, 보호 포지션, 계획 주문 dataclass를 정의한다.
- `protected_positions.py`: 보호 CSV를 읽고 SELL 차단 여부를 판단한다.
- `planner.py`: 잔고, 현금, 목표비중, 시세, 보호 정책을 dry-run 계획으로 변환한다.
- `reports.py`: CSV와 Markdown 요약을 저장한다.

CLI는 `backtester/__main__.py`에 얇게 연결하되, 비즈니스 로직은 위 패키지에 둔다.

## 7. 다음 구현 순서

1. `backtester/kis_us/models.py`에 내부 dataclass를 정의한다.
2. `backtester/kis_us/config.py`에서 모의투자 전용 설정 로더를 만든다.
3. `backtester/kis_us/protected_positions.py`에서 보호 CSV 로더와 SELL 차단 판정을 만든다.
4. `backtester/kis_us/planner.py`에서 dry-run 주문계획 생성 로직을 만든다.
5. `backtester/kis_us/reports.py`에서 CSV/Markdown 저장기를 만든다.
6. `backtester/kis_us/client.py`에서 KIS 조회 클라이언트를 mock 테스트 가능한 구조로 만든다.
7. `backtester/__main__.py`에 `kis-us-paper-plan` 명령만 연결한다.
8. `tests/test_kis_us_*.py`로 파싱, 보호 정책, 플래너, CLI를 검증한다.

## 8. 최종 결론

v1은 KIS API를 직접 얇게 감싸는 방식으로 구현한다. `python-kis`, `mojito`, KIS 공식 예제는 구조와 응답 파싱 방식의 참고자료로 사용하되, 새 의존성으로 추가하지 않는다.

가장 중요한 설계 결정은 안전 기본값이다. 이 트랙은 paper-only이며, 실주문 API 호출 코드를 포함하지 않는다. 생성되는 결과물은 검토용 주문계획일 뿐이고, 어떤 행도 자동 실행 가능 상태로 표시하지 않는다.
