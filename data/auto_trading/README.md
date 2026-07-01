# Auto Trading Data Pack

이 폴더는 자동매매 엔진을 만들기 전 research-to-paper 흐름에 사용할 초기 데이터팩이다.

## 파일

- `us_core_universe.csv`: 자동매매 연구용 기본 미국주식/ETF 유니버스. `symbol`, `name`, `asset_type`, `universe_start`, `universe_end`, `source`, `active_flag`, `survivorship_warning` 컬럼은 필수다.
- `kis_us_targets_core.csv`: 기존 KIS 미국주식 paper-only 계획 생성기에 바로 넣을 수 있는 목표비중 CSV.
- `protected_positions_core.csv`: 보호 포지션 테스트용 CSV.

## 외부 일봉 데이터

일봉 OHLCV는 다음 명령으로 갱신한다.

```powershell
python scripts/fetch_us_yahoo_daily.py --output-dir data/external/yahoo/us_daily
```

데이터 소스는 Yahoo Finance chart endpoint이며, 연구/백테스트 입력으로만 사용한다. 실주문 실행 판단에는 별도 검증, 데이터 품질 점검, paper-only 관찰 기간이 필요하다.
