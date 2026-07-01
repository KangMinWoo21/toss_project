# KIS 미국주식 Paper-Only 실행 런북

작성 기준일: 2026-07-01

이 런북은 KIS 미국주식 모의투자 조회 트랙을 안전하게 실행하기 위한 절차다. v1은 잔고/시세 조회와 dry-run 주문계획 생성만 다루며, 실주문 API 호출은 포함하지 않는다. 생성되는 모든 주문계획 행은 `execution_allowed=False`다.

## 1. 로컬 데모

KIS 계정 정보 없이 샘플 잔고와 샘플 시세로 planner/report 경로를 확인한다.

```powershell
python -m backtester kis-us-paper-plan-demo
```

기본 입력 파일은 아래와 같다.

- `data/examples/kis_us_targets_sample.csv`: 목표비중 샘플
- `data/examples/kis_us_protected_positions_sample.csv`: 보호 포지션 샘플
- `data/examples/kis_us_demo_positions.csv`: 데모 잔고
- `data/examples/kis_us_demo_quotes.csv`: 데모 시세

기본 출력은 아래 파일에 저장된다.

- `data/reports/kis_us_paper_order_plan_demo.csv`
- `data/reports/kis_us_paper_order_plan_demo.md`

데모 결과에서 `TSLA`는 목표비중 파일에 없으므로 SELL 대상이지만, protected position으로 지정되어 `SKIP/BLOCKED` 처리된다.

## 2. 목표비중 CSV

실제 모의투자 조회 계획에는 `symbol,exchange,target_weight` 컬럼이 필요하다.

```csv
symbol,exchange,target_weight
AAPL,NAS,0.45
NVDA,NAS,0.35
QQQ,NAS,0.20
```

지원 exchange 코드는 KIS 해외시세 조회 기준으로 `NAS`, `NYS`, `AMS`만 사용한다. 목표비중 합계가 1.0을 넘거나, 음수 비중/중복 symbol/알 수 없는 exchange가 있으면 fail-closed로 계획 생성을 중단한다.

## 3. Protected Positions CSV

보호 포지션 파일은 선택 사항이며 `symbol,reason` 컬럼을 사용한다.

```csv
symbol,reason
TSLA,long_term_tax_lot_do_not_sell
```

보호 종목은 보유 수량을 줄이는 SELL 계획이 나오더라도 `SKIP/BLOCKED`로 바뀐다. BUY나 수량 변화가 없는 행까지 실주문으로 이어지는 경로는 없다.

## 4. KIS 모의투자 환경 변수

`.env.example`을 참고해 로컬 `.env`에만 실제 값을 넣는다. `.env`는 커밋하지 않는다.

```powershell
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=...
KIS_ACCOUNT_PRODUCT_CODE=...
KIS_MOCK_BASE_URL=https://openapivts.koreainvestment.com:29443
```

`KIS_MOCK_BASE_URL`은 모의투자 도메인만 허용한다. 실전 도메인을 넣으면 설정 로드 단계에서 실패한다.

## 5. KIS 모의투자 조회 기반 계획 생성

목표비중과 보호 포지션을 지정해 dry-run 계획을 만든다.

```powershell
python -m backtester kis-us-paper-plan `
  --targets data/examples/kis_us_targets_sample.csv `
  --protected-positions data/examples/kis_us_protected_positions_sample.csv `
  --balance-exchanges NASD,NYSE,AMEX `
  --output data/reports/kis_us_paper_order_plan.csv `
  --summary-output data/reports/kis_us_paper_order_plan.md
```

현금 값을 KIS 잔고 응답 대신 수동으로 고정하려면 `--cash-usd`를 사용한다.

```powershell
python -m backtester kis-us-paper-plan `
  --targets data/examples/kis_us_targets_sample.csv `
  --cash-usd 1000
```

## 6. 출력 확인

CSV의 핵심 컬럼은 아래와 같다.

- `side`: `BUY`, `SELL`, `SKIP`
- `risk_status`: `PASS` 또는 `BLOCKED`
- `risk_reasons`: `dry_run_only`, `protected_position:...`, `missing_quote`, `invalid_reference_price`, `quantity_below_one_share`
- `execution_allowed`: 항상 `False`

Markdown 요약에는 `paper-only`, `dry-run`, `no order submitted` 문구가 포함된다.

## 7. 안전 원칙

- 이 트랙은 실주문을 제출하지 않는다.
- 주문 제출 함수, 주문 취소 함수, 주문 정정 함수는 v1에 만들지 않는다.
- API 인증/조회 실패, 필수 설정 누락, 잘못된 목표비중은 계획 생성 실패로 처리한다.
- 앱키, 시크릿, 계좌번호는 오류 메시지나 보고서에 출력하지 않는다.
- 기존 국내주식 엔진과 월간 리밸런싱 로직은 변경하지 않는다.
