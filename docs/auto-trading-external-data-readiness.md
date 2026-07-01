# 미국주식 Paper-Only External Data Readiness

## 목적

`auto-paper-external-data-readiness`는 무료 외부 데이터 CSV가 paper-only 엔진에 투입 가능한 상태인지 점검한다. 네트워크 fetch는 하지 않으며, 로컬 CSV만 읽는다.

## 어댑터

v1 readiness는 다음 로컬 어댑터를 검사한다.

- `factors`: `factors.csv`
- `short_sale_volume`: `short_sale_volume.csv`
- `news_sentiment`: `news_sentiment.csv`
- `listing_status`: `listing_status.csv`

각 CSV는 `symbol`과 `source`를 가져야 한다. freshness field는 `factors.as_of`, `short_sale_volume.date`, `news_sentiment.date`를 사용한다. `listing_status`는 상장 상태 스냅샷이므로 freshness field를 `not_applicable`로 둔다.

## Fail-Closed 조건

다음 중 하나라도 발생하면 해당 adapter row는 `BLOCK`이다.

- 파일 없음
- 필수 컬럼 누락
- 요청 심볼 coverage 부족
- `source` 누락
- freshness field 누락

CLI는 하나라도 `BLOCK`이면 exit code `2`를 반환한다.

## 실행

```powershell
python -m backtester auto-paper-external-data-readiness
```

`--symbols`를 생략하면 기본 후보 파일 `data/auto_trading/us_portfolio_optimizer_candidates.csv`에서 심볼을 읽는다.

기본 산출물:

- `data/reports/auto_trading/auto_paper_external_data_readiness.csv`
- `data/reports/auto_trading/auto_paper_external_data_readiness.md`

## 안전 정책

모든 row는 `paper_only=True`, `dry_run=True`, `execution_allowed=False`, `production_effect=none`을 포함한다. 이 리포트는 데이터 준비 상태 감사용이며, 주문 실행이나 실전 배포 신호가 아니다.
