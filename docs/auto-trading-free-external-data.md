# US Paper-Only Free External Data Layer

작성일: 2026-07-01

## 목적

미국주식 paper-only 자동매매 엔진에 무료 외부데이터를 로컬 CSV 형태로 연결한다.
`auto-paper-run`은 계속 로컬 CSV만 읽으며, 실행 중 네트워크, 브로커, KIS, Toss, yfinance 호출을 하지 않는다.

## 적용된 무료 데이터 계층

- SEC EDGAR 계열 재무/factor proxy: `factors.csv`
- FINRA Daily Short Sale Volume: `short_sale_volume.csv`
- GDELT 또는 Alpha Vantage 뉴스 감성 proxy: `news_sentiment.csv`
- Alpha Vantage listing status 또는 Nasdaq Trader symbol directory: `listing_status.csv`
- Yahoo/Alpaca 일봉 volume 기반 ADV proxy: 가격 CSV에서 계산

## 로컬 CSV 위치

기본 seed 위치:

```powershell
data/auto_trading/free_external_data
```

실행 예:

```powershell
python -m backtester auto-paper-run --external-data-dir data/auto_trading/free_external_data
```

## 무료 데이터 갱신 스크립트

네트워크 fetch는 엔진 실행과 분리된 별도 스크립트에서만 수행한다.

```powershell
python scripts/fetch_us_free_external_data.py `
  --symbols SPY,QQQ,AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA `
  --output-dir data/auto_trading/free_external_data `
  --alpha-vantage-key YOUR_ALPHA_VANTAGE_KEY `
  --cik-map data/auto_trading/us_cik_map.csv `
  --finra-date 20260630
```

`--alpha-vantage-key`가 없으면 listing/news는 placeholder row로 저장된다.
`--cik-map`이 없으면 SEC factor proxy는 `missing_cik_map` source로 저장된다.
FINRA short-sale volume은 `--finra-date`의 일별 파일을 사용한다.

## 산출물 반영

`auto_paper_order_plan.csv`에 다음 risk/execution proxy 컬럼이 추가된다.

- `sector`, `beta`, `size_score`, `value_score`, `quality_score`, `momentum_score`
- `short_volume_ratio`
- `news_article_count`, `news_sentiment_score`
- `listing_status`, `delisted`
- `estimated_market_impact_rate`, `estimated_market_impact_usd`, `liquidity_source`
- `external_data_policy`

`auto_paper_audit_log.json`에는 다음 감사 필드가 추가된다.

- `external_data_policy`
- `external_data_dir`
- `external_data_sources`
- `external_data_network_policy`
- `external_data_live_execution_policy`

모든 주문계획 행은 계속 `paper_only=True`, `dry_run=True`, `execution_allowed=False`, `production_effect=none`이다.

## 주의

현재 `data/auto_trading/free_external_data/`의 값은 파이프라인 검증용 seed다.
투자 판단용 데이터가 아니며, 실제 운용 전에는 각 무료 출처에서 새로 가져온 CSV로 교체해야 한다.

무료 데이터는 지연, 누락, 출처별 정의 차이, 생존편향, API 제한이 있을 수 있다.
따라서 이 계층은 실거래 판단이 아니라 paper-only 연구와 리스크 경고 보강용으로만 사용한다.

Point-in-time universe 사용법은 `docs/auto-trading-point-in-time-universe.md`를 참고한다.
