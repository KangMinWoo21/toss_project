# Auto Trading Point-In-Time Universe

작성일: 2026-07-01

## 목적

미국주식 paper-only 자동매매 엔진의 생존편향을 줄이기 위해 `as_of` 기준 universe history를 지원한다.
기존 current universe CSV도 계속 지원하지만, audit/report에는 `survivorship_warning_flag=True`가 남는다.

## Universe History Schema

필수 컬럼:

- `symbol`
- `name`
- `asset_type`
- `exchange`
- `effective_from`
- `effective_to`
- `status`
- `source`
- `survivorship_warning`

선택 컬럼:

- `target_weight`

`status`는 `active`, `listed`, `included`일 때만 포함된다. `delisted` row는 `as_of`와 무관하게 제외된다.

## 실행 예

```powershell
python -m backtester auto-paper-run `
  --universe data/auto_trading/us_universe_history_sample.csv `
  --universe-as-of 2026-07-01 `
  --external-data-dir data/auto_trading/free_external_data
```

## Audit Fields

`auto_paper_audit_log.json`에 다음 필드가 저장된다.

- `universe_mode`: `current` 또는 `point_in_time`
- `universe_as_of`
- `survivorship_warning`
- `survivorship_warning_flag`

`auto_paper_performance.csv`에도 같은 universe mode와 survivorship flag가 저장된다.

## 한계

현재 sample은 검증용 seed다. 실제 기관급 point-in-time 검증을 위해서는 상장/상폐/편입/퇴출 이력이 포함된 신뢰 가능한 데이터셋으로 교체해야 한다.

Paper execution simulator 사용법은 `docs/auto-trading-paper-execution-simulator.md`를 참고한다.
