# 토스증권 자동매매 백테스터

국내주식 자동매매 전략을 실거래 전에 검증하기 위한 로컬 백테스팅 프로그램입니다.

현재 버전은 CSV 일봉 데이터를 사용합니다. 실주문 기능은 넣지 않았고, 토스증권 Open API는 나중에 캔들 데이터 수집이나 실시간 실행 단계에서 연결하는 구조입니다.

## 실행 환경

외부 패키지 없이 Python 표준 라이브러리만 사용합니다.

Codex 번들 Python 예시:

```powershell
& 'C:\Users\KangMinWoo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m backtester compare --data 'data/sample_kr_stock.csv'
```

시스템에 Python이 설치되어 있다면 다음처럼 실행할 수 있습니다.

```powershell
python -m backtester compare --data 'data/sample_kr_stock.csv'
```

## 토스증권 API 키 설정

토스증권 캔들 데이터를 가져오려면 프로젝트 루트에 `.env` 파일을 만들고 아래처럼 입력합니다.

```env
TOSSINVEST_CLIENT_ID=너의_client_id
TOSSINVEST_CLIENT_SECRET=너의_client_secret
```

`.env`는 `.gitignore`에 포함되어 커밋되지 않게 해두었습니다. 형식 예시는 `.env.example`을 참고하면 됩니다.

토스증권에서 삼성전자 일봉 가져오기:

```powershell
python -m backtester fetch-toss --symbol 005930 --output 'data/toss/005930.csv' --pages 5
```

받은 데이터로 전략 비교:

```powershell
python -m backtester compare --data 'data/toss/005930.csv' --initial-cash 1000000
```

## 명령어

전략 하나 실행:

```powershell
python -m backtester run --data 'data/sample_kr_stock.csv' --strategy volatility_breakout
```

내장 전략 전체 비교:

```powershell
python -m backtester compare --data 'data/sample_kr_stock.csv'
```

특정 과거 구간에서 가장 좋았던 전략을 고르고, 그 이후 구간에서 검증:

```powershell
python -m backtester walk-forward --data 'data/sample_kr_stock.csv' --window '2026-01-02:2026-01-08:2026-01-09:2026-01-12' --window '2026-01-06:2026-01-12:2026-01-13:2026-01-16'
```

행 개수 기준으로 여러 구간을 자동 생성해서 검증:

```powershell
python -m backtester walk-forward --data 'data/sample_kr_stock.csv' --train-size 7 --test-size 4 --step-size 2
```

일부 전략만 비교:

```powershell
python -m backtester walk-forward --data 'data/sample_kr_stock.csv' --train-size 7 --test-size 4 --strategies 'volatility_breakout,moving_average_cross,rsi_rebound'
```

뉴스/SNS 이벤트 점수를 섞어 비교:

```powershell
python -m backtester compare --data 'data/sample_kr_stock.csv' --news-filter --events 'data/sample_events.csv' --symbol 005930
```

외국인/기관/개인 수급 점수를 섞어 비교:

```powershell
python -m backtester compare --data 'data/sample_kr_stock.csv' --flow-filter --flows 'data/sample_flows.csv' --symbol 005930
```

뉴스와 수급을 동시에 섞어 비교:

```powershell
python -m backtester compare --data 'data/sample_kr_stock.csv' --news-filter --events 'data/sample_events.csv' --flow-filter --flows 'data/sample_flows.csv' --symbol 005930
```

초기 자금, 수수료, 세금, 슬리피지 조정:

```powershell
python -m backtester compare --data 'data/sample_kr_stock.csv' --initial-cash 10000000 --fee-rate 0 --tax-rate 0.0018 --slippage-rate 0.0005
```

## CSV 형식

CSV는 다음 컬럼을 가져야 합니다.

```csv
date,open,high,low,close,volume
2026-01-02,10000,10200,9900,10100,100000
```

뉴스/SNS 이벤트 CSV는 다음 컬럼을 사용합니다.

```csv
date,symbol,source,title,sentiment_score,importance_score
2026-01-08,005930,news,negative chip cycle note,-0.9,1.0
```

`sentiment_score`는 -1.0에서 +1.0 사이의 점수를 권장합니다. `importance_score`가 높을수록 같은 날짜의 평균 점수에 더 크게 반영됩니다.

수급/내부자 이벤트 CSV는 다음 컬럼을 사용합니다.

```csv
date,symbol,foreign_net_value,institution_net_value,individual_net_value,insider_buy_value,insider_sell_value
2026-01-08,005930,-100000000,-50000000,150000000,0,0
```

점수는 외국인/기관 순매수를 긍정, 개인 순매수 쏠림과 내부자 매도를 부정으로 봅니다. 내부자 매수는 긍정 점수로 반영합니다.

## 내장 전략

| 전략 | 이름 | 설명 |
| --- | --- | --- |
| Buy and Hold | `buy_and_hold` | 첫 날 매수, 마지막 날 매도 |
| 이동평균 크로스 | `moving_average_cross` | 단기 이동평균이 장기 이동평균 위면 매수 |
| 변동성 돌파 | `volatility_breakout` | 전일 변동폭 기준 돌파 시 매수 |
| RSI 반등 | `rsi_rebound` | 과매도 구간 진입 후 반등을 기대 |
| 거래량 돌파 | `volume_breakout` | 거래량 증가와 전고점 돌파를 함께 확인 |

## 결과 지표

- `final_equity`: 최종 평가금액
- `return_%`: 총 수익률
- `mdd_%`: 최대 낙폭
- `trades`: 청산된 거래 수
- `win_%`: 승률
- `profit_factor`: 총이익 / 총손실

## 워크포워드 테스트

`walk-forward` 명령은 다음 순서로 동작합니다.

1. train 구간에서 모든 후보 전략을 백테스트합니다.
2. train 구간 수익률이 가장 높은 전략을 고릅니다.
3. 고른 전략만 이후 test 구간에 적용합니다.
4. 여러 구간에서 반복한 뒤 test 구간 평균 수익률 기준으로 요약합니다.

이 방식은 “과거에 좋아 보였던 전략이 이후 구간에서도 유지되는지” 확인하는 용도입니다. 단순히 전체 기간에서 수익률이 높은 전략을 고르는 것보다 과최적화 위험을 줄이는 데 도움이 됩니다.

## 뉴스/SNS 혼합 백테스트

`--news-filter` 옵션은 기존 전략의 매수/매도 신호에 이벤트 점수를 필터로 추가합니다.

- 매수 신호가 나와도 해당 날짜 이벤트 점수가 `--min-buy-score`보다 낮으면 매수하지 않습니다.
- 보유 중 이벤트 점수가 `--force-sell-score` 이하이면 청산합니다.
- 이벤트가 없는 날짜의 점수는 0으로 봅니다.

예:

```powershell
python -m backtester compare --data 'data/toss/005930.csv' --news-filter --events 'data/my_news_events.csv' --symbol 005930 --min-buy-score -0.2 --force-sell-score -0.8
```

뉴스 API, SNS API, 수동 수집 데이터는 모두 이 이벤트 CSV 형식으로 변환하면 같은 백테스터에서 비교할 수 있습니다.

## 수급/내부자 혼합 백테스트

`--flow-filter` 옵션은 외국인/기관/개인 수급과 내부자 매매 점수를 필터로 사용합니다.

- 매수 신호가 나와도 수급 점수가 `--min-flow-score`보다 낮으면 매수하지 않습니다.
- 보유 중 수급 점수가 `--force-flow-sell-score` 이하이면 청산합니다.
- 수급 데이터가 없는 날짜의 점수는 0으로 봅니다.

예:

```powershell
python -m backtester compare --data 'data/toss/005930.csv' --flow-filter --flows 'data/flows/005930.csv' --symbol 005930 --min-flow-score -0.2 --force-flow-sell-score -0.8
```

`pykrx`가 설치되어 있으면 KRX 투자자별 거래대금 데이터를 가져와 수급 CSV를 만들 수 있습니다.

```powershell
python -m backtester fetch-pykrx-flow --symbol 005930 --start 2026-01-01 --end 2026-06-09 --output 'data/flows/005930.csv'
```

현재 프로그램은 `pykrx`를 필수 의존성으로 설치하지 않습니다. 설치되어 있지 않으면 `pip install pykrx` 안내 메시지를 출력합니다.

## 테스트

```powershell
python -m unittest discover -s tests
```

## 다음 확장 후보

1. 토스증권 `/api/v1/candles` 기반 데이터 수집기
2. 종목 여러 개를 한 번에 돌리는 포트폴리오 백테스트
3. 전략 파라미터 최적화
4. 머신러닝 신호 생성기
5. 모의매매 로그 저장
6. 실주문 연결 전 안전장치: `dry_run`, 일일 손실 제한, 주문 금액 제한

## 주의

백테스트 결과는 미래 수익을 보장하지 않습니다. 실거래 연결 전에는 수수료, 세금, 슬리피지, 거래정지, 호가 공백, 주문 미체결을 반드시 반영해야 합니다.

## 초단기 Paper Scalper

토스증권 현재가, 호가, 최근 체결 REST API를 초 단위로 조회해 실주문 없이 가상 진입/청산 로그를 남깁니다.

```powershell
python -m backtester paper-scalp --symbol 005930 --iterations 30 --interval-seconds 1 --output 'data/scalper/005930_paper_scalp.csv'
```

신호 조건은 다음을 동시에 봅니다.

- 최근 체결량이 직전 평균보다 크게 증가
- 현재가가 직전 조회보다 상승
- 매수 1~5호가 잔량이 매도 1~5호가 잔량보다 우세
- 보유 중 익절/손절 조건 도달 시 가상 청산

이 명령은 실제 주문을 내지 않습니다. 장중 테스트와 로그 검증을 먼저 한 뒤, 실주문 연결은 별도 안전장치가 준비된 뒤에만 진행해야 합니다.
